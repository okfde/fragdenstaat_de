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
      audio.currentTime = parseInt(progress.value)
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

  const track = audio.querySelector<HTMLTrackElement>('track')
  const chapters = root.querySelector<HTMLDivElement>('.audio-player__chapters')
  const chapterLinks: HTMLAnchorElement[] = []

  const createChapters = (): void => {
    if (
      audio.textTracks.length > 0 &&
      audio.textTracks[0].kind === 'chapters'
    ) {
      const track = audio.textTracks[0]

      for (const cue of track.cues ?? []) {
        const span = document.createElement('span')
        span.textContent = `${toTimeString(cue.startTime)} – `
        span.classList.add('text-body-secondary')

        const a = document.createElement('a')
        a.href = '#audio-' + cue.id
        a.innerText = (cue as VTTCue).text

        a.addEventListener('click', (event) => {
          event.preventDefault()
          audio.currentTime = cue.startTime
        })
        a.dataset.cue = cue.id

        const li = document.createElement('li')
        li.appendChild(span)
        li.appendChild(a)

        chapters?.appendChild(li)
        chapterLinks.push(a)
      }

      chapters?.classList.remove('d-none')
    }
  }

  track?.addEventListener('load', createChapters)
  track?.addEventListener('cuechange', () => {
    chapterLinks.forEach((el) => el.classList.remove('fw-bold'))

    chapterLinks
      .find((el) => el.dataset.cue === audio.textTracks[0]?.activeCues?.[0]?.id)
      ?.classList.add('fw-bold')
  })
})
