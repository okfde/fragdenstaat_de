import '../styles/main.scss'

import 'froide/frontend/javascript/main.ts'

import './misc.ts'
import './donation.ts'
import './donation-form.ts'
import './betterplace.ts'
import './magnifier.ts'

if (document.body.dataset.raven) {
  import(/* webpackChunkName: "@sentry/browser" */ '@sentry/browser').then((Sentry) => {
    Sentry.init({
      dsn: document.body.dataset.raven
    })
  })
}
