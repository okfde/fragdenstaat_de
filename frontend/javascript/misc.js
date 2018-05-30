window.addEventListener('message', function (e) {
  if (e.origin !== 'https://okfde.github.io' && e.origin !== 'http://127.0.0.1:8001') { return }
  if (e.data[0] !== 'setIframeHeight') { return }
  var iframeId = e.data[1]
  var iframe = document.getElementById(iframeId)
  iframe.height = e.data[2] + 'px'
}, false)

window.document.addEventListener('securitypolicyviolation', (e) => {
  if (e.violatedDirective.indexOf('script') !== -1 && e.blockedURI.indexOf('https://data1.') !== -1) {
    window.alert('Liebe/r Nutzer/in,\noffenbar versucht eine Ihrer Browser-Erweiterungen Sie vermutlich ohne Ihre Kenntnis zu tracken.\n\nWir raten Ihnen Browser-Erweiterungen zu deinstallieren, die Sie nicht nutzen.')
  }
})
