import "../styles/main.scss";

import "froide/frontend/javascript/main.ts";

import "./betterplace.ts";
import "./donation-form.ts";
import "./donation.ts";
import "./magnifier.ts";
import "./misc.ts";

if (document.body.dataset.raven) {
  import(/* webpackChunkName: "@sentry/browser" */ "@sentry/browser").then((Sentry) => {
    Sentry.init({
      dsn: document.body.dataset.raven,
    });
  });
}
