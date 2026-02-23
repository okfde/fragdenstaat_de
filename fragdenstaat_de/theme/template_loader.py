from django.template.loaders.app_directories import Loader as AppDirLoader
from django.utils.translation import get_language


class LanguagePrefixLoader(AppDirLoader):
    """
    Template loader that prepends the current language code to template paths.

    For example, when the language is "de-ls" and the template "fds_blog/article_list.html"
    is requested, this loader will first try "de-ls/fds_blog/article_list.html"
    (from any app's templates directory), before falling back to the original path.
    """

    def get_template_sources(self, template_name):
        lang = get_language()
        if lang:
            yield from super().get_template_sources(f"{lang}/{template_name}")
        yield from super().get_template_sources(template_name)
