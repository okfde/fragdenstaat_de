window.addEventListener('message', function (e) {
  if (e.origin !== 'https://okfde.github.io' && e.origin !== 'http://127.0.0.1:8001') { return }
  if (e.data[0] !== 'setIframeHeight') { return }
  var iframeId = e.data[1]
  let iframe = document.getElementById(iframeId)
  if (iframe !== null) {
    iframe.style.height = e.data[2] + 'px'
  }
}, false)

window.document.addEventListener('securitypolicyviolation', (e) => {
  if (e.violatedDirective.indexOf('script') !== -1 && e.blockedURI.indexOf('https://data1.') !== -1) {
    window.alert('Liebe/r Nutzer/in,\noffenbar versucht eine Ihrer Browser-Erweiterungen Sie vermutlich ohne Ihre Kenntnis zu tracken.\n\nWir raten Ihnen Browser-Erweiterungen zu deinstallieren, die Sie nicht nutzen.')
  }
});

(function () {
  const videoEmbed = document.querySelector('.video-embed')
  if (videoEmbed !== null) {
    videoEmbed.addEventListener('click', function (this: HTMLElement, e) {
      e.preventDefault()
      let parent = <HTMLElement> this.parentNode
      if (parent !== null) {
        parent.innerHTML = '<iframe src="' + this.dataset.url + '" frameborder="0" webkitallowfullscreen mozallowfullscreen allowfullscreen></iframe>'
      }
    })
  }
}())

interface Window { _paq: Array<Array<string | string[]>>; }

window._paq = window._paq || []
window._paq.push(['setDomains', ['*.fragdenstaat.de']])
window._paq.push(['trackPageView'])
window._paq.push(['enableLinkTracking'])
window._paq.push(['setTrackerUrl', 'https://traffic.okfn.de/piwik.php'])
window._paq.push(['setSiteId', '25'])
