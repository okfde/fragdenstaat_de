from cms.utils.urlutils import static_with_version
from djangocms_text.editors import RTEConfig

ckeditor4 = RTEConfig(
    name="ckeditor4",
    config="CKEDITOR",
    js=(
        static_with_version("cms/js/dist/bundle.admin.base.min.js"),
        "djangocms_text/vendor/ckeditor4/ckeditor.js",
        "djangocms_text/bundles/bundle.ckeditor4.min.js",
    ),
    css={"all": ("djangocms_text/css/cms.ckeditor4.css",)},
    inline_editing=False,
    child_plugin_support=True,
)
