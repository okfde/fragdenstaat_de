import { toggleSlide } from "froide/frontend/javascript/lib/misc";

interface IApplePaySession {
  canMakePayments(): boolean;
}

declare global {
  // tslint:disable-next-line
  interface Window {
    ApplePaySession: IApplePaySession | undefined;
  }
}

function setupDonationForm(form: HTMLFormElement) {
  const amountGroup = form.querySelector(".amount-group");
  if (amountGroup !== null) {
    setupAmountGroup(amountGroup);
  }
  const radioCollapse = form.querySelectorAll('[data-toggle="radiocollapse"]');
  (Array.from(radioCollapse) as HTMLInputElement[]).forEach(setupRadioCollapse);
  const intervalGroup = document.getElementById("id_interval");
  if (intervalGroup !== null) {
    setupIntervalGroup(intervalGroup);
  }
  const additionalCCProviders = [];
  if (window.ApplePaySession && window.ApplePaySession.canMakePayments) {
    additionalCCProviders.push("Apple Pay");
  }
  if (additionalCCProviders.length > 0) {
    const ccInput = document.querySelector('input[value="creditcard"]');
    if (ccInput && ccInput.parentElement) {
      const parent = ccInput.parentElement;
      parent.childNodes[1].textContent += " / " + additionalCCProviders.join(" / ");
    }
  }
}

function setupIntervalGroup(intervalGroup: HTMLElement) {
  const oneTimePaymentMethods = (Array.from(
    document.querySelectorAll('#id_payment_method input[value="sofort"]'),
  ) as HTMLInputElement[]);
  const oneTimeFields = (Array.from(
    document.querySelectorAll('[data-toggle="nonrecurring"]'),
  ) as HTMLInputElement[]);
  const inputs = (Array.from(intervalGroup.querySelectorAll("input")) as HTMLInputElement[]);
  inputs.forEach((input) => {
    input.addEventListener("change", () => {
      const isOneTime = input.value === "0";
      toggleRadioInput(oneTimePaymentMethods, isOneTime);
      oneTimeFields.forEach((el) => {
        if (!isOneTime) {
          el.value = el.querySelectorAll("option")[0].value;
          el.disabled = true;
        } else {
          el.disabled = false;
        }
      });
    });
  });
  const oneTime = document.getElementById("id_interval_0") as HTMLInputElement;
  if (!oneTime || !oneTime.checked) {
    toggleRadioInput(oneTimePaymentMethods, false);
    oneTimeFields.forEach((el) => el.classList.toggle("collapse", false));
  }
}

function toggleRadioInput(inputs: HTMLInputElement[], checked: boolean) {
  inputs.forEach((input) => {
    if (!checked && input.checked) {
      input.checked = checked;
    }
    input.disabled = !checked;
    // Hide parent label element
    if (input.parentElement) {
      input.parentElement.classList.toggle("collapse", !checked);
    }
  });
}

function setupRadioCollapse(radioCollapse: HTMLInputElement) {
  const targetId = radioCollapse.dataset.target;
  if (!targetId) {
    return;
  }
  const target = document.getElementById(targetId);
  if (target === null) {
    return;
  }
  radioCollapse.addEventListener("change", () => {
    toggleRadioCollapse(radioCollapse, target);
  });
}

function toggleRadioCollapse(input: HTMLInputElement, target: HTMLElement) {
  if (input.value === "1") {
    target.classList.add("show");
    toggleSlide(target, 0.5);
    (Array.from(target.querySelectorAll("input,select")) as HTMLInputElement[]).forEach((el) => {
      el.required = true;
    });
  } else {
    target.classList.remove("show");
    toggleSlide(target, 0.5);
    (Array.from(target.querySelectorAll("input,select")) as HTMLInputElement[]).forEach((el) => {
      el.required = false;
    });
  }
}

function setupAmountGroup(amountGroup: Element) {
  const input = amountGroup.querySelector("input");
  const buttons = Array.from(amountGroup.querySelectorAll("button")) as HTMLButtonElement[];

  if (input) {
    const focusClicks = (Array.from(amountGroup.querySelectorAll("[data-focus]")) as HTMLElement[]);
    focusClicks.forEach((focusClick) => {
      focusClick.addEventListener("click", () => {
        input.focus();
      });
    });
  }

  function highlightButtonWithValue(value: string) {
    let hasAny = false;
    buttons.forEach((button) => {
      if (button.dataset.value === value) {
        hasAny = true;
        button.classList.add("btn-primary");
        button.classList.remove("btn-outline-primary");
      } else {
        button.classList.remove("btn-primary");
        button.classList.add("btn-outline-primary");
      }
    });
    return hasAny;
  }

  function buttonClick(button: HTMLButtonElement) {
    const value = button.dataset.value || "";
    if (input !== null) {
      input.value = value;
    }
    highlightButtonWithValue(value);
  }
  function inputChanged(amountInput: HTMLInputElement) {
    const anyButton = highlightButtonWithValue(amountInput.value);
    if (!anyButton) {
      amountInput.classList.add("border", "border-primary");
    } else {
      amountInput.classList.remove("border", "border-primary");
    }
  }

  buttons.forEach((button) => {
    button.addEventListener("click", () => buttonClick(button));
  });
  if (input) {
    input.addEventListener("focus", () => inputChanged(input));
    input.addEventListener("keyup", () => inputChanged(input));
    input.addEventListener("change", () => inputChanged(input));
  }
}

const donationForm = document.querySelector(".donation-form");
if (donationForm !== null) {
  setupDonationForm(donationForm as HTMLFormElement);
}
