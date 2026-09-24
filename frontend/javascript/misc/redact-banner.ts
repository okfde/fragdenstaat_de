// dev: localStorage.removeItem('redact-banner-dismissed')
const STORAGE_KEY = 'redact-banner-dismissed'
// once dismissed, stay hidden this long — so a later campaign can show again
// const DISMISSAL_DURATION = 1000 * 60 * 60 * 24 * 90 // 90 days
const CAMPAIGN_URL = '/ifg-retten/'
const LABEL = 'INFORMATIONSFREIHEIT RETTEN!'
// opposing angles so the two tapes cross in an X; offset spreads them apart
// from the shared centre point
const TAPES = [
  { angle: 18, offset: '-12vw', delay: 0 },
  { angle: -25, offset: '5vw', delay: 0.25 },
  { angle: -75, offset: '-20vw', delay: 0.5 }
]

/** localStorage keeps no metadata, so the dismissal time is stored explicitly. */
function isDismissed(): boolean {
  const timestamp = Number(localStorage.getItem(STORAGE_KEY))
  return timestamp > 0 // && Date.now() - timestamp < DISMISSAL_DURATION
}

function rememberDismissal() {
  localStorage.setItem(STORAGE_KEY, String(Date.now()))
}

function injectStyles() {
  const style = document.createElement('style')
  style.textContent = `
    .redact-tapes {
      position: fixed;
      inset: 0;
      z-index: 1080;
      overflow: hidden;
      pointer-events: none;
    }

    .redact-tape {
      position: absolute;
      /* anchored to the viewport centre so the two tapes always cross there,
         regardless of screen width */
      top: 50%;
      left: 50%;
      width: 160vmax;
      margin-left: -80vmax;
      padding: clamp(1rem, 2.2vw, 1.8rem) 0;
      background: #2e2e2e;
      color: #fff;
      display: flex;
      justify-content: center;
      gap: clamp(3rem, 4vw, 6rem);
      white-space: nowrap;
      box-shadow: 0 0.4rem 1.2rem rgba(0, 0, 0, 0.5);
      transform-origin: center center;
      /* rotate first, so --offset shifts the tape perpendicular to its own
         length instead of straight down the viewport */
      transform: translateY(-50%) rotate(var(--angle)) translateY(var(--offset));
      /* clipped, not scaled, so the text keeps its size while rolling out.
         negative top/bottom leaves room for the shadow inside the clip */
      clip-path: inset(-3rem 100% -3rem 0);
      transition: clip-path 0.9s ease-in-out;
    }

    .redact-tapes.is-rolled .redact-tape {
      clip-path: inset(-3rem -3rem -3rem 0);
    }

    .redact-tape span {
      font-family: var(--bs-font-sans-serif, sans-serif);
      font-size: clamp(1.6rem, 5vw, 4rem);
      font-weight: 700;
      letter-spacing: 0.02em;
    }

    .redact-tapes-actions {
      position: absolute;
      inset: 0;
      z-index: 1; /* above the tapes */
      display: flex;
      align-items: flex-end;
      justify-content: center;
      padding-bottom: 12vh;
    }

    .redact-tapes-more {
      pointer-events: auto;
      background: #2e2e2e;
      color: #fff;
      font-size: clamp(1.1rem, 2.5vw, 1.6rem);
      padding: 0.6rem 1.4rem;
      border-radius: 2rem;
      text-decoration: none;
      box-shadow: 0 0.3rem 1rem rgba(0, 0, 0, 0.4);
      opacity: 0;
      transition: opacity 0.4s ease-out 0.9s;
    }

    .redact-tapes.is-rolled .redact-tapes-more { opacity: 1; }
    .redact-tapes-more:hover { text-decoration: underline; color: #fff; }

    .redact-tapes-close {
      position: absolute;
      top: 1.5rem;
      right: 1.5rem;
      pointer-events: auto;
      background: #2e2e2e;
      border: 0;
      border-radius: 50%;
      padding: 0.6rem;
      line-height: 1;
      cursor: pointer;
      color: #fff;
      box-shadow: 0 0.3rem 1rem rgba(0, 0, 0, 0.4);
    }

    .redact-tapes-close svg { display: block; width: 2rem; height: 2rem; }

    .redact-tapes-more:focus-visible,
    .redact-tapes-close:focus-visible {
      outline: 3px solid #fff;
      outline-offset: 3px;
    }

    @media (prefers-reduced-motion: reduce) {
      .redact-tape {
        transition: none;
        transition-delay: 0s !important; /* the stagger is set inline */
        clip-path: inset(-3rem -3rem -3rem 0);
      }
      .redact-tapes-more { transition: none; opacity: 1; }
    }
  `
  document.head.appendChild(style)
}

function build(): HTMLElement {
  const root = document.createElement('div')
  root.className = 'redact-tapes'
  root.setAttribute('role', 'region')
  root.setAttribute('aria-label', LABEL)

  for (const { angle, offset, delay } of TAPES) {
    const tape = document.createElement('div')
    tape.className = 'redact-tape'
    tape.ariaHidden = 'true'
    tape.style.setProperty('--angle', `${angle}deg`)
    tape.style.setProperty('--offset', offset)
    tape.style.transitionDelay = `${delay}s`

    // repeated so the text keeps reading across the full width
    for (let i = 0; i < 6; i++) {
      const label = document.createElement('span')
      label.textContent = LABEL
      tape.appendChild(label)
    }
    root.appendChild(tape)
  }

  const actions = document.createElement('div')
  actions.className = 'redact-tapes-actions'

  const more = document.createElement('a')
  more.className = 'redact-tapes-more'
  more.href = CAMPAIGN_URL
  more.textContent = 'mehr erfahren →'
  // "mehr erfahren" alone gives no context out of the link list
  more.setAttribute('aria-label', `${LABEL} – mehr erfahren`)

  const close = document.createElement('button')
  close.type = 'button'
  close.className = 'redact-tapes-close'
  close.setAttribute('aria-label', 'Schließen')
  close.innerHTML =
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><path d="M4 4l16 16M20 4L4 20"/></svg>'

  // close before the link, so tabbing runs close → link → rest of page
  actions.append(close, more)

  root.append(actions)
  return root
}

document.addEventListener('DOMContentLoaded', () => {
  if (isDismissed()) return
  if (location.pathname !== '/' && !location.pathname.startsWith('/artikel'))
    return

  injectStyles()
  const root = build()
  document.body.appendChild(root)

  const closeButton = root.querySelector<HTMLButtonElement>(
    '.redact-tapes-close'
  )

  const dismiss = () => {
    rememberDismissal()
    root.remove()
    document.removeEventListener('keydown', onKeydown)
  }

  function onKeydown(e: KeyboardEvent) {
    if (e.key === 'Escape') dismiss()
  }

  closeButton?.addEventListener('click', dismiss)
  // following the link counts as dismissing: mark it before navigating away
  root
    .querySelector('.redact-tapes-more')
    ?.addEventListener('click', rememberDismissal)
  document.addEventListener('keydown', onKeydown)

  // the overlay sits at the end of the body, so without this a keyboard user
  // would have to tab through the whole page to dismiss it
  closeButton?.focus()

  requestAnimationFrame(() => root.classList.add('is-rolled'))
})
