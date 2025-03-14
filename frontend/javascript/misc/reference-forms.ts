let referenceData: undefined | ReferenceData

type ReferenceData = {
  reference?: string
  keyword?: string
}

function getReferenceData(): ReferenceData {
  if (referenceData !== undefined) return referenceData
  if (URLSearchParams === undefined) return {}

  const urlParams = new URLSearchParams(window.location.search)
  const reference = urlParams.get('pk_campaign') ?? document.location.pathname.split("/")[1] ?? 'homepage'
  const keyword =
    urlParams.get('pk_keyword') ??
    `${document.location.href} @ ${document.referrer}`
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
    const input = document.createElement('input')
    input.type = 'hidden'
    input.name = key
    input.value = referenceData[key] ?? ''
    form.appendChild(input)
  }
})
