import Tooltip from 'bootstrap/js/dist/tooltip'
import { toggleSlide } from 'froide/frontend/javascript/lib/misc'

interface IApplePaySession {
  canMakePayments: () => boolean
}

declare global {
  // tslint:disable-next-line
  interface Window {
    ApplePaySession: IApplePaySession | undefined
  }
}

interface IFeeMap {
  [name: string]: (amount: number) => number
}

interface IAddressFields {
  [name: string]: HTMLFormElement | null
}

const fees: IFeeMap = {
  creditcard: (a: number) => Math.round((a * 0.014 + 0.25) * 100) / 100,
  paypal: (a: number) => Math.round((a * 0.015 + 0.35) * 100) / 100,
  sepa: () => 0.35,
  sofort: (a: number) => Math.round((a * 0.014 + 0.25) * 100) / 100
}

function setupDonationForm(form: HTMLFormElement): void {
  setupAdditionalCC()
  const amountGroup = form.querySelector('.amount-group')
  if (amountGroup !== null) {
    setupAmountGroup(amountGroup)
    amountChanged(amountGroup.querySelector('input'))
  }
  const radioCollapse = form.querySelectorAll('[data-toggle="radiocollapse"]')
  ;(Array.from(radioCollapse) as HTMLInputElement[]).forEach(setupRadioCollapse)

  const intervalInputs: HTMLFormElement[] = Array.from(
    form.querySelectorAll('input[name="interval"]')
  )
  if (intervalInputs.length >= 0) {
    setupIntervalGroup(intervalInputs)
  }

  const hasShipping: boolean = form.querySelector('#id_chosen_gift') !== null
  if (hasShipping) {
    const fillShippingFields = form.querySelector(
      '[data-fillfields="shipping"]'
    )
    const shippingFields: HTMLFormElement[] = Array.from(
      form.querySelectorAll("input[name*='shipping'], select[name*='shipping']")
    )
    const addressFields: IAddressFields = {}
    shippingFields.forEach((e) => {
      const key = e.name.replace('shipping_', '')
      addressFields[key] = form.querySelector(`[name="${key}"]`)
    })

    const setShippingFields = (): void => {
      shippingFields.forEach((el) => {
        const key = el.name.replace('shipping_', '')
        el.value = addressFields[key]?.value ?? ''
      })
    }

    setShippingFields()

    if (fillShippingFields != null) {
      fillShippingFields.addEventListener('click', setShippingFields)
    }

    const receiptRadios: HTMLFormElement[] = Array.from(
      form.querySelectorAll('input[name="receipt"]')
    )
    const setFillShippingButton = (): void => {
      const state =
        form
          .querySelector('input[name="receipt"]:checked')
          ?.getAttribute('value') ?? '0'
      if (state === '1') {
        fillShippingFields?.removeAttribute('disabled')
      } else {
        fillShippingFields?.setAttribute('disabled', '')
      }
    }
    setFillShippingButton()
    receiptRadios.forEach((el) => {
      el.addEventListener('change', setFillShippingButton)
    })
  }

  ;['creditcard', 'paypal', 'sofort', 'sepa'].forEach((p) => {
    const el = document.querySelector(`input[value="${p}"]`)
    if (el?.parentElement != null) {
      el.parentElement.classList.add('onion-hide')
    }
  })
  // End of year lastschrift warning
  const d = new Date()
  const decemberDate = 22
  if (d.getMonth() + 1 === 12 && d.getDate() >= decemberDate) {
    const ls = document.querySelector('input[value="sepa"]')
    if (ls?.parentElement?.parentElement != null) {
      const nextYear = d.getFullYear() + 1
      const container = document.createElement('small')
      container.classList.add('bg-warning')
      container.classList.add('ml-2')
      container.innerHTML = `Ihre Spende wird ggf. erst ${nextYear} eingezogen.
      <a href="#" class="text-dark"
        data-bs-toggle="tooltip"
        data-bs-placement="top"
        title="Wenn Sie diesen Zahlungsweg wählen, kann es sein, dass Ihre Spende durch Banklaufzeiten
        erst ${nextYear} abgebucht wird. Damit wird sie ggf. auf Ihrer Spendenbescheinigung
        ${d.getFullYear()} nicht erscheinen.">
        <span class="fa fa-info-circle"></span>
      </a>
      `
      const li = ls.parentElement.parentElement
      li.appendChild(container)
      // console.log(li.querySelector("a"))
      const infoLink = li.querySelector('a')
      if (infoLink != null) {
        // eslint-disable-next-line no-new
        new Tooltip(infoLink)
      }
    }
  }
}

function setupAdditionalCC(): void {
  const additionalCCProviders = []
  if (window.ApplePaySession?.canMakePayments != null) {
    additionalCCProviders.push('Apple Pay')
  }

  if (additionalCCProviders.length > 0) {
    const ccInput = document.querySelector('input[value="creditcard"]')
    if (ccInput?.parentElement != null) {
      const label = ccInput.parentElement
      const ccProviders = document.createElement('span')
      ccProviders.className = 'additional-cc'
      ccProviders.textContent = ` / ${additionalCCProviders.join(' / ')}`
      label.appendChild(ccProviders)
    }
  }
}

function amountChanged(amountInput: HTMLInputElement | null): void {
  if (amountInput == null) return
  const amount = parseFloat(amountInput.value)
  for (const key of Object.keys(fees)) {
    const el = document.querySelector(`input[value="${key}"]`)
    if (el?.parentElement != null) {
      const label = el.parentElement
      let feeHint = label.querySelector('.fee-hint')
      if (feeHint === null) {
        feeHint = document.createElement('small')
        feeHint.classList.add('fee-hint')
        feeHint.classList.add('text-muted')
        label.appendChild(feeHint)
        feeHint = label.querySelector('.fee-hint')
      }
      if (feeHint !== null) {
        if (amount === 0 || isNaN(amount)) {
          feeHint.classList.add('d-none')
        } else {
          feeHint.classList.remove('d-none')
          const fee = fees[key](amount)
          const displayAmount = (amount - fee).toFixed(2).replace(/\./, ',')
          feeHint.textContent =
            document.documentElement.lang === 'de'
              ? ` (abzüglich Gebühren erhalten wir ${displayAmount} Euro)`
              : `(minus fees we receive ${displayAmount} Euro)`
        }
      }
    }
  }
}

function setupIntervalGroup(intervalInputs: HTMLFormElement[]): void {
  const oneTimePaymentMethods = document.querySelectorAll<HTMLInputElement>(
    '#id_payment_method input[value="sofort"]'
  )
  const oneTimeFields = document.querySelectorAll<HTMLInputElement>(
    '[data-toggle="nonrecurring"]'
  )
  const additionalCCLabel = document.querySelector('.additional-cc')

  function triggerIntervalChange(input: HTMLFormElement): void {
    const isOneTime = input.value === '0'
    if (additionalCCLabel != null) {
      additionalCCLabel.classList.toggle('d-none', !isOneTime)
    }
    toggleRadioInput(oneTimePaymentMethods, isOneTime)
    oneTimeFields.forEach((el) => {
      if (!isOneTime) {
        el.value = el.querySelectorAll('option')[0].value
        el.disabled = true
      } else {
        el.disabled = false
      }
    })
  }

  intervalInputs.forEach((input) => {
    input.addEventListener('change', () => {
      triggerIntervalChange(input)
    })
  })

  const preChosenIntervalInput = intervalInputs.filter((i) => i.checked)
  if (preChosenIntervalInput.length > 0) {
    triggerIntervalChange(preChosenIntervalInput[0])
  }

  const oneTime = document.querySelector<HTMLInputElement>('#id_interval_0')
  if (oneTime == null || !oneTime.checked) {
    toggleRadioInput(oneTimePaymentMethods, false)
    oneTimeFields.forEach((el) => el.classList.toggle('collapse', false))
  }
}

function toggleRadioInput(
  inputs: NodeListOf<HTMLInputElement>,
  checked: boolean
): void {
  inputs.forEach((input) => {
    if (!checked && input.checked) {
      input.checked = checked
    }
    input.disabled = !checked
    // Hide parent label element
    if (input.parentElement?.parentElement != null) {
      input.parentElement.parentElement.classList.toggle('collapse', !checked)
    }
  })
}

function setupRadioCollapse(radioCollapse: HTMLInputElement): void {
  const targetId = radioCollapse.dataset.target
  if (targetId == null) return
  const target = document.getElementById(targetId)
  if (target === null) return

  radioCollapse.addEventListener('change', () => {
    toggleRadioCollapse(radioCollapse, target)
  })
  if (radioCollapse.checked) {
    toggleRadioCollapse(radioCollapse, target)
  }
}

function toggleRadioCollapse(
  input: HTMLInputElement,
  target: HTMLElement
): void {
  if (input.value === '1') {
    if (!target.classList.contains('show')) {
      target.classList.add('show')
      toggleSlide(target, 0.5)
    }
    target
      .querySelectorAll<HTMLInputElement | HTMLSelectElement>('input,select')
      .forEach((el) => {
        el.required = true
      })
  } else {
    if (target.classList.contains('show')) {
      target.classList.remove('show')
      toggleSlide(target, 0.5)
    }
    target
      .querySelectorAll<HTMLInputElement | HTMLSelectElement>('input,select')
      .forEach((el) => {
        el.required = false
      })
  }
}

function setupAmountGroup(amountGroup: Element): void {
  const input = amountGroup.querySelector('input')
  const buttons = Array.from(amountGroup.querySelectorAll('button'))

  if (input != null) {
    const focusClicks = Array.from(amountGroup.querySelectorAll('[data-focus]'))
    focusClicks.forEach((focusClick) => {
      focusClick.addEventListener('click', () => {
        input.focus()
      })
    })
  }

  function highlightButtonWithValue(value: string): boolean {
    let hasAny = false
    buttons.forEach((button) => {
      if (button.dataset.value === value) {
        hasAny = true
        button.classList.add('btn-primary')
        button.classList.remove('btn-outline-primary')
      } else {
        button.classList.remove('btn-primary')
        button.classList.add('btn-outline-primary')
      }
    })
    return hasAny
  }

  function buttonClick(button: HTMLButtonElement): void {
    const value = button.dataset.value ?? ''
    if (input !== null) {
      input.value = value
      inputChanged(input)
    }
    highlightButtonWithValue(value)
  }
  function inputChanged(amountInput: HTMLInputElement): void {
    const anyButton = highlightButtonWithValue(amountInput.value)
    if (!anyButton) {
      amountInput.classList.add('border', 'border-primary')
    } else {
      amountInput.classList.remove('border', 'border-primary')
    }
    amountChanged(amountInput)
  }

  buttons.forEach((button) => {
    button.addEventListener('click', () => buttonClick(button))
  })
  if (input != null) {
    input.addEventListener('focus', () => inputChanged(input))
    input.addEventListener('keyup', () => inputChanged(input))
    input.addEventListener('change', () => inputChanged(input))
  }
}

const donationForm = document.querySelector('.donation-form')
if (donationForm !== null) {
  setupDonationForm(donationForm as HTMLFormElement)
}
