# fds_easylang

Plain-language ("Leichte Sprache") variant of the site, served under the
`de-ls` language code alongside the regular `de` content.

All files related to "Leichte Sprache" (templates, static assets, template
tags, tests) live in this app so they are easy to find and maintain.

However, the CSS lives under `frontend/` alongside the rest of the site's
styles so it can share the build pipeline and design tokens.

## Why a separate language code?

Modeling `de-ls` as its own language lets us reuse Django's i18n machinery
and the CMS translation features for content (CMS pages, blog articles).

From a user's perspective, however, "Leichte Sprache" is not just another
language: it is a different style of German that affects writing, layout,
and visual design. The layout should be much simpler and less distracting
than the default. `de-ls` content therefore also relies on dedicated,
stripped-down templates and styles.

`de-ls` is in `settings.LANGUAGES` but **not** in `settings.USER_LANGUAGES`,
so it does not appear in the general language switcher. It is exposed only
through this app's dedicated toggle button. The regular language switcher
is not expected to appear on `de-ls` pages; if it does, the active language
will not be highlighted — by design.

Links on `de-ls` content pages should point to other `de-ls` pages whenever
possible.

## `EASYLANG_ENABLED`

Global on/off flag for end-user access to `de-ls` (default `False`).

- Hides/exposes the easylang toggle.
- Hides `de-ls` blog articles from non-staff users.
- While off, non-staff visitors get a 404 on `de-ls` CMS pages.

Staff users bypass the gate, so editors can author and review `de-ls`
content in production before the public flip.

## URL routing

Handled by `theme.cms_utils.LanguageUtilsMiddleware` (site-wide):

- Non-CMS URLs under `/de-ls/...` are 301-redirected to the default
  language. Easy Language has no per-view translation for pages like
  account or admin.
- `/admin/` is exempt so editors can work on `de-ls` CMS pages.
- CMS pages without a published `de-ls` translation fall back to `de` via
  CMS's `redirect_on_fallback`.

## The toggle

`{% easylang_toggle %}` (`templatetags/easylang_tags.py`) renders a single
button that flips between `de` and `de-ls`. The target URL points to the
actual translation when one exists:

- plain CMS pages with a published `de-ls` translation,
- CMS apphook root pages with a published `de-ls` translation,
- blog articles linked by shared `uuid` between `de` and `de-ls`.

Otherwise (non-CMS pages, apphook subpages, missing translation) it falls
back to the language home (`/de-ls/` or `/de/`).

## Blog template overrides

`BaseBlogView` and `ArticleDetailView` prepend a language-prefixed template
path (e.g. `de-ls/fds_blog/article_list.html`) before the default, so
editors can override individual blog templates for Easy Language without
touching `de` templates.

Articles are linked across languages by a shared `uuid`. Both the toggle
and the inline language list on the article detail page rely on this.

## Localization

`de-ls` is included in the localization files. Use `make messagesls` to
regenerate the `de-ls` `.po` file — the expectation is to run this only
when new strings need translation.

The number of interface strings that need a `de-ls` translation is
currently very small, so translating them locally (or extracting them for
an external translator) is the most practical option. Integrating `de-ls`
into Weblate would be overkill for now.

- Strings without a `de-ls` translation fall back to `de`.
- Strings that are explicitly only relevant for LS content can be marked
  with the gettext context `Leichte Sprache`.

## Setting up `de-ls` content

Initial setup steps to bring a `de-ls` site online. Most of this is done
once; only the per-article steps recur.

- **Create the CMS pages in `de-ls`** — In the CMS, switch the language to
  "Deutsch (Leichte Sprache)" and add translations for the pages that should
  be available in Easy Language:
  - **Start** — use the *Page template (Easy Language)*.
  - **Artikel** (blog landing) — use the *Blog base template (Easy 
    Language)*. This is the apphook root for `de-ls` blog articles.
  - **Recherchen** — set up as a redirect to the Artikel page.
- **Translate blog categories** used by `de-ls` articles.
- **Create a footer alias** under "Deutsch (Leichte Sprache)" (not under
   "Deutsch"!) so the `de-ls` pages render their own simplified footer.
- **Create blog articles in `de-ls`** — Each `de-ls` article should be linked
  to its `de` counterpart. This can be done with the admin action to mark articles
  as translations of each other.
