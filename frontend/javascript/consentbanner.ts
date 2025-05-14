import { Modal } from 'bootstrap'
import {showCookieBar} from 'django-cookie-consent';


const cookieConsentModalTemplateId = "cookie-consent__cookie-bar"

const startConsentCheck = (statusUrl: string) => {
    let modal: Modal | null = null
    showCookieBar({
        statusUrl,
        templateSelector: `#${cookieConsentModalTemplateId}`,
        cookieGroupsSelector: '#cookie-consent__cookie-groups',
        acceptSelector: "#cookie-consent__accept",
        declineSelector: "#cookie-consent__decline",
        onShow: () => {
            modal = new Modal("#cookie-consent__modal")
            modal.show()
        },
        onAccept: () => {
            modal?.hide()
            let pixelUrls: string[] = []
            pixelUrls = JSON.parse(document.getElementById('cookie-consent__pixelurls')?.textContent || '[]');
            pixelUrls.forEach((url: string) => {
                const img = document.createElement('img')
                img.src = url
                img.height = 1
                img.width = 1
                img.style.display = 'none'
                document.body.appendChild(img)
            })
        },
        onDecline: () => {
            modal?.hide()
        },
    });
}



const cookieBarTemplate = document.getElementById(cookieConsentModalTemplateId)
if (cookieBarTemplate !== null) {
    startConsentCheck(cookieBarTemplate.dataset.cookiestatus!)
}
