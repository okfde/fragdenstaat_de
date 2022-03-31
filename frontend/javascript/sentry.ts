
import * as Sentry from '@sentry/browser'
import { Integrations as TracingIntegrations } from '@sentry/tracing'

export function init (dsn: string): void {
  Sentry.init({
    dsn: dsn,
    integrations: [new TracingIntegrations.BrowserTracing()],
    tracesSampleRate: 1.0
  })
}
