import "../styles/main.scss";

import "es6-promise/auto";

import "bootstrap.native";

import "froide/frontend/javascript/snippets/copy-input.ts";
import "froide/frontend/javascript/snippets/form-ajax.ts";
import "froide/frontend/javascript/snippets/misc.ts";
import "froide/frontend/javascript/snippets/search.ts";

import "./drawer-menu.ts";
import "./top-menu.ts";
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
