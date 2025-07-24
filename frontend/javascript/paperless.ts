// list users

declare global {
  interface Window {
    dismissRelatedLookupPopup: (win: Window, id: number) => void
  }
}

window.dismissRelatedLookupPopup = (win, id) => {
  win.close()
  window.location.href = window.location.pathname + `import/${id}/`
}

document
  .querySelectorAll<HTMLAnchorElement>('#paperless-recipients a')
  .forEach((el) => {
    el.addEventListener('click', (e) => {
      e.preventDefault()
      window.open(el.href, 'picker', 'height=900')
    })
  })

// select documents

const previewDocument = (url: string) => {
  const preview =
    document.querySelector<HTMLIFrameElement>('#paperless-preview')!
  preview.previousElementSibling?.remove()
  preview.classList.remove('d-none')
  preview.src = url
}

document
  .querySelectorAll<HTMLAnchorElement>('.paperless-preview-btn')
  .forEach((el) => {
    el.addEventListener('click', (e) => {
      e.preventDefault()
      previewDocument(el.href)
    })
  })

const checkboxes = [
  ...document.querySelectorAll<HTMLInputElement>(
    '#paperless-documents input[type=checkbox]'
  )
]

const getChecked = () => checkboxes.filter((c) => c.checked)

checkboxes.forEach((el) => {
  el.addEventListener('input', () => {
    // if it is the only checked one
    if (el.checked && getChecked().length === 1) {
      document.querySelector<HTMLInputElement>('#id_date')!.value = new Date(
        el.dataset.date!
      ).toLocaleDateString('de-DE')

      const pdfUrl = (
        el.nextElementSibling!.nextElementSibling as HTMLAnchorElement
      ).href
      previewDocument(pdfUrl)
    }
  })
})
