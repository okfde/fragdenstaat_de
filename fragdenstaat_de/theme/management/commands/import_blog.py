import glob
import itertools
import logging
import os
import re

from django.conf import settings
from django.contrib.redirects.models import Redirect
from django.contrib.sites.models import Site
from django.core.files import File
from django.core.files.temp import NamedTemporaryFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management.base import BaseCommand
from django.db import transaction
from django.template.defaultfilters import slugify
from django.utils import translation
from django.utils.dateparse import parse_datetime
from django.utils.html import strip_tags
from django.utils.text import Truncator

import html5lib
import markdown
import pytz
import requests
import yaml
from cms.api import add_plugin
from cms.models.pluginmodel import CMSPlugin
from djangocms_blog.models import Post
from djangocms_text_ckeditor.utils import plugin_to_tag
from filer.models import Image
from lxml import etree

from froide.account.models import User

logger = logging.getLogger(__name__)

YAML_SEPARATOR = "---\n"
NON_SLUG = re.compile(r"[^-\w]")

LIQUID_STRING = re.compile(r'\{\{\s*["\']([^"\']+)["\']\s*\}\}')
MKD_IMAGE = re.compile(r"!\[(.*?)\]\((.*?)\)")


def clean_content(text):
    text = text.replace("<p></p>", "")
    text = text.replace("<p>&nbsp;</p>", "")
    text = text.replace("<br>", "")
    text = text.replace("<center>", "")
    text = text.replace("</center>", "")
    text = LIQUID_STRING.sub("\\1", text)
    text = MKD_IMAGE.sub('<img src="\\2" alt="\\1"/>', text)
    return text


def get_inner_html(tag):
    return (tag.text or "") + "".join(etree.tostring(e).decode("utf-8") for e in tag)


def get_text_for_node(n):
    return "".join(n.itertext())


def get_date(date_str):
    if len(date_str) > 10:
        naive = parse_datetime(date_str)
    else:
        naive = parse_datetime(date_str + "T00:00:00")
    if naive.tzinfo is None:
        return pytz.timezone("Europe/Berlin").localize(naive, is_dst=None)
    return naive


def remove_text(content):
    tree_builder = html5lib.treebuilders.getTreeBuilder("dom")
    parser = html5lib.html5parser.HTMLParser(tree=tree_builder)
    dom = parser.parse(content)

    def out(node):
        if node.nodeType == node.TEXT_NODE:
            return ""
        return node.toxml()

    return "".join([out(y) for y in dom.getElementsByTagName("body")[0].childNodes])


def truncate_text(text):
    return Truncator(strip_tags(text)).words(50)


def create_image_plugin(filename, image, parent_plugin, **kwargs):
    """
    Used for drag-n-drop image insertion with djangocms-text-ckeditor.
    Set TEXT_SAVE_IMAGE_FUNCTION='cmsplugin_filer_image.integrations.ckeditor.create_image_plugin' to enable.
    """
    # from cmsplugin_filer_image.models import FilerImage
    from djangocms_picture.models import Picture
    from filer.models import Image

    print(filename, kwargs)

    image_plugin = Picture()
    image_plugin.placeholder = parent_plugin.placeholder
    image_plugin.parent = parent_plugin
    image_plugin.position = CMSPlugin.objects.filter(
        parent=parent_plugin
    ).count() + kwargs.get("counter", 0)
    image_plugin.language = parent_plugin.language
    image_plugin.plugin_type = "PicturePlugin"
    image_plugin.caption_text = kwargs.get("caption", "")

    if "filer_image" in kwargs:
        image_model = kwargs["filer_image"]
    else:
        image.seek(0)
        image_model = Image.objects.create(
            name=kwargs.get("caption", ""),
            description=kwargs.get("description", ""),
            file=SimpleUploadedFile(name=filename, content=image.read()),
        )

    image_plugin.picture = image_model
    image_plugin.save()
    return image_plugin


class Command(BaseCommand):
    help = "import_blog <directory>"

    def add_arguments(self, parser):
        parser.add_argument("directory", type=str)
        parser.add_argument("slug", nargs="?", type=str)

    def handle(self, *args, **options):
        translation.activate(settings.LANGUAGE_CODE)

        self.author_cache = None
        self.SITE = Site.objects.get_current()
        self.filer_folder = {}
        self.image_cache = {}

        directory = options["directory"]
        do_slug = options.get("slug", "")
        self.directory = directory

        filenames = itertools.chain(
            glob.glob(os.path.join(directory, "**/*.html")),
            glob.glob(os.path.join(directory, "**/*.markdown")),
            glob.glob(os.path.join(directory, "**/*.md")),
        )

        for item in self.get_posts(filenames):
            if do_slug and do_slug != item["slug"]:
                continue
            logging.info("Processing: %s\n", item["title"])
            link = item.pop("link")
            author = item.pop("author")
            meta = item["meta"]
            old_slug = item["slug"]
            date = item["date"]
            slug = slugify(old_slug)
            lang = item["language"]
            with transaction.atomic():
                posts = Post.objects.language(lang).translated(slug=slug)
                if posts:
                    post = posts[0]
                    created = False
                else:
                    post = Post.objects.language(lang).create(
                        **{
                            "author": author,
                            "date_created": date,
                            "date_modified": date,
                            "date_published": date if item["published"] else None,
                            "publish": item["published"],
                            "enable_comments": False,
                            "app_config_id": 1,
                            "title": item["title"],
                            "slug": slug,
                            "post_text": item["content"],
                        }
                    )
                    created = True

                post.sites.add(self.SITE)

                if created:
                    logging.info("Creating: %s\n", item["title"])
                    add_plugin(
                        post.content,
                        "TextPlugin",
                        settings.LANGUAGE_CODE,
                        body=post.post_text,
                    )
                print("Fixing", item["title"], item["slug"])
                self.fix_text_plugin(post, entry_content=item["content"])
                post.save()
                if old_slug != slug:
                    red, created = Redirect.objects.get_or_create(
                        site=self.SITE,
                        old_path="/blog/%s/%s/" % (date.year, slug),
                        new_path=post.get_absolute_url(),
                    )
            if meta.get("redirect_from"):
                red, created = Redirect.objects.get_or_create(
                    site=self.SITE,
                    old_path="/blog/" + meta.get("redirect_from"),
                    new_path="/blog/" + link,
                )

    def get_posts(self, filenames):
        for filename in filenames:
            yield self.get_post(filename)

    def get_post(self, filename):
        with open(filename) as f:
            content = f.read()

        _, meta, html = content.split(YAML_SEPARATOR)

        meta = yaml.load(meta)
        basename = os.path.basename(filename)
        basename = basename.split(".")[0]
        parts = basename.split("-")
        date = get_date("-".join(parts[:3]))
        slug = "-".join(parts[3:])
        link = "%s/%s/" % (date.year, slug)
        if "date" in meta:
            date = get_date(meta["date"])

        if filename.endswith(("markdown", "md")):
            html = markdown.markdown(html)

        return {
            "meta": meta,
            "title": meta["title"],
            "link": link,
            "slug": slug,
            "date": date,
            "language": settings.LANGUAGE_CODE,
            "content": clean_content(html),
            "published": meta.get("published", True),
            "author": self.get_author(meta.get("author", None)),
        }

    def get_author(self, name):
        if name is None:
            return None
        first_name, last_name = name.split(" ", 1)
        users = User.objects.filter(first_name=first_name, last_name=last_name)
        if not users:
            return None
        return users[0]

    def get_image(self, image_url):
        resp = requests.get(image_url)
        if resp.status_code != 200:
            print("Warning: %s does not exist" % image_url)
            return None
        img_tmp = NamedTemporaryFile(delete=False)
        img_tmp.write(resp.content)
        img_tmp.flush()
        img_tmp.close()
        filename = os.path.basename(image_url)
        return File(open(img_tmp.name, "rb"), name=filename)

    def get_filer_image(self, image_url=None, file_obj=None, name="", description=""):
        if image_url is not None:
            file_obj = self.get_image(image_url)
        if file_obj is None:
            return None
        return Image.objects.create(
            name=name,
            description=description,
            original_filename=os.path.basename(file_obj.name),
            file=SimpleUploadedFile(name=file_obj.name, content=file_obj.read()),
        )

    def fix_text_plugin(self, entry, entry_content=None):
        placeholder = entry.content
        plugins = placeholder.get_plugins()

        for plugin in plugins:
            if plugin.plugin_type != "TextPlugin":
                continue

            changed = False
            text_plugin = plugin.djangocms_text_ckeditor_text
            # content = text_plugin.body
            content = entry_content

            cleaned_content = clean_content(content)
            if cleaned_content != content:
                changed = True
                content = cleaned_content

            if not content:
                continue
            dom = etree.fromstring(content, etree.HTMLParser())

            for script in dom.xpath(".//script"):
                script.getparent().remove(script)

            abstract = None
            strongs = dom.xpath(".//strong")
            if len(strongs):
                abstract = get_inner_html(strongs[0])
                strongs[0].getparent().remove(strongs[0])

            changed = self.fix_images(plugin, dom, entry) or changed

            if changed:
                content = "".join(
                    [
                        etree.tostring(n, pretty_print=True).decode("utf-8")
                        for n in dom.xpath(".//body/*")
                    ]
                )
                content = content.strip()
                entry.post_text = content
                if abstract is not None:
                    entry.abstract = abstract
                text_plugin.body = content
                text_plugin.save()

    def fix_images(self, plugin, dom, entry):
        found = False
        CMSPlugin.objects.filter(parent=plugin, plugin_type="PicturePlugin").delete()
        for counter, img in enumerate(dom.xpath("//img")):
            src = img.attrib["src"]
            alt = img.attrib.get("alt") or ""
            imgid = img.attrib.get("id")
            logging.info("Extracting image %s: %s", imgid, src)
            print("image src", src)
            # if img.getparent().tag == 'a':
            #     link = img.getparent()
            #     link.getparent().replace(link, img)

            if imgid is not None and imgid.startswith("plugin_obj_"):
                plugin_id = imgid.rsplit("_", 1)[0]
                plugin_id
                continue

            found = True
            image_plugin = None
            filer_image = None

            if src.startswith("http"):
                file_obj = self.get_image(src)
                if file_obj is not None:
                    filer_image = self.get_filer_image(file_obj=file_obj, name=alt)
            else:
                src_part = src.split("/")[-1].lower()
                filer_images = Image.objects.filter(file__endswith=src_part)
                if not filer_images:
                    if src.startswith("/"):
                        src_part = src[1:]
                        print("trying import from local folder")
                        image_file = os.path.join(self.directory, "..", src_part)
                        if os.path.exists(image_file):
                            with open(image_file, "rb") as file_obj:
                                filer_image = self.get_filer_image(
                                    file_obj=file_obj, name=alt
                                )
                            print("import success")
                        else:
                            print("image not found at", image_file)
                    else:
                        print("Could not find image", src_part)
                else:
                    filer_image = filer_images[0]

            if not entry.main_image:
                entry.main_image = filer_image
                img.getparent().remove(img)
            else:
                image_plugin = create_image_plugin(
                    None,
                    None,
                    filer_image=filer_image,
                    parent_plugin=plugin,
                    caption=alt,
                    description=src,
                    counter=counter,
                )

            if image_plugin:
                # render the new html for the plugin
                new_img_html = plugin_to_tag(image_plugin)
                # Get single image element
                new_img = etree.HTML(new_img_html).xpath(".//cms-plugin")[0]
                img.getparent().replace(img, new_img)

        return found
