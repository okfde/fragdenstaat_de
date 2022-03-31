import '../styles/main.scss'

import 'es6-promise/auto'

import 'bootstrap.native/dist/bootstrap-native-v4.js'
import 'bootstrap.native/dist/polyfill.js'

import 'froide/frontend/javascript/snippets/copy-input.ts'
import 'froide/frontend/javascript/snippets/form-ajax.ts'
import 'froide/frontend/javascript/snippets/misc.ts'
import 'froide/frontend/javascript/snippets/search.ts'

import './drawer-menu.ts'
import './slider.js'
import './donation-form.ts'
import './top-banner.ts'
import './magnifier.ts'
import './smooth-scroll.ts'
import './misc.ts'

WEBPACK_PUBLIC_PATH = (document.body.dataset.staticurl ?? '/static/') + 'js/'

if (document.body.dataset.sentry !== undefined) {
  void import(/* webpackChunkName: "sentry" */ './sentry').then((mod) => {
    if (document.body.dataset.sentry !== undefined) {
      mod.init(document.body.dataset.sentry)
    }
  })
}
