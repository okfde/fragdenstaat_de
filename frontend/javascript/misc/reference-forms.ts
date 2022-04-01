let referenceData: undefined | any

function getReferenceData(): any {
  if (referenceData !== undefined) return referenceData
  if (URLSearchParams === undefined) return {}

  const urlParams = new URLSearchParams(window.location.search)
  const reference = urlParams.get('pk_campaign') ?? ''
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
  const referenceData = getReferenceData()
  for (const key in referenceData) {
    const input = document.createElement('input')
    input.type = 'hidden'
    input.name = key
    input.value = referenceData[key]
    form.appendChild(input)
  }
})
