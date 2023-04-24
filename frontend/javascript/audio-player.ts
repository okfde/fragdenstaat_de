document.querySelectorAll<HTMLDivElement>('.audio-player').forEach((root) => {
  const audio = root.querySelector<HTMLAudioElement>('audio')
  if (audio === null) return

  const playBtn = root.querySelector<HTMLButtonElement>(
    '.audio-player__playpause'
  )
  playBtn?.addEventListener('click', () => {
    void (audio.paused ? audio.play() : audio.pause())
  })

  const updatePlaying = (playing: boolean): void => {
    const iconClasses = playBtn?.querySelector('i')?.classList
    if (playing) {
      iconClasses?.add('fa-pause')
      iconClasses?.remove('fa-play')
    } else {
      iconClasses?.remove('fa-pause')
      iconClasses?.add('fa-play')
    }
  }

  audio.addEventListener('play', () => updatePlaying(true))
  audio.addEventListener('pause', () => updatePlaying(false))
  audio.addEventListener('ended', () => updatePlaying(false))

  const toTimeString = (duration: number): string => {
    const minutes = Math.floor(duration / 60)
    const seconds = Math.floor(duration % 60)
    return `${minutes < 10 ? '0' : ''}${minutes}:${
      seconds < 10 ? '0' : ''
    }${seconds}`
  }

  const progress = root.querySelector<HTMLInputElement>(
    '.audio-player__progress'
  )
  const textProgress = root.querySelector<HTMLDivElement>(
    '.audio-player__textprogress'
  )
  if (progress !== null && textProgress !== null) {
    let hovering = false

    const updateProgress = (): void => {
      progress.max = Math.floor(audio.duration).toString()
      if (!hovering) progress.value = Math.floor(audio.currentTime).toString()

      textProgress.innerText = `${toTimeString(
        audio.currentTime
      )} / ${toTimeString(audio.duration)}`
    }
    audio.addEventListener('timeupdate', updateProgress)
    audio.addEventListener('loadedmetadata', updateProgress)

    progress.addEventListener('input', () => {
      audio.fastSeek(parseInt(progress.value))
      console.log(parseInt(progress.value), audio.currentTime)
    })
    progress.addEventListener('pointerdown', () => {
      hovering = true
    })
    progress.addEventListener('pointerup', () => {
      hovering = false
    })
  }

  const seek = (by: number): void => {
    audio.currentTime += by
  }
  root
    .querySelector('.audio-player__forward')
    ?.addEventListener('click', () => seek(15))
  root
    .querySelector('.audio-player__backward')
    ?.addEventListener('click', () => seek(-15))

  const speeds = [0.5, 1, 1.25, 1.5, 1.75, 2, 2.25, 2.5, 3]
  const playbackSpeed = root.querySelector<HTMLButtonElement>(
    '.audio-player__speed'
  )
  playbackSpeed?.addEventListener('click', () => {
    const i = speeds.findIndex((x) => x >= audio.playbackRate)
    const next = i + 1 >= speeds.length ? 0 : i + 1

    const speed = speeds[next] ?? 1

    audio.playbackRate = speed
    const text = playbackSpeed.querySelector<HTMLSpanElement>(
      '.audio-player__speed-display'
    )
    if (text !== null) text.innerText = `${speed}x`
  })
})
