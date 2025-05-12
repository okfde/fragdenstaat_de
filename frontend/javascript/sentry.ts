import {
  captureConsoleIntegration,
  browserTracingIntegration,
  init as initSentry
} from '@sentry/browser'

export function init(dsn: string): void {
  initSentry({
    dsn,
    integrations: [
      browserTracingIntegration(),
      captureConsoleIntegration({
        levels: ['error']
      })
    ]
  })
}
