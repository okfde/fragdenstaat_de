const revealElemets: NodeListOf<HTMLElement> =
  document.querySelectorAll('.reveal-cutoff')

revealElemets.forEach((element) => {
  let { cutoff } = element.dataset
  if (cutoff === undefined) return

  if (cutoff.endsWith('rows')) {
    const pixels =
      parseFloat(cutoff) *
      (element.querySelector<HTMLElement>('.col')?.offsetHeight ?? 0)
    cutoff = `${pixels}px`
  }

  const inner = element.querySelector<HTMLElement>('.reveal-inner')
  if (inner == null) return
  inner.style.maxHeight = cutoff

  const button = element.querySelector<HTMLElement>('.reveal-show a')

  button?.addEventListener('click', () => {
    inner.addEventListener(
      'transitionend',
      () => {
        button.setAttribute('aria-expanded', 'true')

        // remove reveal styles
        inner.style.maxHeight = 'none'
        element.classList.remove('reveal-cutoff', 'transitioning')
        inner.classList.remove('reveal-inner')
        button.parentElement?.remove()
      },
      { once: true }
    )
    element.classList.add('transitioning')
  })
})
