export default async function transitionDone(
  el: HTMLElement | Array<HTMLElement> | NodeList
): Promise<void> {
  if (el instanceof NodeList) {
    await transitionDone([...el] as Array<HTMLElement>)
    return
  }

  if (Array.isArray(el)) {
    await Promise.all(el.map((e) => transitionDone(e)))
    return
  }

  if (el.getAnimations().length !== 0) {
    return new Promise((resolve) =>
      el.addEventListener('transitionend', () => resolve(), { once: true })
    )
  }
}
