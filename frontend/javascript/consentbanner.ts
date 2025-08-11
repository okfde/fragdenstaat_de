import { Modal } from 'bootstrap'

const DEFAULT_FETCH_HEADERS = {
  'X-Cookie-Consent-Fetch': '1'
}

document
  .querySelectorAll<HTMLElement>('.cookie-consent')
  .forEach(async (container) => {
    const consentMessage = container
      .querySelector<HTMLTemplateElement>('.cookie-consent__message')!
      .content.cloneNode(true) as Element

    let modal: Modal | undefined

    const accepted = () => {
      modal?.hide()

      const { content } = container.querySelector<HTMLTemplateElement>(
        '.cookie-consent__content'
      )!

      content
        .querySelectorAll<HTMLElement>('[data-consent-src]')
        .forEach((el) => {
          el.setAttribute('src', el.dataset.consentSrc!)
          el.removeAttribute('data-consent-src')
        })

      console.log(content)

      container.replaceChildren()
      container.appendChild(content.cloneNode(true))
    }

    const declined = () => {
      modal?.hide()

      const declinedMessage = container
        .querySelector<HTMLTemplateElement>('.cookie-consent__declined')
        ?.content.cloneNode(true)

      if (declinedMessage) {
        container.replaceChildren()
        container.appendChild(declinedMessage)
      } else {
        container.remove()
      }
    }

    const group = container.dataset.cookieGroup!

    const status = await fetch(container.dataset.statusUrl!, {
      credentials: 'same-origin',
      headers: DEFAULT_FETCH_HEADERS
    }).then((r) => r.json())

    const postConsentStatus = async (url: string) => {
      await fetch(url, {
        method: 'POST',
        credentials: 'same-origin',
        headers: DEFAULT_FETCH_HEADERS
      })
    }

    if (status.acceptedCookieGroups.includes(group)) {
      accepted()
    } else if (!status.declinedCookieGroups.includes(group)) {
      let buttonsContainer

      if (consentMessage.firstElementChild?.classList.contains('modal')) {
        // can't append the entire consentMessage, as that's a document fragment,
        // and appendChild returns the copied (now empty!) fragment when appending a document fragment
        const modalEl = document.body.appendChild(
          consentMessage.firstElementChild
        )
        modal = new Modal(modalEl)
        modal.show()
        buttonsContainer = modalEl
      } else {
        container.appendChild(consentMessage)
        buttonsContainer = container
      }

      buttonsContainer
        .querySelector('.cookie-consent__accept')
        ?.addEventListener('click', async () => {
          accepted()
          await postConsentStatus(container.dataset.acceptUrl!)
        })

      buttonsContainer
        .querySelector('.cookie-consent__decline')
        ?.addEventListener('click', async () => {
          declined()
          await postConsentStatus(container.dataset.declineUrl!)
        })
    } else {
      declined()
    }
  })
