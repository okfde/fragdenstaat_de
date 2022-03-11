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

  const button = element.querySelector<HTMLElement>('.reveal-show a');

  button?.addEventListener('click', () => {
    inner.addEventListener('transitionend', () => {
      button.ariaExpanded = 'true';

      element.classList.add('revealed')
      element.classList.remove('transitioning')
    }, { once: true })
    element.classList.add('transitioning')
  })
})