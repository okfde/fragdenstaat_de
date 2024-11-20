import dataclasses
import datetime
import enum
import io
import locale
import re
import ssl
import tempfile
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from urllib.parse import urljoin

import bs4
import html_text
import requests
import requests.adapters
import urllib3
from bs4 import BeautifulSoup
from PIL import Image

if TYPE_CHECKING:
    from . import captcha

TOKEN_RE = r"^Token: (?P<token>.+)$"
EMAIL_RE = r"^Email: (?P<email>.+)$"
CASE_ID_REGEX = r"^Case Id: (?P<caseid>.+)$"
VALID_UNTIL_REGEX = r"^Please be informed that the link is valid until (?P<date>.+)$"
LOGIN_URL = "https://pad.frontex.europa.eu/Token/Create"


HEADERS = {"User-Agent": "FragDenStaat Importer (info@fragdenstaat.de)"}


def search_re_or_none(regex: str, group: str, text: str) -> Optional[str]:
    match = re.search(regex, text, flags=re.MULTILINE)
    if match is None:
        return None
    return match.group(group).strip()


@dataclasses.dataclass
class FrontexCredentials:
    token: str
    email: str
    case_id: str
    valid_until: datetime.date

    @classmethod
    def from_email(cls, text: str) -> Optional["FrontexCredentials"]:
        token = search_re_or_none(TOKEN_RE, "token", text)
        email = search_re_or_none(EMAIL_RE, "email", text)
        case_id = search_re_or_none(CASE_ID_REGEX, "caseid", text)
        valid_until_str = search_re_or_none(VALID_UNTIL_REGEX, "date", text)

        if token is None or email is None or case_id is None or valid_until_str is None:
            return None

        valid_until = parse_frontex_mail_date(valid_until_str)
        return cls(token, email, case_id, valid_until)


def parse_frontex_mail_date(datestr: str) -> datetime.date:
    locale.setlocale(locale.LC_ALL, "en_US.utf-8")
    date = datetime.datetime.strptime(datestr, "%A, %d %B %Y").date()
    locale.setlocale(locale.LC_ALL, None)
    return date


@dataclass
class PadCase:
    metadata: "PadMetadata"
    messages: List["PadMessage"]
    raw: str

    @classmethod
    def from_source(cls, text: str) -> "PadCase":
        soup = BeautifulSoup(text, features="html.parser")
        metadata = None
        messages = []
        for item in soup.find_all(class_="askFX_Item"):
            if "askFX_Header" in item.get("class"):
                metadata = parse_header(item)
            elif item.find("textarea", id="NewEntry"):
                pass
            else:
                messages.append(parse_message(item))

        return cls(metadata=metadata, messages=messages, raw=text)


@dataclass
class PadMetadata:
    created_on: datetime.datetime
    documents: List["PadDocument"]
    subject: str
    created_by: str
    case_id: str


@dataclass
class PadDocument:
    name: str
    link: str


class Direction(enum.Enum):
    IN = "IN"
    OUT = "OUT"


@dataclass
class PadMessage:
    direction: Direction
    date: datetime.datetime
    author: str
    message: str


def is_hidden_input(tag: bs4.element.Tag) -> bool:
    return tag.name == "input" and (
        tag.get("hidden") is not None or tag.get("type") == "hidden"
    )


def parse_documents(elem: bs4.element.Tag) -> List[PadDocument]:
    docs = []
    for link_elem in elem.find_all(class_="askFX_DokumentLink"):
        a_elem = link_elem.find("a")
        name = html_text.extract_text(str(a_elem))
        link = a_elem.get("href")
        docs.append(PadDocument(name=name, link=link))
    return docs


def parse_table(table_elem: bs4.element.Tag) -> Dict[str, Any]:
    data = {}
    for row in table_elem.find_all("tr"):
        label_elem = row.find(class_="askFX_HeaderLabel")
        value_elem = row.find(class_="askFX_HeaderValue")
        label = html_text.extract_text(str(label_elem))
        if "askFX_HeaderValueDocuments" in value_elem.get("class"):
            value = parse_documents(value_elem)
        else:
            value = html_text.extract_text(str(value_elem))
        data[label] = value

    return data


def parse_date(datestr: str) -> datetime.datetime:
    return datetime.datetime.strptime(datestr, "%d/%m/%Y %H:%M")


def parse_header(item: bs4.element.Tag) -> PadMetadata:
    raw_data = parse_table(item.find(class_="askFX_Table"))
    return PadMetadata(
        created_on=parse_date(raw_data["Created on"]),
        documents=raw_data.get("Documents", []),
        subject=raw_data["Subject"],
        created_by=raw_data["Created by"],
        case_id=raw_data["PAD Case ID"],
    )


def get_item_date(item: bs4.element.Tag) -> datetime.datetime:
    raw_date = html_text.extract_text(str(item.find(class_="askFX_itemDateTime")))
    date = datetime.datetime.strptime(raw_date, "%d/%m/%Y\n%H:%M")
    return date


def parse_message(item: bs4.element.Tag) -> PadMessage:
    direction = ""
    if "askFX_OUT" in item.get("class", ""):
        direction = Direction.OUT
    elif "askFX_IN" in item.get("class", ""):
        direction = Direction.IN
    else:
        raise Exception("Unknown direction")
    date = get_item_date(item)
    author_raw = str(item.find(class_="askFX_itemAuthor"))
    author = html_text.extract_text(author_raw)
    message_raw = str(item.find(class_="askFX_itemMessage"))
    message = html_text.extract_text(message_raw)

    return PadMessage(
        direction=direction,
        date=date,
        author=author,
        message=message,
    )


@dataclass
class CaptchaResponse:
    id: str
    text: str


class LoginFailedException(Exception):
    pass


class FrontexHttpAdapter(requests.adapters.HTTPAdapter):
    """Frontex really needs to fix their servers. With newer python versions,
    the connections sometime only works by setting SSL_OP_LEGACY_SERVER_CONNECT
    (0x4) which we do with this custom http adapter"""

    def __init__(self, **kwargs):
        self.ssl_context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
        self.ssl_context.options |= 0x4
        super().__init__(**kwargs)

    def init_poolmanager(self, connections, maxsize, block=False, **pool_kwargs):
        self.poolmanager = urllib3.poolmanager.PoolManager(
            num_pools=connections,
            maxsize=maxsize,
            block=block,
            ssl_context=self.ssl_context,
            **pool_kwargs,
        )


class FrontexPadClient:
    def __init__(self, credentials: FrontexCredentials, captcha_net: "captcha.Net"):
        self.session = requests.Session()
        self.session.mount("https://", FrontexHttpAdapter())
        self.login_url = LOGIN_URL
        self._tmpdir = tempfile.mkdtemp()

        self.credentials = credentials

        # Frontexes Server is configured weirdly and relies on Authority Information Access (AIA) chasing,
        # which python does not support https://bugs.python.org/issue18617
        self._ca_path = Path(__file__).parent / "pad_cadata.pem"
        self.captcha_net = captcha_net

    def _load_captcha(self) -> CaptchaResponse:
        captcha_id = str(uuid.uuid4())
        captcha_url = f"https://pad.frontex.europa.eu/Captcha/Image/{captcha_id}"
        req = self._get(captcha_url)
        image_file = io.BytesIO(req.content)
        captcha_image = Image.open(image_file)
        text = self.captcha_net.solve_image(captcha_image)
        return CaptchaResponse(id=captcha_id, text=text)

    def _extract_form(self, src: str):
        soup = BeautifulSoup(src, features="html.parser")

        form_data = {}
        form = soup.find("form", action="/Token/Create")
        for hidden_field in form.find_all(is_hidden_input):
            form_data[hidden_field.attrs["name"]] = hidden_field.attrs["value"]

        return form_data

    def _get(self, *args, **kwargs) -> requests.Response:
        req = self.session.get(
            *args, **kwargs, verify=str(self._ca_path), headers=HEADERS
        )
        req.raise_for_status()
        return req

    def _post(self, *args, **kwargs) -> requests.Response:
        req = self.session.post(
            *args, **kwargs, verify=str(self._ca_path), headers=HEADERS
        )
        req.raise_for_status()
        return req

    def _login(self, retries: int = 100) -> str:
        """Load the login form and return a path to the captcha iamge

        Returns:
            Path: The path to the captcha image
        """
        while retries > 0:
            req = self._get(self.login_url)

            form_data = self._extract_form(req.text)
            form_data["Guid"] = self.credentials.token
            form_data["Email"] = self.credentials.email
            form_data["CaseId"] = self.credentials.case_id

            captcha_data = self._load_captcha()
            form_data["CaptchaCode"] = captcha_data.text
            form_data["captchaId"] = captcha_data.id

            req = self._post(self.login_url, data=form_data)
            success = "Invalid captcha code provided" not in req.text

            if success:
                return req.text
            retries -= 1

        raise LoginFailedException()

    def load_pad_case(self) -> PadCase:
        text = self._login()
        case = PadCase.from_source(text)
        return case

    def download_document(self, document: PadDocument):
        link = urljoin(self.login_url, document.link)
        return self._get(link).content
