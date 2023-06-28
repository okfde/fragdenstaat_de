import '../styles/main.scss'

import 'froide/frontend/javascript/snippets/bootstrap'
import 'froide/frontend/javascript/snippets/copy-input'
import 'froide/frontend/javascript/snippets/form-ajax'
import 'froide/frontend/javascript/snippets/misc'
import 'froide/frontend/javascript/snippets/search'
import 'froide/frontend/javascript/snippets/inline-edit-forms'
import 'froide/frontend/javascript/snippets/color-mode'

import './donation-form'
import './magnifier'
import './misc'
import './slider.js'
import './smooth-scroll'
import './top-banner'

if (document.body.dataset.sentry !== undefined) {
  void import(/* webpackChunkName: "sentry" */ './sentry').then((mod) => {
    if (document.body.dataset.sentry !== undefined) {
      mod.init(document.body.dataset.sentry)
    }
  })
}
