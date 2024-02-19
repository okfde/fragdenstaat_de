import transitionDone from './misc/await-transition'

const header = document.querySelector('#header')
let open: HTMLElement | undefined = undefined
let hide: () => void = () => {}

const menuToggles = [
  ...(header?.querySelectorAll<HTMLElement>('.nav-toggle-menu') ?? [])
]

menuToggles.forEach((el) =>
  el.addEventListener('click', async () => {
    const targetName = el.dataset.target
    if (targetName == null) return

    const target = header!.querySelector<HTMLElement>(`#menu-${targetName}`)
    if (target == null) return

    // hide other navs
    const otherNavs = header!.querySelectorAll('.nav-menu')
    otherNavs.forEach((el) => el !== target && el.classList.remove('show'))
    await transitionDone(otherNavs)

    const otherTriggers = header!.querySelectorAll('a[data-target]')
    otherTriggers.forEach((el) => el.setAttribute('aria-expanded', 'false'))

    updateDropdowns()
    if (window.innerWidth >= 992) return

    // hide if it is already open
    if (open === target) return hide()

    const show = !target.classList.contains('show')
    open = target

    target.classList.remove('d-none')

    el.setAttribute('aria-expanded', show ? 'true' : 'false')

    if (show) {
      target.querySelector('a')?.focus()
      target.classList.add('show')
    } else {
      target.classList.remove('show')
    }

    hide = () => {
      target.classList.remove('show')
      el.setAttribute('aria-expanded', 'false')
      open = undefined
    }
  })
)

window.addEventListener('resize', () => hide())

window.addEventListener('click', (e) => {
  if (
    open !== undefined &&
    header?.contains(e.target as HTMLElement) === false
  ) {
    hide()
  }
})

window.addEventListener('scroll', () => {
  if (open && open.clientHeight * 2 < window.scrollY) {
    hide()
  }
})

function updateDropdowns(): void {
  document.querySelectorAll('.nav-dropdown-trigger').forEach((trigger) => {
    const target = trigger.nextElementSibling!
    const el = target.parentElement!

    if (window.innerWidth < 992) {
      el.classList.remove('dropdown')
      target?.classList.remove('dropdown-menu')
      trigger.removeAttribute('data-bs-toggle')
      trigger.classList.remove('dropdown-toggle')

      if (trigger.closest('ul.nav-menu')) {
        trigger.setAttribute('aria-hidden', 'true')
        trigger.setAttribute('tabindex', '-1')
      }

      const dropdown = window.bootstrap.Dropdown.getInstance(trigger)
      dropdown?.dispose()
    } else {
      el.classList.add('dropdown')
      trigger.setAttribute('data-bs-toggle', 'dropdown')
      trigger.removeAttribute('aria-hidden')
      trigger.removeAttribute('tabindex')
      trigger.classList.add('dropdown-toggle')
      target?.classList.add('dropdown-menu')

      window.bootstrap.Dropdown.getOrCreateInstance(trigger)
    }
  })
}

window.addEventListener('resize', updateDropdowns)
updateDropdowns()

const navSearch = header?.querySelector<HTMLElement>('.nav-search')
const searchUrls = [
  ...(navSearch?.querySelector<HTMLSelectElement>('select') ?? [])
].map((el) => el.value)

if (searchUrls.includes(window.location.pathname)) {
  navSearch?.previousElementSibling?.remove()
  navSearch?.remove()
}

const input = navSearch?.querySelector('input')
const placeholder = input?.getAttribute('placeholder') ?? ''
const isMac = navigator.userAgent.includes('Mac OS X')
if (isMac) {
  // macOS
  input?.setAttribute('placeholder', `${placeholder} (⌘ + K)`)
} else {
  input?.setAttribute('placeholder', `${placeholder} (Ctrl + K)`)
}

document.addEventListener('keydown', (e) => {
  if ((isMac ? e.metaKey : e.ctrlKey) && e.key === 'k') {
    e.preventDefault()
    input?.focus()
  }
})
