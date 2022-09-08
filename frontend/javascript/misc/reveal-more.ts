const revealElemets: NodeListOf<HTMLElement> =
  document.querySelectorAll('.reveal-cutoff')

revealElemets.forEach((element) => {
  let { cutoff } = element.dataset
  if (cutoff === undefined) return

  const originalHeight = element.offsetHeight
  let pixels = parseFloat(cutoff)

  if (cutoff.endsWith('rows')) {
    pixels =
      parseFloat(cutoff) *
      (element.querySelector<HTMLElement>('.col')?.offsetHeight ?? 0)
    cutoff = `${pixels}px`
  } else if (cutoff.endsWith('rem')) {
    pixels *= parseFloat(getComputedStyle(document.documentElement).fontSize)
  }

  const inner = element.querySelector<HTMLElement>('.reveal-inner')
  if (inner == null) return
  inner.style.maxHeight = cutoff

  const button = element.querySelector<HTMLElement>('.reveal-show a')
  const destroy = (): void => {
    inner.style.maxHeight = 'none'
    element.classList.remove('reveal-cutoff', 'transitioning')
    inner.classList.remove('reveal-inner')
    button?.parentElement?.remove()
  }

  const anchored = (): boolean => {
    try {
      return element.querySelector(window.location.hash) != null
    } catch {
      return false
    }
  }

  anchored() && destroy()
  window.addEventListener('hashchange', () => {
    anchored() && destroy()
  })

  // if we only save around half the height, it's not worth it
  if (originalHeight / pixels < 1.9) {
    destroy()
  }

  button?.addEventListener('click', () => {
    button.setAttribute('aria-expanded', 'true')
    inner.addEventListener('transitionend', () => destroy(), { once: true })
    element.classList.add('transitioning')
  })
})
