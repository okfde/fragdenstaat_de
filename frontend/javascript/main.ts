import '../styles/main.scss'

import { Modal, Dropdown, Collapse, Alert, Tab, Tooltip } from 'bootstrap'

import 'froide/frontend/javascript/snippets/copy-input.ts'
import 'froide/frontend/javascript/snippets/form-ajax.ts'
import 'froide/frontend/javascript/snippets/misc.ts'
import 'froide/frontend/javascript/snippets/search.ts'
import 'froide/frontend/javascript/snippets/inline-edit-forms.ts'

import './donation-form.ts'
import './drawer-menu.ts'
import './magnifier.ts'
import './misc.ts'
import './public-path.ts'
import './slider.js'
import './smooth-scroll.ts'
import './top-banner.ts'
console.log(Modal, Dropdown, Collapse, Alert, Tab, Tooltip)

if (document.body.dataset.sentry !== undefined) {
  void import(/* webpackChunkName: "sentry" */ './sentry').then((mod) => {
    if (document.body.dataset.sentry !== undefined) {
      mod.init(document.body.dataset.sentry)
    }
  })
}
