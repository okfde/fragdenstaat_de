window.addEventListener('message', (e) => {
  if (
    e.origin === 'https://okfde.github.io' ||
    e.origin === 'http://127.0.0.1:8001'
  ) {
    if (e.data[0] !== 'setIframeHeight') return
    const iframeId = e.data[1]
    const height: string = e.data[2]
    const iframe = document.getElementById(iframeId)
    if (iframe !== null) {
      iframe.style.height = `${height}px`
    }
  }
  // datawrapper, see https://developer.datawrapper.de/docs/responsive-iframe#working-with-javascript-restrictions
  else if (e.origin === 'null' && e.data['datawrapper-height'] !== undefined) {
    const iframes = document.querySelectorAll<HTMLIFrameElement>('iframe')
    for (const chartId in e.data['datawrapper-height']) {
      for (const frame of iframes) {
        // this check is important to ensure we don't accept messages from other origins
        if (frame.contentWindow === e.source) {
          frame.style.height = e.data['datawrapper-height'][chartId] + 'px'
        }
      }
    }
  }
})
