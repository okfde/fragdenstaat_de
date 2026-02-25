# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

FragDenStaat.de is the German Freedom of Information (FOI) portal, built as a theme/plugin layer on top of the [froide](https://github.com/okfde/froide) core platform. It uses Django 5.2, django-cms 5.x, PostgreSQL 16 with PostGIS, Elasticsearch 8, and Celery. The frontend uses TypeScript, Vue 3, SCSS (Bootstrap 5), and Vite 7.

## Common Commands

### Backend
```bash
make test                    # Lint (ruff) + pytest
pytest --reuse-db            # Run tests directly (faster re-runs)
pytest tests/path/test_file.py::TestClass::test_method --reuse-db  # Single test
ruff check                   # Lint only
ruff check --fix             # Lint + autofix
```

### Frontend
```bash
pnpm run dev                 # Dev server with HMR (port 5173)
pnpm run build               # Production build to ./build/
pnpm run lint                # ESLint
```

### Translations
```bash
make messagesde              # Generate German .po files
make messagesls              # Generate Easy Language (de_LS) .po files
python manage.py compilemessages -i node_modules -l de
python manage.py compilemessages -i node_modules -l de_LS
```

### Dependencies
```bash
make dependencies            # Recompile backend + frontend deps
bash devsetup.sh             # Full environment bootstrap (clones froide repos, installs everything)
```

## Architecture

### Froide Ecosystem
This repo is a **theme layer** over `froide`. Many `froide-*` packages (froide-campaign, froide-payment, froide-legalaction, django-filingcabinet, etc.) are installed from GitHub `@main`. During development, all froide repos are expected as **sibling directories** and frontend packages are pnpm-linked from them.

### Django Apps (in `fragdenstaat_de/`)
- `theme/` — Core: URL routing, views, template tags, middleware
- `fds_blog/` — Blog/articles
- `fds_cms/` — django-cms plugins and page integration
- `fds_donation/` — Donations (Stripe, PayPal, bank transfer, SEPA)
- `fds_events/` — Events
- `fds_mailing/` — Newsletter sending and tracking
- `fds_newsletter/` — Newsletter subscriber management
- `fds_ogimage/` — Open Graph image generation
- `fds_easylang/` — "Leichte Sprache" (Easy Language) support

### Settings
Uses `django-configurations` (class-based). Key classes:
- `settings.base.FragDenStaatBase` — shared base (inherits `froide.settings.Base`)
- `settings.development.Dev` — local development (default)
- `settings.test.Test` — test runner
- `settings.local_settings.py` — gitignored local overrides (copy from `.example`)

Set via `DJANGO_CONFIGURATION` (class name) and `DJANGO_SETTINGS_MODULE` (module path).

### Frontend Build
Vite with multiple entry points defined in `vite.config.ts` (main, request, document, payment, campaign_list, etc.). Assets output to `./build/` with `manifest.json` for Django integration. Dev server uses `vite-plugin-dev-manifest` for HMR with Django.

### Languages
Three languages: `de` (German), `de-ls` (Easy Language), `en` (English). Templates for `de-ls` are resolved via `LanguagePrefixLoader` which looks up language-prefixed template paths first.

## Code Style

### Python
- **Ruff** for linting and formatting (pre-commit enforced)
- Import order: standard-library → django → third-party → froide → first-party → local-folder (ruff isort sections)
- Line length and complexity rules (E501, C901) are disabled

### Frontend
- TypeScript strict mode
- ESLint with `@okfde/eslint-config-froide`
- Vue 3 single-file components

### Templates
- **djlint** for Django template linting and formatting (pre-commit enforced)

## Testing

- `pytest` with `--reuse-db` for speed
- Use parametrized tests if it makes sense.
- Markers: `@pytest.mark.stripe`, `@pytest.mark.paypal` (skipped without keys), `@pytest.mark.elasticsearch` (needs running ES)
- CI runs on Python 3.12 and 3.13 with PostgreSQL + Elasticsearch services

## Infrastructure

- Local dev services via `compose-dev.yaml`: PostgreSQL 16 + PostGIS, Elasticsearch 8
- Default dev DB: `fragdenstaat_de`/`fragdenstaat_de` on `localhost:5432`
- pnpm version pinned to 9.15.x