const MATOMO_DOMAIN = 'https://traffic.okfn.de'

window._paq = window._paq ?? []
window._paq.push(['trackPageView'])
window._paq.push(['enableLinkTracking'])
window._paq.push(['setDomains', [document.location.host]])
window._paq.push(['setTrackerUrl', `${MATOMO_DOMAIN}/matomo.php`])
window._paq.push(['disableCookies'])
window._paq.push(['disableBrowserFeatureDetection'])

const matomoId = document.body.dataset.matomoid
if (matomoId) {
  window._paq.push(['setSiteId', matomoId])
  const script = document.createElement('script')
  script.type = 'text/javascript'
  script.async = true
  script.defer = true
  script.src = `${MATOMO_DOMAIN}/matomo.js`
  document.body.appendChild(script)
}
