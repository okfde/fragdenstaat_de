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
  const destroy = (): void => {
    inner.style.maxHeight = 'none'
    element.classList.remove('reveal-cutoff', 'transitioning')
    inner.classList.remove('reveal-inner')
    button?.parentElement?.remove()
  }

  if (
    window.location.hash !== '' &&
    element.querySelector(window.location.hash) != null
  ) {
    destroy()
  }

  button?.addEventListener('click', () => {
    button.setAttribute('aria-expanded', 'true')
    inner.addEventListener(
      'transitionend',
      () => {
        destroy()
      },
      { once: true }
    )
    element.classList.add('transitioning')
  })
})
