let referenceData: undefined | any

function getReferenceData () {
  if (referenceData) {
    return referenceData
  }
  if (!URLSearchParams) {
    return {}
  }
  let urlParams = new URLSearchParams(window.location.search);
  let reference = urlParams.get('pk_campaign') || ''
  let keyword = urlParams.get('pk_keyword') || `${document.location.href} @ ${document.referrer}`
  referenceData = {
    reference, keyword
  }
  return referenceData
}
const formsWithReference = document.querySelectorAll('form[data-reference]')
Array.from(formsWithReference).forEach(form => {
  let referenceData = getReferenceData()
  for (let key in referenceData) {
    const input = document.createElement('input')
    input.type = 'hidden'
    input.name = key
    input.value = referenceData[key]
    form.appendChild(input)
  }
})