from django.contrib import admin
from django.http import HttpResponse
from django.core.exceptions import PermissionDenied
from django.shortcuts import render, get_object_or_404
from django.conf.urls import url

from cms.admin.placeholderadmin import PlaceholderAdminMixin

from .models import EmailTemplate


class EmailTemplateAdmin(PlaceholderAdminMixin, admin.ModelAdmin):
    list_display = ('name', 'category', 'created', 'updated',)
    list_filter = (
        'category',
    )
    search_fields = ('name', 'subject',)
    date_hierarchy = 'updated'

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            url(r'^(?P<pk>\d+)/edit-body/$',
                self.admin_site.admin_view(self.edit_body),
                name='fds_mailing-emailtemplate-edit_body'),
            url(r'^(?P<pk>\d+)/preview/$',
                self.admin_site.admin_view(self.preview),
                name='fds_mailing-emailtemplate-preview'),
            url(r'^(?P<pk>\d+)/preview-eml/$',
                self.admin_site.admin_view(self.preview_eml),
                name='fds_mailing-emailtemplate-preview_eml'),
        ]
        return my_urls + urls

    def edit_body(self, request, pk):
        if not self.has_change_permission(request):
            raise PermissionDenied

        email_template = get_object_or_404(EmailTemplate, pk=pk)

        return render(request, 'fds_mailing/emailtemplate_update_form.html', {
            'object': email_template
        })

    def preview(self, request, pk):
        if not self.has_change_permission(request):
            raise PermissionDenied

        email_template = get_object_or_404(EmailTemplate, pk=pk)
        content = email_template.render_email_html().encode('utf-8')
        return HttpResponse(content=content)

    def preview_eml(self, request, pk):
        if not self.has_change_permission(request):
            raise PermissionDenied

        email_template = get_object_or_404(EmailTemplate, pk=pk)
        content = email_template.get_email_bytes({'request': request})
        return HttpResponse(
            content=content, content_type='message/rfc822'
        )


admin.site.register(EmailTemplate, EmailTemplateAdmin)
