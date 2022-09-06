import * as Sentry from '@sentry/browser'
import { Integrations as TracingIntegrations } from '@sentry/tracing'
import { CaptureConsole as CaptureConsoleIntegration } from '@sentry/integrations'

export function init(dsn: string): void {
  Sentry.init({
    dsn,
    integrations: [
      new TracingIntegrations.BrowserTracing(),
      new CaptureConsoleIntegration({
        levels: ['error']
      })
    ],
    tracesSampleRate: 1.0
  })
}
