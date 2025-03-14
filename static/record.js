// center header
window.addEventListener("load", () => {
  let orgWrapper = document.getElementById("org")
  let usernameWrapper = document.getElementById("username")
  let org = orgWrapper.firstElementChild
  let username = usernameWrapper.firstElementChild

  function resize() {
    let orgSize = org.getBoundingClientRect()
    let usernameSize = username.getBoundingClientRect()
    usernameWrapper.style.minWidth = orgSize.width + "px"
    orgWrapper.style.minWidth = usernameSize.width + "px"
  }

  resize()
  const orgObserver = new ResizeObserver(resize)
  orgObserver.observe(org)
  const usernameObserver = new ResizeObserver(resize)
  usernameObserver.observe(username)
}, {passive: true})

window.addEventListener("load", () => {
  document.querySelector("#result-all").addEventListener("click", () => {
    Array.from(document.querySelectorAll(".annotation-on")).forEach(
      x => { x.checked = true })
  })
  document.querySelector("#result-none").addEventListener("click", () => {
    Array.from(document.querySelectorAll(".annotation-off")).forEach(
      x => { x.checked = true })
  })
}, {passive: true})

function findButtons(that) {
  that.playbackButton = document.getElementById("playback")
  that.nextButton = document.getElementById("next-audio")
}

function resetPlaybackButton(button, ...add) {
  const playbackButtonClasses = [
      "play", "playable", "pause", "load", "stop", "record", "done", "error",
      "ing"
    ];

  for (let i of playbackButtonClasses) {
    button.classList.remove(i)
  }

  for (let i of add) {
    button.classList.add(i)
  }
}

class Audio extends AudioPrefetch {
  constructor(project) {
    super("#playing", project)
  }

  start(project) {
    this.project = project
    return fetch(`/jnd/api/${this.project}/start`)
  }

  done() {
    window.location.href =
      `/jnd/${this.project}_done.html?project=${this.project}`
  }

  restart() {
    window.location.href = "/jnd"
  }

  load(data) {
    let { name } = data;
    document.getElementById("username").firstElementChild.innerText = name;
    this.waited()
  }

  loading() {
    resetPlaybackButton(this.playbackButton, "load");
  }

  loaded() {
    this.pause()
  }

  initialize() {
    findButtons(this)
    if (window.location.host === "localhost:8088") {
      this.audio.setAttribute("controls", "")
      this.loadq.add(() => {
        const f = recorder.onSuccess, g = this.loaded, h = () => {
          recorder.ready.call(recorder)
          recorder.done.call(recorder)
        }

        recorder.onSuccess = stream => {
          f.call(recorder, stream)
          h()
          this.loaded = () => {
            g.call(this)
            h()
          }
        }
      }, this)
    }
  }

  waiting() {
    resetPlaybackButton(this.playbackButton, "load");
  }

  waited() {
    if (this.#playing) this.play()
    else this.pause()
  }

  ready() {
    this.pause()
  }

  backlogged = 0;
  async result(key, f=undefined) {
    this.backlogged += 1;
    super.result(key, k => f(k).then(response => {
      if (response.ok) this.backlogged = 0;
      return response
    }));
  }


  retries(f) {
    this.loadq.add(() => {
      this.nextButton.onclick = f
    }, this)
  }

  retrying(still) {
    // this.backlogged:
    // 0 -> failed not on result fetch or recovering
    // 1 -> failed but has preloaded audio pending
    // 2 -> nothing queued to play; ask user to retry
    this.loadq.add(() => {
      if (this.backlogged >= 2) {
        resetPlaybackButton(this.playbackButton, still ? "load" : "error");
        this.nextButton.disabled = still
        this.nextButton.firstElementChild.innerText = (
          still ? "Next Audio" : "Retry")
      }
    })
  }

  recovered() {
    this.pause()
  }

  debug(url) {
    console.info("Now playing " + (new URL(url, document.baseURI).href))
  }

  #playing = false;
  play() {
    this.#playing = true;
    // resetPlaybackButton(this.playbackButton, "pause");
    resetPlaybackButton(this.playbackButton, "play", "ing");
    this.playbackButton.onclick = () => {
      this.audio.pause();
      this.pause();
    }
  }

  pause() {
    this.#playing = false;
    resetPlaybackButton(this.playbackButton, "play");
    this.playbackButton.onclick = () => {
      this.audio.play()
      this.play()
    }
  }
}

class AudioResults extends Audio {
  load(data) {
    super.load(data)
    const { name, has_results } = data;
    // second clause checks that it ends with a UUID4
    if (name.startsWith('test-') && name.at(-22) === "4") {
      this.enableOverlay(has_results);
    }
  }

  #overlayButton = "#overlay-results"
  #overlayEle = "#results-overlay"
  #overlayImg = "#results-overlay img"
  #resultsClickable = "#results-clickable"
  overlaid = false
  #overlayEnabled
  enableOverlay(immediately) {
    this.overlaid = true
    this.#overlayEnabled = immediately
    this.#overlayButton = document.querySelector(this.#overlayButton)
    this.#overlayEle = document.querySelector(this.#overlayEle)
    this.#overlayImg = document.querySelector(this.#overlayImg)
    this.#resultsClickable = document.querySelector(this.#resultsClickable)
    this.#overlayButton.classList.remove("hidden")
    this.#overlayButton.addEventListener(
      "click", this.overlayResults.bind(this))
    this.#overlayEle.addEventListener(
      "click", e => document.body.classList.remove("overlaying"));
    this.#resultsClickable.addEventListener(
      "click", e => e.stopPropagation());
  }

  done() {
    if (this.overlaid) {
      window.location.href = `/jnd/${this.project}_done.html?` +
        `debug=true&project=${this.project}`
    } else {
      super.done()
    }
  }

  initialize() {
    super.initialize()
    this.showNowPlaying()
  }

  #playbackDebug = "#playback-debug"
  showNowPlaying() {
    this.#playbackDebug = document.querySelector(this.#playbackDebug)
  }

  debug(url) {
    super.debug(url);
    if (this.overlaid) this.#playbackDebug.innerText = url
  }

  loaded() {
    super.loaded()
    if (this.overlaid) {
      this.#overlayButton.disabled = !this.#overlayEnabled;
      this.#overlayEnabled = true
    }
  }

  overlayResults(e) {
    if (!this.audio.paused) {
      this.audio.pause()
      this.pause()
    }
    document.body.classList.add("overlaying")
    this.#overlayImg.setAttribute("src", this.#overlayURL)
    this.#overlayImg.addEventListener("load", e => {
      const { naturalWidth, naturalHeight } = this.#overlayImg;
      this.#resultsClickable.style.aspectRatio = naturalWidth / naturalHeight;
    })
  }

  get #overlayURL() {
    // time parameter to prevent caching; should be done with response headers
    return `/jnd/api/${this.project}/plot?t=` + Date.now();
  }
}

class InteractiveRecorder extends DiscretelyTunedRecorder {
  #audio
  #mic
  #steps = "#playback-wrapper, #recording-wrapper";
  constructor(audio, timeslice, streaming) {
    super(".sound-bar", timeslice, streaming)
    new LoadQueue().add(() => {
      findButtons(this)
      this.#mic = document.getElementById("sound-wrapper")
      this.#steps = document.querySelectorAll(this.#steps);
    })
    this.#audio = audio
    const f = audio.initialize, g = audio.overlayResults
    audio.initialize = () => {
      f.call(audio)
      audio.audio.addEventListener("play", this.ready.bind(this))
      audio.audio.addEventListener("ended", this.ended.bind(this))
    }
    audio.overlayResults = () => {
      if (g !== undefined) {
        if (this.recording) this.done()
        g.call(audio)
      }
    }
  }

  highlight(step) {
    for (let i of this.#steps) {
      i.classList.remove("active")
    }
    this.#steps[step].classList.add("active")
  }

  start() {
    this.#mic.classList.add("active")
    return super.start()
  }

  stop() {
    this.#mic.classList.remove("active")
    return super.stop()
  }

  get recording() {
    return this.state === "recording"
  }

  async complete() {
    if (this.recording) {
      await this.stop().then(() => this.complete())
      return
    }
    this.nextButton.disabled = true;
    const data = await this.result(`/jnd/api/${this.#audio.project}/result`, {})
    await this.#audio.result(1, k => {
        return fetch(data[0], data[1]).then(response => {
          if (!response.ok) this.debug(response.statusText);
          return response
        }).catch(e => {
          this.debug(e.message)
          console.error(e)
          return Promise.reject(e)
        })
      }
    )
    this.highlight(0)
    this.#audio.pause()
  }

  autostart() { return true; }

  activate() {
    this.start()
    // this.playbackButton.onclick = () => this.done()
    this.playbackButton.onclick = () => {}
    this.nextButton.onclick = () => this.complete()
    this.nextButton.disabled = false;
  }

  ended() {
    resetPlaybackButton(this.playbackButton, "done");
  }

  done() {
    return this.stop().then(() => {
      resetPlaybackButton(this.playbackButton, "record");
      this.playbackButton.onclick = () => this.activate()
    })
  }

  ready() {
    this.highlight(1)
    if (this.autostart()) {
      this.activate()
    } else {
      resetPlaybackButton(this.playbackButton, "record");
      this.playbackButton.onclick = () => this.activate()
    }
  }

  exceptionsView = "#exceptions-view"
  debug(v) {
    new LoadQueue(this).add(() => {
      this.exceptionsView = document.querySelector(this.exceptionsView)
      this.debug = (v => {
        this.exceptionsView.innerText = v
      }).bind(this);
      this.debug(v)
    })
  }
}

class AutoEndingRecorder extends InteractiveRecorder {
  #silence = -8
  #timing = 1000 * 20
  #minimum = 1000 * 0.2
  #lastNoise
  #starting
  volume(v) {
    super.volume(v)
    if (!this.recording) return this.#lastNoise = undefined
    const now = Date.now()
    if (this.#lastNoise == undefined) {
      this.#starting = now
      this.#lastNoise = now
    } else if (v > this.#silence) {
      this.#lastNoise = now
    } else if (now - this.#lastNoise > this.#timing) {
      // this.done()
      this.stop()
      if (this.#lastNoise - this.#starting < this.#minimum) {
        this.nextButton.disabled = true
      }
    }
  }
}

class AnnotatedRecorder extends AutoEndingRecorder {
  async result(url, headers) {
    url = URL.parse(url, window.location.href)
    url.searchParams.set("annotations", JSON.stringify(this.aux_data()))
    return super.result(url, headers)
  }

  aux_data() {
    return Array.from(document.querySelectorAll(".annotation-on")).map(
      x => x.checked)
  }
}

// TODO: prefetch answers
class AnnotatedAudio extends AudioResults {
  #holding
  #holder = "#aux-data"
  options(answer) {
    if (typeof this.#holder === "string") {
      this.#holder = document.querySelector(this.#holder)
    }
    if (answer === undefined) { return }
    const existing = this.#holder.querySelector(".options-case")
    if (existing !== null) this.#holder.removeChild(existing)
    const container = this.#holder.appendChild(document.createElement("div"))
    container.classList.add("options-case")
    answer.split(",").forEach((x, i) => {
      const name = `option-${i}`
      const wrapper = container.appendChild(document.createElement("div"))
      for (const j of ['on', 'off']) {
        const check = wrapper.appendChild(document.createElement("input"))
        const label = wrapper.appendChild(document.createElement("label"))
        check.setAttribute("type", "radio")
        check.setAttribute("id", `${name}-${j}`)
        check.setAttribute("name", name)
        check.classList.add("annotation", `annotation-${j}`)
        check.setAttribute("required", "")
        label.setAttribute("for", `${name}-${j}`)
        label.classList.add("option", "base-button", `option-${j}`)
        label.innerText = x
      }
      return wrapper
    })
  }

  prefetch(next) {
    const { answer, ...others } = next
    if (answer !== undefined && answer !== 1) this.#holding.push(answer)
    return super.prefetch(others)
  }

  load(data) {
    let { answer } = data
    this.options(answer[0])
    this.#holding = [answer[1]]
    return super.load(data)
  }

  async result(key, f=undefined) {
    super.result(key, k => f(k).then(response => {
      if (this.backlogged < 2) this.options(this.#holding.pop())
      return response
    }).catch(e => {
      console.error(e)
    }));
  }

  #playbackProgress = "#playback-debug"
  debug(url) {
    if (url === undefined) return
    if (typeof this.#playbackProgress === "string")
      this.#playbackProgress = document.querySelector(this.#playbackProgress)
    const [ list, seq ] = url.match(/[0-9]+/g).map(x => parseInt(x))
    const lang = url.match(/([^-/]+)-[^/]+$/)[1]
    this.#playbackProgress.innerText =
      `${lang} list ${list} sentence ${seq}`;
    return super.debug(url)
  }

  initialize() {
    super.initialize()
    if (window.location.host === "localhost:8088") {
      const f = this.options.bind(this)
      this.options = (answer) => {
        const res = f(answer)
        document.querySelectorAll(".annotation").forEach(x => {
          x.removeAttribute("required")
        })
        return res
      }
    }
  }

  enableOverlay(immediately) {
  }

  done() {
    this.overlaid = true
    super.done()
  }
}

