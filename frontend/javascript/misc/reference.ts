let referenceData: undefined | ReferenceData

type ReferenceData = {
  reference?: string
  keyword?: string
}

function getReferenceData(): ReferenceData {
  if (referenceData !== undefined) return referenceData
  if (URLSearchParams === undefined) return {}

  const urlParams = new URLSearchParams(window.location.search)
  const reference =
    urlParams.get('pk_campaign') ??
    document.location.pathname.split('/')[1] ??
    'homepage'
  const content = urlParams.get('pk_content') || ''
  const urlKeyword = urlParams.get('pk_keyword')
  let keyword = `${document.location.href}#${content} @ ${document.referrer}`
  if (urlKeyword !== null) {
    if (urlKeyword.indexOf('#') === -1) {
      keyword = `${urlKeyword}#${content}`
    } else {
      keyword = urlKeyword
    }
  }
  referenceData = {
    reference,
    keyword
  }
  return referenceData
}

const formsWithReference = document.querySelectorAll('form[data-reference]')
formsWithReference.forEach((form) => {
  const referenceData: ReferenceData = getReferenceData()
  let key: keyof typeof referenceData
  for (key in referenceData) {
    const exists = form.querySelector<HTMLInputElement>(`input[name="${key}"]`)
    if (exists !== null && exists.value) {
      continue
    }
    const input = document.createElement('input')
    input.type = 'hidden'
    input.name = key
    input.value = referenceData[key] ?? ''
    form.appendChild(input)
  }
})

const linksWithReference = document.querySelectorAll('a[data-reference]')
;([...linksWithReference] as HTMLLinkElement[]).forEach((link) => {
  const referenceData: ReferenceData = getReferenceData()
  const href = link.getAttribute('href')
  if (!href) return
  const url = new URL(href, document.location.href)
  if (referenceData.reference) {
    url.searchParams.set('pk_campaign', referenceData.reference)
  }
  if (referenceData.keyword) {
    url.searchParams.set('pk_keyword', referenceData.keyword)
  }
  if (link.dataset.reference && url.searchParams.get('pk_content') === null) {
    url.searchParams.set('pk_content', link.dataset.reference)
  }
  link.setAttribute('href', url.toString())
})
