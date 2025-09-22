window.addEventListener('message', (e) => {
  // datawrapper, see https://developer.datawrapper.de/docs/responsive-iframe#working-with-javascript-restrictions
  if (e.data['datawrapper-height'] !== undefined) {
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
