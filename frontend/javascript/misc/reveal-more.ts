const revealElemets: NodeListOf<HTMLElement> = document.querySelectorAll('.reveal-cutoff')

revealElemets.forEach((element) => {
  const { cutoff } = element.dataset
  if (!cutoff) return

  let pixels

  if (cutoff.endsWith('px')) {
    pixels = parseFloat(cutoff)
  } else if (cutoff.endsWith('rem')) {
    pixels = parseFloat(cutoff) * parseFloat(getComputedStyle(document.documentElement).fontSize)
  } else if (cutoff.endsWith('rows')) {
    pixels = parseFloat(cutoff) * (element.querySelector<HTMLElement>('.col')?.offsetHeight ?? 0)
  }

  if (!pixels) return

  const inner = element.querySelector<HTMLElement>('.reveal-inner')
  if (!inner) return
  inner.style.maxHeight = `${pixels}px`

  element.querySelector('.reveal-show a')?.addEventListener('click', () => {
    inner.addEventListener('transitionend', () => {
      element.classList.add('revealed')
      element.classList.remove('transitioning')
    }, { once: true })
    element.classList.add('transitioning')
  })
})