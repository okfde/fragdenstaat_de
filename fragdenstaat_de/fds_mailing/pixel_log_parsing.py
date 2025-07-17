import collections
import logging
import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Generator, Iterable, Optional

from dogtail import Dogtail

from .models import Mailing
from .pixel_log import PixelPath, parse_pixel_path, validate_pixel_path_signature

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PixelLogLine:
    timestamp: datetime
    path: str


@dataclass(frozen=True)
class VerifiedPixelPath(PixelPath):
    timestamp: datetime

    @classmethod
    def from_pixel_path(
        cls, pixel_path: PixelPath, timestamp: datetime
    ) -> "VerifiedPixelPath":
        return cls(
            namespace=pixel_path.namespace,
            mailing_id=pixel_path.mailing_id,
            token=pixel_path.token,
            signature=pixel_path.signature,
            timestamp=timestamp,
        )


class PixelLogParser(collections.abc.Iterator):
    """
    Parses a pixel log, e.g.

    This iterator yields delivery notices for messages in the pixel log
    """

    TIMESTAMP_RE = r"(?P<timestamp>[^\|]+)"
    HTTP_VERB_RE = r"(?P<http_verb>GET|POST|PUT|DELETE|HEAD|OPTIONS)"
    PATH_RE = r"(?P<path>/[^\.]+\.gif)"
    HTTP_VERSION_RE = r"(?P<http_version>HTTP/\d\.\d)"
    LINE_RE = rf"^{TIMESTAMP_RE}\|{HTTP_VERB_RE} {PATH_RE} {HTTP_VERSION_RE}$"

    def __init__(
        self,
        logfile_reader: Iterable[str],
    ):
        self.logfile_reader = logfile_reader

        self._msg_log = defaultdict(lambda: {"log": [], "data": {}})

    def __iter__(self):
        return self

    def __next__(self):
        for line in self.logfile_reader:
            parsed_line = self._parse_line(line.strip())
            if parsed_line is None:
                continue

            return parsed_line

        raise StopIteration

    def _parse_line(self, line: str) -> Optional[PixelLogLine]:
        """Parse a single pixel logline

        ```
        24/Apr/2025:11:37:37 +0200|GET /mailing/1/foobar/signature.gif HTTP/2.0
        ```

        Args:
            line (str): The log line to be parsed

        Returns:
            Optional[PixelLogLine]: If the logline was parsed successfully, a PixelLogLine namedtuple is returned. If it could not be parsed, None is returned
        """

        match = re.match(self.LINE_RE, line)
        if not match:
            return
        line_data = match.groupdict()

        return PixelLogLine(
            timestamp=self._parse_date(line_data["timestamp"]),
            path=line_data["path"],
        )

    @staticmethod
    def _parse_date(date_str: str) -> datetime:
        """Parse a date string into a datetime object.

        Args:
            date_str (str): The date string to be parsed.

        Returns:
            datetime: The parsed datetime object.
        """
        return datetime.strptime(date_str, "%d/%b/%Y:%H:%M:%S %z")


class DogtailPixelLogParser(PixelLogParser):
    """A logfile parser that keeps track of its position in the logfile using dogtail."""

    DEFAULT_DOGTAIL_OFFSET_PATH = Path("./pixel_log.offset")

    def __init__(
        self,
        log_paths: Iterable[str],
        offset_path: Optional[Path] = None,
    ):
        if offset_path is None:
            offset_path = self.DEFAULT_DOGTAIL_OFFSET_PATH

        self.logfile_reader = Dogtail(
            log_paths,
            offset_path=offset_path,
        )
        super().__init__(self.logfile_reader)

    def iteration_done(self):
        self.logfile_reader.update_offset_file()

    def __next__(self):
        for line, _offset in self.logfile_reader:
            parsed_line = self._parse_line(line)
            if parsed_line is None:
                continue

            return parsed_line

        self.iteration_done()

        raise StopIteration


def read_pixel_log(
    log_line_generator: Iterable[PixelLogLine],
) -> Generator[VerifiedPixelPath, None, None]:
    for logline in log_line_generator:
        pixel_path = parse_pixel_path(logline.path)
        if pixel_path is None:
            continue
        if not validate_pixel_path_signature(pixel_path):
            logger.warning("Invalid signature on pixel path: %s", logline.path)
            continue
        yield VerifiedPixelPath.from_pixel_path(pixel_path, logline.timestamp)


def get_pixel_log_generator(
    log_path: Path, offset_path: Optional[Path] = None
) -> Generator[VerifiedPixelPath, None, None]:
    log_paths = [
        log_path,
        log_path.with_suffix(".1"),
    ]
    return read_pixel_log(DogtailPixelLogParser(log_paths, offset_path))


class PixelProcessor:
    def __init__(self, pixel_generator: Iterable[VerifiedPixelPath]):
        self.pixel_generator = pixel_generator
        self.mailings = {}
        self.token_set = defaultdict(set)
        self.open_count = defaultdict(int)

    def run(self):
        for pixel in self.pixel_generator:
            if pixel.namespace != "mailing":
                # Ignore other namespaces
                continue
            mailing = self.get_mailing(pixel)
            if mailing is None:
                continue
            self.process_pixel(pixel, mailing)

        # Done reading the log, now save the results
        for mailing_id, mailing in self.mailings.items():
            if mailing is None:
                continue
            if self.open_count[mailing_id] > 0:
                mailing.open_count += self.open_count[mailing_id]
                mailing.save()
                logger.info(
                    "Processed %d opens for mailing %d",
                    self.open_count[mailing_id],
                    mailing_id,
                )

    def process_pixel(self, pixel: VerifiedPixelPath, mailing: Mailing):
        if pixel.token in self.token_set[pixel.mailing_id]:
            # Already seen this mail in this log run
            # Do not count again but remember the timestamp
            mailing.open_log_timestamp = max(
                pixel.timestamp, mailing.open_log_timestamp
            )
            return
        if (
            mailing.open_log_timestamp is not None
            and mailing.open_log_timestamp >= pixel.timestamp
        ):
            # Already read until there and counted
            return
        self.token_set[pixel.mailing_id].add(pixel.token)
        self.open_count[pixel.mailing_id] += 1
        mailing.open_log_timestamp = pixel.timestamp

    def get_mailing(self, pixel):
        if pixel.mailing_id in self.mailings:
            return self.mailings[pixel.mailing_id]
        try:
            mailing = Mailing._default_manager.get_tracked().get(id=pixel.mailing_id)
        except Mailing.DoesNotExist:
            mailing = None
        self.mailings[pixel.mailing_id] = mailing
        return mailing
