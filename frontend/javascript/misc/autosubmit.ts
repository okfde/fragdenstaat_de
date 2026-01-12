const autoSubmitForm = document.querySelector(
  'form[data-autosubmit]'
) as HTMLFormElement | null
if (autoSubmitForm && autoSubmitForm.checkValidity()) {
  // Use click on type submit instead of calling .submit()
  // so 'submit' event handler runs
  autoSubmitForm.querySelector<HTMLElement>("[type='submit']")?.click()
}
