from django.apps import AppConfig


def obj_for_value(self, value):
    '''
    Remove when https://github.com/divio/django-filer/pull/1108
    '''
    if hasattr(self, '_obj'):
        return self._obj
    try:
        key = self.rel.get_related_field().name
        obj = self.rel.model._default_manager.get(**{key: value})
    except (ValueError, self.rel.model.DoesNotExist):
        obj = None
    self._obj = obj
    return obj


class BlogConfig(AppConfig):
    name = 'fragdenstaat_de.fds_blog'
    verbose_name = 'FragDenStaat Blog'

    def ready(self):
        '''
        Remove when https://github.com/divio/django-filer/issues/1103
        '''
        from filer.fields.file import AdminFileWidget

        AdminFileWidget.Media.js = (
            'admin/js/vendor/jquery/jquery.js',
            'admin/js/jquery.init.js',
        ) + AdminFileWidget.Media.js

        AdminFileWidget.obj_for_value = obj_for_value

        from froide.account import account_merged

        account_merged.connect(merge_user)


def merge_user(sender, old_user=None, new_user=None, **kwargs):
    from .models import Author, ArticleAuthorship

    old_exists = Author.objects.filter(user=old_user).exists()
    new_exists = Author.objects.filter(user=new_user).exists()

    if old_exists and new_exists:
        old_author = Author.objects.get(user=old_user)
        new_author = Author.objects.get(user=new_user)
        ArticleAuthorship.objects.filter(
            author=old_author
        ).update(author=new_author)
    elif old_exists:
        Author.objects.filter(user=old_user).update(user=new_user)
