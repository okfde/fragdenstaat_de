# On main page
- cms/base.html works like normal
- gegenrechtsschutz.html
    -> extends cmssites/grs_base.html via MAINSITE_BASE_TEMPLATE injected via theme settings checking current page's site

# On CMS site
- cms/base.html looks up cmssites/cms/base.html first
    -> extends CMSSITE_BASE_TEMPLATE = cmssites/grs_base.html
    -> extends cms/base.html again which goes to default cms/base.html
- gegenrechtsschutz.html
    -> can't find MAINSITE_BASE_TEMPLATE, defaults to cms/base.html
    -> see above
