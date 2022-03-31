// tslint:disable-next-line: interface-name
interface Window { _paq: undefined | Array<Array<string | string[]>> }
declare let window: Window

const MATOMO_DOMAIN = 'https://traffic.okfn.de'

window._paq = window._paq ?? []
window._paq.push(['trackPageView'])
window._paq.push(['enableLinkTracking'])
window._paq.push(['setDomains', ['*.fragdenstaat.de']])
window._paq.push(['setTrackerUrl', `${MATOMO_DOMAIN}/matomo.php`])
window._paq.push(['disableCookies'])
// Not yet available on our Matomo
// window._paq.push(["disableBrowserFeatureDetection"]);
window._paq.push(['setSiteId', '25'])

if (!document.location.hostname.includes('.onion')) {
  const script = document.createElement('script')
  script.type = 'text/javascript'
  script.async = true
  script.defer = true
  script.src = `${MATOMO_DOMAIN}/matomo.js`
  document.body.appendChild(script)
}
