import { toggleSlide } from 'froide/frontend/javascript/lib/misc'


function setupDonationForm (form: HTMLFormElement) {
  const amountGroup = form.querySelector('.amount-group')
  if (amountGroup !== null) {
    setupAmountGroup(amountGroup)
  }
  const radioCollapse = form.querySelectorAll('[data-toggle="radiocollapse"]');
  (<HTMLInputElement[]>Array.from(radioCollapse)).forEach(setupRadioCollapse);
  const intervalGroup = document.getElementById('id_interval')
  if (intervalGroup !== null) {
    setupIntervalGroup(intervalGroup)
  }
}

function setupIntervalGroup(intervalGroup: HTMLElement) {
  const oneTimePaymentMethods = (<HTMLInputElement[]>Array.from(
    document.querySelectorAll('#id_payment_method input[value="sofort"]')
  ));
  const oneTimeFields = (<HTMLInputElement[]>Array.from(
    document.querySelectorAll('[data-toggle="nonrecurring"]')
  ));
  const inputs = (<HTMLInputElement[]>Array.from(intervalGroup.querySelectorAll('input')));
  inputs.forEach((input) => {
    input.addEventListener('change', () => {
      const oneTime = input.value === '0'
      toggleRadioInput(oneTimePaymentMethods, oneTime)
      oneTimeFields.forEach((el) => {
        if (!oneTime) {
          el.value = ''
          el.disabled = true
        } else {
          el.disabled = false
        }
      })
    })
  })
  const oneTime = <HTMLInputElement>document.getElementById('id_interval_0')
  if (!oneTime || !oneTime.checked) {
    toggleRadioInput(oneTimePaymentMethods, false)
    oneTimeFields.forEach((el) => el.classList.toggle('collapse', false))
  }
}

function toggleRadioInput(inputs: HTMLInputElement[], checked: boolean) {
  inputs.forEach((input) => {
    if (!checked && input.checked) {
      input.checked = checked
    }
    input.disabled = !checked
    // Hide parent label element
    if (input.parentElement) {
      input.parentElement.classList.toggle('collapse', !checked)
    }
  })
}

function setupRadioCollapse (radioCollapse: HTMLInputElement) {
  const targetId = radioCollapse.dataset.target
  if (!targetId) {
    return
  }
  const target = document.getElementById(targetId)
  if (target === null) {
    return
  }
  radioCollapse.addEventListener('change', () => {
    toggleRadioCollapse(radioCollapse, target)
  })
}

function toggleRadioCollapse (input: HTMLInputElement, target: HTMLElement) {
  if (input.value === '1') {
    target.classList.add('show')
    toggleSlide(target, 0.5);
    (<HTMLInputElement[]>Array.from(target.querySelectorAll('input,select'))).forEach((el) => {
      el.required = true
    })
  } else {
    target.classList.remove('show')
    toggleSlide(target, 0.5);
    (<HTMLInputElement[]>Array.from(target.querySelectorAll('input,select'))).forEach((el) => {
      el.required = false
    })
  }
}

function setupAmountGroup (amountGroup: Element) {
  const input = amountGroup.querySelector('input')
  const buttons = <HTMLButtonElement[]>Array.from(amountGroup.querySelectorAll('button'))

  if (input) {
    const focusClicks = (<HTMLElement[]>Array.from(amountGroup.querySelectorAll('[data-focus]')));
    focusClicks.forEach((focusClick) => {
      focusClick.addEventListener('click', () => {
        input.focus()
      })
    })
  }

  function highlightButtonWithValue (value: string) {
    let any = false
    buttons.forEach((button) => {
      if (button.dataset.value === value) {
        any = true
        button.classList.add('btn-primary')
        button.classList.remove('btn-outline-primary')
      } else {
        button.classList.remove('btn-primary')
        button.classList.add('btn-outline-primary')
      }
    })
    return any
  }

  function buttonClick (button: HTMLButtonElement) {
    const value = button.dataset.value || ''
    if (input !== null) {
      input.value = value
    }
    highlightButtonWithValue(value)
  }
  function inputChanged (input: HTMLInputElement) {
    const anyButton = highlightButtonWithValue(input.value)
    if (!anyButton) {
      input.classList.add('border', 'border-primary')
    } else {
      input.classList.remove('border', 'border-primary')
    }
  }

  buttons.forEach((button) => {
    button.addEventListener('click', () => buttonClick(button))
  })
  if (input) {
    input.addEventListener('focus', () => inputChanged(input))
    input.addEventListener('keyup', () => inputChanged(input))
    input.addEventListener('change', () => inputChanged(input))
  }
}


const donationForm = document.querySelector('.donation-form')
if (donationForm !== null) {
  setupDonationForm(<HTMLFormElement>donationForm)
}
