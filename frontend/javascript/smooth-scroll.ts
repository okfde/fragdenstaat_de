const anchors: NodeListOf<HTMLAnchorElement> = document.querySelectorAll('a.smooth-scroll')
anchors.forEach(element => {
  element.addEventListener('click', event => {
    event.preventDefault()

    const { hash, href } = element
    window.history.pushState({}, '', href)

    const target = document.querySelector(hash)
    target?.scrollIntoView({ behavior: 'smooth' })
  })
})