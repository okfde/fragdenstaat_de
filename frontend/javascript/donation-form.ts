import { Tooltip } from "bootstrap.native/dist/bootstrap-native-v4"
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

interface IFeeMap {
  [name: string]: (amount: number) => number;
}

const fees: IFeeMap = {
  creditcard: (a: number) => Math.round(((a * 0.014) + 0.25) * 100) / 100,
  paypal: (a: number) => Math.round(((a * 0.0249) + 0.35) * 100) / 100,
  sepa: () => 0.35,
  sofort: (a: number) => Math.round(((a * 0.014) + 0.25) * 100) / 100,
};

function setupDonationForm(form: HTMLFormElement) {
  setupAdditionalCC()
  const amountGroup = form.querySelector(".amount-group");
  if (amountGroup !== null) {
    setupAmountGroup(amountGroup);
    amountChanged(amountGroup.querySelector("input"));
  }
  const radioCollapse = form.querySelectorAll('[data-toggle="radiocollapse"]');
  (Array.from(radioCollapse) as HTMLInputElement[]).forEach(setupRadioCollapse);

  const intervalGroup = document.getElementById("id_interval");
  if (intervalGroup !== null) {
    setupIntervalGroup(intervalGroup);
  }

  ["creditcard", "paypal", "sofort", "sepa"].forEach((p) => {
    const el = document.querySelector(`input[value="${p}"]`);
    if (el && el.parentElement && el.parentElement.parentElement) {
      el.parentElement.parentElement.classList.add("onion-hide");
    }
  });
  // End of year lastschrift warning
  const d = new Date();
  const decemberDate = 22;
  if (d.getMonth() + 1 === 12 && d.getDate() >= decemberDate) {
    const ls = document.querySelector('input[value="sepa"]');
    if (ls && ls.parentElement && ls.parentElement.parentElement) {
      const nextYear = d.getFullYear() + 1;
      const container = document.createElement("small");
      container.classList.add("bg-warning");
      container.classList.add("ml-2");
      container.innerHTML = `Ihre Spende wird ggf. erst ${nextYear} eingezogen.
      <a href="#" class="text-dark"
        data-container="body" data-toggle="tooltip"
        data-placement="top"
        title="Wenn Sie diesen Zahlungsweg wählen, kann es sein, dass Ihre Spende durch Banklaufzeiten
        erst ${nextYear} abgebucht wird. Damit wird sie ggf. auf Ihrer Spendenbescheinigung
        ${d.getFullYear()} nicht erscheinen.">
        <span class="fa fa-info-circle"></span>
      </a>
      `;
      const li = ls.parentElement.parentElement;
      li.appendChild(container);
      // console.log(li.querySelector("a"))
      const infoLink = li.querySelector("a");
      if (infoLink) {
        // tslint:disable-next-line: no-unused-expression
        new Tooltip(infoLink);
      }
    }
  }
}

function setupAdditionalCC() {
  const additionalCCProviders = [];
  if (window.ApplePaySession && window.ApplePaySession.canMakePayments) {
    additionalCCProviders.push("Apple Pay");
  }

  if (additionalCCProviders.length > 0) {
    const ccInput = document.querySelector('input[value="creditcard"]');
    if (ccInput && ccInput.parentElement) {
      const label = ccInput.parentElement;
      const ccProviders = document.createElement("span");
      ccProviders.className = "additional-cc"
      ccProviders.textContent = ` / ${additionalCCProviders.join(" / ")}`
      label.appendChild(ccProviders)
    }
  }
}

function amountChanged(amountInput: HTMLInputElement | null) {
  if (!amountInput) { return; }
  const amount = parseFloat(amountInput.value);
  for (const key in fees) {
    if (fees.hasOwnProperty(key)) {
      const el = document.querySelector(`input[value="${key}"]`);
      if (el && el.parentElement) {
        const label = el.parentElement;
        let feeHint = label.querySelector(".fee-hint");
        if (feeHint === null) {
          feeHint = document.createElement("small");
          feeHint.classList.add("fee-hint");
          feeHint.classList.add("text-muted");
          label.appendChild(feeHint);
          feeHint = label.querySelector(".fee-hint");
        }
        if (feeHint !== null) {
          if (!amount) {
            feeHint.classList.add("d-none")
          } else {
            feeHint.classList.remove("d-none")
            const fee = fees[key](amount);
            const displayAmount = (amount - fee).toFixed(2).replace(/\./, ",");
            feeHint.textContent = ` (abzüglich Gebühren erhalten wir ${displayAmount} Euro)`;
          }
        }
      }
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
  const additionalCCLabel = document.querySelector(".additional-cc")

  function triggerIntervalChange(input: HTMLInputElement) {
    const isOneTime = input.value === "0";
    if (additionalCCLabel) {
      additionalCCLabel.classList.toggle("d-none", !isOneTime)
    }
    toggleRadioInput(oneTimePaymentMethods, isOneTime);
    oneTimeFields.forEach((el) => {
      if (!isOneTime) {
        el.value = el.querySelectorAll("option")[0].value;
        el.disabled = true;
      } else {
        el.disabled = false;
      }
    });
  }

  const inputs = (Array.from(intervalGroup.querySelectorAll("input")) as HTMLInputElement[]);
  inputs.forEach((input) => {
    input.addEventListener("change", () => {
      triggerIntervalChange(input)
    });
  });

  const preChosenIntervalInput = intervalGroup.querySelector("input[checked]") as HTMLInputElement;
  if (preChosenIntervalInput) {
    triggerIntervalChange(preChosenIntervalInput)
  }

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
    if (input.parentElement && input.parentElement.parentElement) {
      input.parentElement.parentElement.classList.toggle("collapse", !checked);
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
  if (radioCollapse.checked) {
    toggleRadioCollapse(radioCollapse, target);
  }
}

function toggleRadioCollapse(input: HTMLInputElement, target: HTMLElement) {
  if (input.value === "1") {
    if (!target.classList.contains("show")) {
      target.classList.add("show");
      toggleSlide(target, 0.5);
    }
    (Array.from(target.querySelectorAll("input,select")) as HTMLInputElement[]).forEach((el) => {
      el.required = true;
    });
  } else {
    if (target.classList.contains("show")) {
      target.classList.remove("show");
      toggleSlide(target, 0.5);
    }
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
      inputChanged(input);
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
    amountChanged(amountInput);
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
