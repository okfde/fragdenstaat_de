import '../styles/main.scss'

import 'froide/frontend/javascript/snippets/bootstrap'
import 'froide/frontend/javascript/snippets/copy-text'
import 'froide/frontend/javascript/snippets/form-ajax'
import 'froide/frontend/javascript/snippets/misc'
import 'froide/frontend/javascript/snippets/search'
import 'froide/frontend/javascript/snippets/share-links'
import 'froide/frontend/javascript/snippets/inline-edit-forms'
import 'froide/frontend/javascript/snippets/color-mode'

import './donation-form'
import './magnifier'
import './misc'
import './navbar'
import './slider.js'
import './smooth-scroll'
import './banner'

if (document.body.dataset.sentry !== undefined) {
  void import('./sentry').then((mod) => {
    if (document.body.dataset.sentry !== undefined) {
      mod.init(document.body.dataset.sentry)
    }
  })
}
