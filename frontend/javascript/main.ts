import '../styles/main.scss'

import 'froide/frontend/javascript/snippets/bootstrap.ts'
import 'froide/frontend/javascript/snippets/copy-input.ts'
import 'froide/frontend/javascript/snippets/form-ajax.ts'
import 'froide/frontend/javascript/snippets/misc.ts'
import 'froide/frontend/javascript/snippets/search.ts'
import 'froide/frontend/javascript/snippets/inline-edit-forms.ts'

import './donation-form.ts'
import './drawer-menu.ts'
import './magnifier.ts'
import './misc.ts'
import './slider.js'
import './smooth-scroll.ts'
import './top-banner.ts'

if (document.body.dataset.sentry !== undefined) {
  void import(/* webpackChunkName: "sentry" */ './sentry').then((mod) => {
    if (document.body.dataset.sentry !== undefined) {
      mod.init(document.body.dataset.sentry)
    }
  })
}
