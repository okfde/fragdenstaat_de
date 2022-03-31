const revealElemets: NodeListOf<HTMLElement> = document.querySelectorAll('.reveal-cutoff')

revealElemets.forEach((element) => {
  const { cutoff } = element.dataset
  if (cutoff === undefined) return

  let pixels

  if (cutoff.endsWith('px')) {
    pixels = parseFloat(cutoff)
  } else if (cutoff.endsWith('rem')) {
    pixels = parseFloat(cutoff) * parseFloat(getComputedStyle(document.documentElement).fontSize)
  } else if (cutoff.endsWith('rows')) {
    pixels = parseFloat(cutoff) * (element.querySelector<HTMLElement>('.col')?.offsetHeight ?? 0)
  }

  if (pixels === undefined) return

  const inner = element.querySelector<HTMLElement>('.reveal-inner')
  if (inner == null) return
  inner.style.maxHeight = `${pixels}px`

  const button = element.querySelector<HTMLElement>('.reveal-show a')

  button?.addEventListener('click', () => {
    inner.addEventListener('transitionend', () => {
      button.setAttribute('aria-expanded', 'true')

      element.classList.add('revealed')
      element.classList.remove('transitioning')
    }, { once: true })
    element.classList.add('transitioning')
  })
})
