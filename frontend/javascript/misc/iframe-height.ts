window.addEventListener(
  'message',
  (e) => {
    if (
      e.origin !== 'https://okfde.github.io' &&
      e.origin !== 'http://127.0.0.1:8001'
    ) {
      return
    }

    if (e.data[0] !== 'setIframeHeight') return
    const iframeId = e.data[1]
    const height: string = e.data[2]
    const iframe = document.getElementById(iframeId)
    if (iframe !== null) {
      iframe.style.height = `${height}px`
    }
  },
  false
)
