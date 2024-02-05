import transitionDone from './misc/await-transition'

const header = document.querySelector('#header')
let counter = 0

header?.querySelectorAll<HTMLElement>('.nav-toggle-menu').forEach((el) =>
  el.addEventListener('click', async () => {
    const targetName = el.dataset.target
    if (targetName == null) return

    const target = header.querySelector<HTMLElement>(`#menu-${targetName}`)
    if (target == null) return

    // hide other navs
    const otherNavs = header.querySelectorAll('.nav-menu')
    otherNavs.forEach((el) => el !== target && el.classList.remove('show'))
    await transitionDone(otherNavs)

    const otherTriggers = header.querySelectorAll('a[data-target]')
    otherTriggers.forEach((el) => el.setAttribute('aria-expanded', 'false'))

    counter++

    updateDropdowns()
    if (window.innerWidth >= 768) return

    target.classList.toggle('show')
    target.classList.remove('d-none')
    target.style.visibility = 'visible'

    el.setAttribute(
      'aria-expanded',
      target.classList.contains('show') ? 'true' : 'false'
    )

    if (target.classList.contains('show')) {
      target.querySelector('a')?.focus()
    }

    let id = counter

    const hide = () => {
      if (id === counter) {
        target.classList.remove('show')
        el.setAttribute('aria-expanded', 'false')
      }
    }
    window.addEventListener('resize', hide, { once: true })

    window.requestAnimationFrame(() => {
      window.addEventListener('click', (e) => {
        if (!target.contains(e.target as Element) && id === counter) hide()
      })
    })

    window.addEventListener('scroll', () => {
      if (window.scrollY > 150) hide()
    })
  })
)

function updateDropdowns(): void {
  document.querySelectorAll('.nav-dropdown-trigger').forEach((trigger) => {
    const target = trigger.nextElementSibling!
    const el = target.parentElement!

    if (window.innerWidth < 768) {
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
  navSearch?.remove()
  document.querySelector('#menu-user-nav')?.classList.add('ms-md-auto')
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
