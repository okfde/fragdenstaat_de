const pauseModalVideo = function (this: HTMLVideoElement): void {
  const video = this.querySelector('video')
  if (video != null) {
    video.pause()
  }
}

const videoModals = document.querySelectorAll('[data-modal="video"]')
Array.from(videoModals).forEach((videoModal) => {
  videoModal.addEventListener('hidden.bs.modal', pauseModalVideo)
})
