import { Tooltip, Collapse } from 'bootstrap'

interface PaymentConfirmData {
  resolve: (data: Record<string, any>) => void;
  reject: (error: Error) => void;
  data: Record<string, string>;
}

interface CustomEventMap {
  "paymentConfirm": CustomEvent<PaymentConfirmData>;
}
declare global {
  interface HTMLFormElement { //adds definition to Document, but you can do the same with HTMLElement
    addEventListener<K extends keyof CustomEventMap>(type: K,
      listener: (this: Document, ev: CustomEventMap[K]) => void): void;

  }
}

interface IApplePaySession {
  canMakePayments: () => boolean
}

declare global {
  interface Window {
    ApplePaySession: IApplePaySession | undefined
  }
}

type FeeMap = Record<string, (amount: number) => number>
type AddressFields = Record<string, HTMLFormElement | null>

const fees: FeeMap = {
  creditcard: (a: number) => Math.round((a * 0.014 + 0.25) * 100) / 100,
  paypal: (a: number) => Math.round((a * 0.015 + 0.35) * 100) / 100,
  sepa: () => 0.35,
}

class DonationForm {
  form: HTMLFormElement
  quickpayment: HTMLFormElement | null = null

  constructor(form: HTMLFormElement) {
    this.form = form
    this.setup()
  }

  private setup(): void {
    this.setupAdditionalCC()
    this.setupQuickpayment()

    const amountGroup = this.form.querySelector('.amount-group')
    if (amountGroup !== null) {
      this.setupAmountGroup(amountGroup)
      this.amountChanged(amountGroup.querySelector('input'))
    }
    this.form
      .querySelectorAll<HTMLInputElement>('[data-toggle="radiocollapse"]')
      .forEach((el) => this.setupRadioCollapse(el))

    const intervalInputs = this.form.querySelectorAll<HTMLFormElement>(
      'input[name="interval"]'
    )

    if (intervalInputs.length >= 0) {
      this.setupIntervalGroup(intervalInputs)
    }

    const hasShipping: boolean = this.form.querySelector('#id_chosen_gift') !== null
    if (hasShipping) {
      this.setupShipping()
    }

    ;['creditcard', 'paypal', 'sepa'].forEach((p) => {
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
        container.classList.add('ms-2')
        container.innerHTML = `Deine Spende wird ggf. erst ${nextYear} eingezogen.
        <a href="#" class="text-dark"
          data-bs-toggle="tooltip"
          data-bs-placement="top"
          title="Wenn Du diesen Zahlungsweg wählst, kann es sein, dass Deine Spende durch Banklaufzeiten
          erst ${nextYear} abgebucht wird. Damit wird sie ggf. auf Deiner Spendenbescheinigung
          ${d.getFullYear()} nicht erscheinen.">
          <span class="fa fa-info-circle"></span>
        </a>
        `
        const li = ls.parentElement
        li.appendChild(container)

        const infoLink = li.querySelector('a')
        if (infoLink != null) {
          new Tooltip(infoLink)
        }
      }
    }
  }

  private setupShipping(): void {
    const fillShippingFields = this.form.querySelector(
      '[data-fillfields="shipping"]'
    )
    const shippingFields = this.form.querySelectorAll<HTMLFormElement>(
      "input[name*='shipping'], select[name*='shipping']"
    )

    const addressFields: AddressFields = {}
    shippingFields.forEach((e) => {
      const key = e.name.replace('shipping_', '')
      addressFields[key] = this.form.querySelector(`[name="${key}"]`)
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

    const receiptRadios = this.form.querySelectorAll('input[name="receipt"]')

    const setFillShippingButton = () => {
      const state =
        this.form
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

  private setupAdditionalCC(): void {
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

  private amountChanged(amountInput: HTMLInputElement | null): void {
    if (amountInput == null) return
    let amount = parseFloat(amountInput.value.replace(',', '.'))
    if (isNaN(amount)) {
      amount = 0
    }
    for (const key of Object.keys(fees)) {
      const el = document.querySelector(`input[value="${key}"]`)
      if (el?.parentElement != null) {
        const label = el.parentElement
        let feeHint = label.querySelector('.fee-hint')
        if (feeHint === null) {
          feeHint = document.createElement('small')
          feeHint.classList.add('fee-hint')
          feeHint.classList.add('text-body-secondary')
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
    this.updateQuickpayment()
  }

  private setupIntervalGroup(intervalInputs: NodeListOf<HTMLFormElement>): void {
    const oneTimeFields = document.querySelectorAll<HTMLInputElement>(
      '[data-toggle="nonrecurring"]'
    )
    const additionalCCLabel = document.querySelector('.additional-cc')

    const triggerIntervalChange = (input: HTMLFormElement): void => {
      const isOneTime = input.value === '0'
      if (additionalCCLabel != null) {
        additionalCCLabel.classList.toggle('d-none', !isOneTime)
      }
      oneTimeFields.forEach((el) => {
        if (!isOneTime) {
          el.value = el.querySelectorAll('option')[0].value
          el.disabled = true
        } else {
          el.disabled = false
        }
      })

      this.updateQuickpayment()
    }

    intervalInputs.forEach((input) => {
      input.addEventListener('change', () => {
        triggerIntervalChange(input)
      })
    })

    const preChosenIntervalInput = [...intervalInputs].filter((i) => i.checked)
    if (preChosenIntervalInput.length > 0) {
      triggerIntervalChange(preChosenIntervalInput[0])
    }

    const oneTime = document.querySelector<HTMLInputElement>('#id_interval_0')
    if (oneTime == null || !oneTime.checked) {
      oneTimeFields.forEach((el) => el.classList.toggle('collapse', false))
    }
  }

  private setupRadioCollapse(radioCollapse: HTMLInputElement): void {
    const targetId = radioCollapse.dataset.target
    if (targetId == null) return
    const target = document.getElementById(targetId)
    if (target === null) return

    radioCollapse.addEventListener('change', () => {
      this.toggleRadioCollapse(radioCollapse, target)
    })
    if (radioCollapse.checked && radioCollapse.value === '1') {
      this.toggleRadioCollapse(radioCollapse, target)
    }
  }

  private toggleRadioCollapse(
    input: HTMLInputElement,
    target: HTMLElement
  ): void {
    const collapse = Collapse.getOrCreateInstance(target)
    const show = input.value === '1'
    if (show) collapse.show()
    else collapse.hide()

    target
      .querySelectorAll<HTMLInputElement | HTMLSelectElement>('input,select')
      .forEach((el) => {
        el.required = show

        const label = el.previousElementSibling
        if (label?.tagName !== 'LABEL') return

        if (show) label?.classList.add('field-required')
        else label?.classList.remove('field-required')
      })
  }

  private setupAmountGroup(amountGroup: Element): void {
    const input = amountGroup.querySelector('input')
    const buttons = amountGroup.querySelectorAll('button')
    const otherAmount = amountGroup.querySelector('.btn-other-amount')

    if (input != null) {
      amountGroup.querySelectorAll('[data-focus]').forEach((focusClick) => {
        focusClick.addEventListener('click', () => {
          input.focus()
        })
      })

      const updateButtons = () => {
        let hasAny = false

        otherAmount?.classList.remove('active')
        buttons.forEach((button) => {
          if (button.dataset.value === input.value) {
            hasAny = true
            button.classList.add('active')
          } else {
            button.classList.remove('active')
          }
        })

        if (!hasAny && input.value !== '') otherAmount?.classList.add('active')
      }

      buttons.forEach((button) => {
        button.addEventListener('click', () => {
          const value = button.dataset.value ?? ''
          input.value = value
          this.amountChanged(input)

          updateButtons()
        })
      })

      input.addEventListener('change', updateButtons)
      input.addEventListener('input', () => this.amountChanged(input))
    }
  }

  private setupQuickpayment(): void {
    this.quickpayment = this.form.querySelector("[data-quickpayment]")
    this.quickpayment?.addEventListener('quickpaymentAvailable', () => {
      this.updateQuickpayment()
      this.form.removeAttribute('hidden')
    })
    this.quickpayment?.addEventListener('paymentConfirm', async (event: CustomEvent<PaymentConfirmData>) => {
      //take form data, update with quickpayment data and send via fetch
      const quickPaymentdata: Record<string, string> = event.detail.data
      const formData = new FormData(this.form)

      const name = quickPaymentdata.name || ''
      const nameParts = name.split(' ')

      const data = {
        first_name: nameParts[0] || '',
        last_name: nameParts.slice(1).join(' ') || nameParts[0],
        email: quickPaymentdata.email,
        city: quickPaymentdata.city || '',
        postcode: quickPaymentdata.postcode || '',
        country: quickPaymentdata.country || '',
        address: (quickPaymentdata.street_address_1 || '') + (quickPaymentdata.street_address_2 ? `, ${quickPaymentdata.street_address_2}` : ''),
      }

      for (const [key, value] of Object.entries(data)) {
        formData.set(key, value)
      }

      const csrfTokenInput = this.form.querySelector('input[name="csrfmiddlewaretoken"]') as HTMLInputElement
      if (!csrfTokenInput) {
        event.detail.reject(new Error('CSRF token not found'))
        return
      }
      const fetchOptions: RequestInit = {
        method: 'POST',
        body: formData,
        headers: {
          'X-Requested-With': 'XMLHttpRequest',
          'Accept': 'application/json',
          'X-CSRFToken': csrfTokenInput.value
        }
      }
      const response = await fetch(this.form.action, fetchOptions)
      if (!response.ok) {
        event.detail.reject(new Error('Network response was not ok'))
      }
      const responseData = await response.json()
      event.detail.resolve(responseData)
    })
  }

  private updateQuickpayment(): void {
    if (this.quickpayment === null) {
      return
    }
    const formData = new FormData(this.form)
    let amount, interval;
    if (formData.get('amount')) {
      // amount in eurocents
      amount = Math.floor(parseFloat((formData.get('amount') as string).replace(',', '.')) * 100)
      if (isNaN(amount)) {
        amount = undefined
      }
    }
    if (formData.get('interval')) {
      interval = parseInt(formData.get('interval') as string, 10)
    }
    if (amount !== undefined && interval !== undefined) {
      const event = new CustomEvent("donationchange", {
        detail: {
          amount,
          interval
        }
      });
      this.quickpayment.dispatchEvent(event);
    }
  }
}

// Bootstrap logic
const donationForm = document.querySelector('.donation-form')
if (donationForm !== null) {
  new DonationForm(donationForm as HTMLFormElement)

  // Hide tagged donation links in header when there's a donation form on the page
  const donationLinks = document.querySelectorAll<HTMLElement>("[data-donationlink]")
  donationLinks.forEach((link) => {
    link.style.display = "none"
    link.classList.add('d-none')
    link.classList.add('d-sm-none')
    link.classList.add('d-md-none')
    link.classList.add('d-lg-none')
    link.classList.add('d-xl-none')
  })
}
