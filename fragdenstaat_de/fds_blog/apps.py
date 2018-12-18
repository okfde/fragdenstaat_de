from django.apps import AppConfig


class BlogConfig(AppConfig):
    name = 'fragdenstaat_de.fds_blog'
    verbose_name = 'FragDenStaat Blog'

    def ready(self):
        from filer.fields.file import AdminFileWidget

        AdminFileWidget.Media.js = (
            'admin/js/vendor/jquery/jquery.js',
            'admin/js/jquery.init.js',
        ) + AdminFileWidget.Media.js
