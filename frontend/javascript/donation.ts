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

  const els = document.querySelectorAll(".donation-block");
  if (els.length === 2) {
    /* Show second banner like normal */
    const demoEl = els[1] as HTMLElement;
    demoEl.style.display = "block";
    return;
  }
  if (els.length !== 1) {
    return;
  }
  const el = els[0] as HTMLElement;

  if (document.location && document.location.pathname) {
    if (document.location.pathname.indexOf("/spenden/") !== -1 ||
        document.location.pathname.indexOf("/blog/") !== -1 ||
        document.location.pathname.indexOf("/gesendet/") !== -1 ||
        document.location.pathname.indexOf("/anfrage-stellen/") !== -1 ||
        document.location.pathname.indexOf("/account/") !== -1) {
      return removeBanner();
    }
  }
  const donationIframe = document.querySelector('iframe[src^="https://www.betterplace.org/de/projects/"]');
  if (donationIframe !== null) {
    return removeBanner();
  }

  if (!window.localStorage) {
    return removeBanner();
  }
  const requiresAnimation = el.dataset.topbanner === "true";
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
