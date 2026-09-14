function shuffleArray(array: any[]) {
  for (let i = array.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1))
    const temp = array[i]
    array[i] = array[j]
    array[j] = temp
  }
}

document.addEventListener('DOMContentLoaded', () => {
  setTimeout(() => {
    const candidates = [
      document.querySelector<HTMLElement>('article > .blog-content > p'),
      document.querySelector<HTMLElement>('article h1 > span:last-child')
    ].filter((el) => el !== null)

    const redactions: HTMLElement[] = []

    const remove = () => redactions.forEach((r) => r.remove())

    const main = document.querySelector<HTMLElement>('main')!
    main.style.position = 'relative'

    function draw(source: HTMLElement, index = 0) {
      const rect = source.getBoundingClientRect()
      const { fontSize, paddingLeft, paddingRight } = getComputedStyle(source)

      const el = document.createElement('div')
      el.ariaHidden = 'true'
      el.style.background = '#000'
      el.style.color = '#fff'
      el.innerText = 'IFG retten!'
      el.style.fontSize = fontSize
      el.style.padding = '0 0.25rem'

      el.style.position = 'absolute'
      el.style.top = `${rect.top - main.getBoundingClientRect().top}px`
      el.style.left = `calc(${source.offsetLeft}px + ${paddingLeft})`
      el.style.width = `calc(${source.offsetWidth}px - ${paddingLeft} - ${paddingRight})`
      el.style.clipPath = 'polygon(0 0, 0 0, 0 100%, 0% 100%)'
      el.style.transformOrigin = '0 0'
      el.style.transitionProperty = 'clip-path'
      el.style.transitionTimingFunction = index === 0 ? 'ease-in' : 'linear'
      el.style.transitionDuration = '0.2s'
      el.style.transitionDelay = `${index * 0.2}s`
      el.style.cursor = 'pointer'
      el.title = 'Schwärzung entfernen'

      el.addEventListener('click', remove)

      main.appendChild(el)
      redactions.push(el)

      setTimeout(
        () => (el.style.clipPath = 'polygon(0 0, 100% 0, 100% 100%, 0% 100%)'),
        100
      )
    }

    shuffleArray(candidates)
    candidates.slice(0, 2).forEach((c, i) => draw(c, i))

    window.addEventListener('resize', remove)
  }, 300)
})
