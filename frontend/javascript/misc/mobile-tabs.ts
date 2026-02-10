// Render a <select> above Bootstrap nav tabs for small screens; keep tabs on md+
import { Tab } from 'bootstrap'

// Collect tab toggles with their targets and labels
function getToggleTargets(nav: HTMLElement): Array<{ el: HTMLElement; target: string; label: string }> {
  const toggles = Array.from(nav.querySelectorAll<HTMLElement>('.nav-link[data-bs-toggle="tab"]'))
  return toggles
    .map((el) => {
      const target = el.getAttribute('data-bs-target') || (el as HTMLAnchorElement).getAttribute?.('href') || ''
      const label = (el.textContent || '').replace(/\s+/g, ' ').trim()
      return target ? { el, target, label } : null
    })
    .filter((x): x is { el: HTMLElement; target: string; label: string } => x !== null)
}

// Determine tab items for overflow detection
function getTabItems(nav: HTMLElement): HTMLElement[] {
  const items = Array.from(nav.querySelectorAll<HTMLElement>('li.nav-item'))
  if (items.length > 0) return items
  return Array.from(nav.querySelectorAll<HTMLElement>('.nav-link'))
}

// Detect if tabs overflow the container or wrap to a new line
function isOverflowingOrWrapped(nav: HTMLElement): boolean {
  const wasHidden = nav.classList.contains('d-none')
  if (wasHidden) nav.classList.remove('d-none')

  const items = getTabItems(nav)
  if (items.length <= 1) {
    if (wasHidden) nav.classList.add('d-none')
    return false
  }

  const containerWidth = nav.clientWidth
  const totalWidth = items.reduce((sum, el) => sum + el.offsetWidth, 0)
  const firstTop = items[0].offsetTop
  const wrapped = items.some((el) => el.offsetTop > firstTop)
  const overflowing = totalWidth > containerWidth || nav.scrollWidth > nav.clientWidth

  if (wasHidden) nav.classList.add('d-none')
  return wrapped || overflowing
}

// Render <select> and keep it in sync
function initSelectForNavTabs(nav: HTMLElement): void {
  if (nav.dataset.mobileSelectInitialized === 'true') return
  const items = getToggleTargets(nav)
  if (items.length === 0) return

  nav.dataset.mobileSelectInitialized = 'true'

  const select = document.createElement('select')
  select.className = 'form-select mb-0 rounded-0'
  select.setAttribute('aria-label', 'Select tab')
  select.classList.add('d-none')

  items.forEach(({ el, target, label }) => {
    const opt = document.createElement('option')
    opt.value = target
    opt.textContent = label
    if (el.classList.contains('active')) opt.selected = true
    select.appendChild(opt)
  })

  select.addEventListener('change', () => {
    const { value } = select
    const match = items.find((i) => i.target === value)
    if (match) {
      Tab.getOrCreateInstance(match.el).show()
    }
  })

  // Insert select before the tab list
  nav.parentElement?.insertBefore(select, nav)

  // Toggle between select and tab bar based on available space
  function updateVisibility(): void {
    const useSelect = isOverflowingOrWrapped(nav)
    if (useSelect) {
      select.classList.remove('d-none')
      nav.classList.add('d-none')
    } else {
      select.classList.add('d-none')
      nav.classList.remove('d-none')
    }
  }

  updateVisibility()

  let resizeTimer: number | undefined
  window.addEventListener('resize', () => {
    window.clearTimeout(resizeTimer)
    resizeTimer = window.setTimeout(updateVisibility, 100)
  })

  // Reevaluate on content size changes
  if ('ResizeObserver' in window) {
    const ro = new ResizeObserver(() => updateVisibility())
    ro.observe(nav)
    if (nav.parentElement) {
      ro.observe(nav.parentElement)
    }
  }

  window.addEventListener('load', updateVisibility)

  // Keep select in sync when changed back to tab bar
  nav.addEventListener('shown.bs.tab' as any, (e: Event) => {
    const active = e.target as HTMLElement | null
    if (!active) return
    const activeTarget = active.getAttribute('data-bs-target') || (active as HTMLAnchorElement).getAttribute?.('href')
    if (!activeTarget) return
    if (select.value !== activeTarget) {
      select.value = activeTarget
    }
  })
}

function initAll(): void {
  document.querySelectorAll<HTMLElement>('ul.nav.nav-tabs').forEach(initSelectForNavTabs)
}

if (typeof document !== 'undefined') {
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initAll)
  } else {
    initAll()
  }
} 