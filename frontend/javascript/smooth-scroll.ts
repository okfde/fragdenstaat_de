const anchors: NodeListOf<HTMLAnchorElement> =
  document.querySelectorAll('a.smooth-scroll')
anchors.forEach((element) => {
  element.addEventListener('click', (event) => {
    const a = event.target as HTMLAnchorElement
    if (
      a.host !== window.location.host ||
      a.pathname !== window.location.pathname
    )
      return
    event.preventDefault()

    const { hash, href } = element
    window.history.pushState({}, '', href)

    const target = document.querySelector(hash)
    target?.scrollIntoView({ behavior: 'smooth' })
  })
})
