import { toggleSlide } from "froide/frontend/javascript/lib/misc";

interface IDonationBannerStore { timestamp: number; }

function showDonationBanner() {
  window._paq = window._paq || [];

  function hideBanner(code: string, time: number) {
    return (e: Event) => {
      e.preventDefault();
      window._paq.push(["trackEvent", "donations", "donationBanner", code]);
      window.localStorage.setItem(itemName, JSON.stringify({
        timestamp: time,
      }));
      if (requiresAnimation) {
        toggleSlide(el);
        window.setTimeout(() => {
          removeBanner();
        }, 5 * 1000);
      } else {
        removeBanner();
      }
    };
  }
  function removeBanner() {
    if (el.parentNode) {
      el.parentNode.removeChild(el);
    }
  }

  const els = document.querySelectorAll(".dropdown-wrapper");
  if (els.length !== 1) {
    return;
  }
  const el = els[0] as HTMLElement;

  if (document.location && document.location.pathname) {
    const path = document.location.pathname;
    if (path.indexOf("/spenden/") !== -1 ||
        path.indexOf("/gesendet/") !== -1 ||
        path.indexOf("/payment/") !== -1 ||
        path.indexOf("/abgeschlossen/") !== -1 ||
        path.indexOf("/anfrage-stellen/") !== -1 ||
        path.indexOf("/account/") !== -1) {
      return removeBanner();
    }
  }
  const donationForm = document.querySelector(".donation-form");
  if (donationForm !== null) {
    return removeBanner();
  }

  const noBanner = document.querySelector("[data-nobanner]");
  if (noBanner !== null) {
    return removeBanner();
  }

  if (!window.localStorage) {
    return removeBanner();
  }

  const cancel = el.querySelector(".cancel-donation");
  const already = el.querySelector(".already-donation");
  const close = el.querySelector(".close");

  const itemName = "donation-banner";
  const now = (new Date()).getTime();
  const data = window.localStorage.getItem(itemName);
  if (data !== null) {
    const last = JSON.parse(data) as IDonationBannerStore;
    if (last.timestamp && (now - last.timestamp) < (60 * 60 * 24 * 1000)) {
      return removeBanner();
    }
  }
  window.localStorage.removeItem(itemName);

  if (close) {
    close.addEventListener("click", hideBanner("close", now));
  }

  if (cancel) {
    cancel.addEventListener("click", hideBanner("notnow", now));
  }
  if (already) {
    already.addEventListener("click", hideBanner("donated", now + (1000 * 60 * 60 * 24 * 30)));
  }

  if (el.style.display === 'block') {
    return
  }

  const banner = el.querySelector('.donation-block') as HTMLElement;
  let requiresAnimation = false;
  if (banner) {
    requiresAnimation = banner.dataset.topbanner === "true";
  }

  if (requiresAnimation) {
    window.setTimeout(() => {
      window._paq.push(["trackEvent", "donations", "donationBanner", "shown"]);
      if (window.innerWidth > 768) {
        el.style.position = "sticky";
        el.style.top = "0";
      }
      toggleSlide(el);
    }, 3000);
  } else {
    el.style.display = "block";
    window._paq.push(["trackEvent", "donations", "donationBanner", "shown"]);
  }
}

if (document.readyState === "loading") {
  window.document.addEventListener("DOMContentLoaded", showDonationBanner);
} else {
  showDonationBanner();
}
