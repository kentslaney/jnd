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

function findButtons(that) {
  that.playbackButton = document.getElementById("playback")
  that.nextButton = document.getElementById("next-audio")
}

function resetPlaybackButton(button, ...add) {
  const playbackButtonClasses = [
    "play", "playable", "pause", "load", "stop", "record", "done", "error"];

  for (let i of playbackButtonClasses) {
    button.classList.remove(i)
  }

  for (let i of add) {
    button.classList.add(i)
  }
}

class Audio extends AudioPrefetch {
  constructor() {
    super("#playing")
  }

  start() {
    return fetch("/jnd/api/quick/start")
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
    this.play()
  }

  initialize() {
    findButtons(this)
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

  #backlogged = 0;
  result(key, f=undefined) {
    this.#backlogged += 1;
    super.result(key, k => f(k).then(response => {
      if (response.ok) this.#backlogged = 0;
      return response
    }));
  }


  retries(f) {
    this.loadq.add(() => {
      this.nextButton.onclick = f
    })
  }

  retrying(still) {
    // this.#backlogged:
    // 0 -> failed not on result fetch or recovering
    // 1 -> failed but has preloaded audio pending
    // 2 -> nothing queued to play; ask user to retry
    this.loadq.add(() => {
      if (this.#backlogged >= 2) {
        resetPlaybackButton(this.playbackButton, still ? "load" : "error");
        this.nextButton.disabled = still
        this.nextButton.firstElementChild.innerText = (
          still ? "Next Audio" : "Retry")
      }
    })
  }

  recovered() {
    this.play()
  }

  #playing = true;
  play() {
    this.#playing = true;
    resetPlaybackButton(this.playbackButton, "pause");
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
      this.#enableOverlay(has_results)
    }
  }

  #overlayButton = "#overlay-results"
  #overlayEle = "#results-overlay"
  #overlayImg = "#results-overlay img"
  #resultsClickable = "#results-clickable"
  #overlayEnabled = 1
  #enableOverlay(immediately) {
    this.#overlayButton = document.querySelector(this.#overlayButton)
    this.#overlayEle = document.querySelector(this.#overlayEle)
    this.#overlayImg = document.querySelector(this.#overlayImg)
    this.#resultsClickable = document.querySelector(this.#resultsClickable)
    this.#overlayButton.classList.remove("hidden")
    this.#overlayButton.addEventListener(
      "click", this.#overlayResults.bind(this))
    this.#overlayEle.addEventListener(
      "click", e => document.body.classList.remove("overlaying"));
    this.#resultsClickable.addEventListener(
      "click", e => e.stopPropagation());
    this.#overlayEnabled ^= immediately
    // matches (enabled) immediately if first, inverts it if not
    this.#overlayButton.disabled = !(this.#overlayEnabled & 1);
  }

  loaded() {
    super.loaded()
    this.#overlayEnabled ^= 1
    // first call: matches (enabled) immediately if first, inverts it if not
    // subsequent calls: always false
    this.#overlayButton.disabled = !this.#overlayEnabled;
    this.#overlayEnabled |= 2
  }

  #overlayResults(e) {
    document.body.classList.add("overlaying")
    this.#overlayImg.setAttribute("src", this.#overlayURL)
    this.#overlayImg.addEventListener("load", e => {
      const { naturalWidth, naturalHeight } = this.#overlayImg;
      this.#resultsClickable.style.aspectRatio = naturalWidth / naturalHeight;
    })
  }

  get #overlayURL() {
    // time parameter to prevent caching; should be done with response headers
    return "/jnd/api/quick/plot?t=" + Date.now();
  }
}

class Recording {
  #chunks = [];

  #mediaRecorder
  constructor(mediaRecorder) {
    this.#mediaRecorder = mediaRecorder
  }

  recieve(e) {
    this.#chunks.push(e.data)
  }

  blob() {
    return new Blob(this.#chunks, { type: this.#mediaRecorder.mimeType });
  }
}

class Recorder {
  constructor() {
    if (!navigator.mediaDevices.getUserMedia) {
      console.error("media devices API unsupported")
    }

    const constraints = { audio: true };
    navigator.mediaDevices.getUserMedia(constraints)
      .then(stream => this.onSuccess(stream))
      .catch(e => {
        const err = new DOMException("user denied mic permissions", {cause: e});
        console.error(err)
        this.debug(err.message);
      });
  }

  #mediaRecorder
  onSuccess(stream) {
    this.#mediaRecorder = new MediaRecorder(stream);
    this.#mediaRecorder.onstop = () => this.#stopped.call(this)
    this.#mediaRecorder.ondataavailable = e => this.recieve(e)
  }

  #recording
  create() {
    this.#recording = new Recording(this.#mediaRecorder)
  }

  start() {
    this.#stopnt()
    try {
      this.#mediaRecorder.start();
    } catch(e) {
      this.debug(e.message);
      throw e
    }
  }

  #stopping
  #stopped() { if (this.#stopping !== undefined) this.#stopping(true); }
  #stopnt() { if (this.#stopping !== undefined) this.#stopping(false); }

  stop() {
    this.#stopnt()
    this.#mediaRecorder.stop();
    return new Promise((resolve, reject) => {
      this.#stopping = worked => {
        (worked ? resolve : reject).call(this);
        this.#stopping = undefined;
      }
    })
  }

  recieve(e) {
    this.#recording.recieve(e);
  }

  upload(url) {
    var data = new FormData()
    data.append('file', this.#recording.blob(), 'file')
    return fetch(url, {method: "POST", body: data})
  }

  get state() {
    return this.#mediaRecorder.state
  }

  debug(v) {
    document.getElementById("footer").innerText = v;
  }
}

// https://github.com/mdn/webaudio-examples
class MeteredRecorder extends Recorder {
  #audioCtx
  #analyser
  #bins
  #buffer
  initialize() {
    this.#audioCtx = new AudioContext();
    this.#analyser = this.#audioCtx.createAnalyser();
    this.#analyser.minDecibels = -90;
    this.#analyser.maxDecibels = -10;
    this.#analyser.smoothingTimeConstant = 0.85;
    this.#analyser.fftSize = 256;
    this.#bins = this.#analyser.frequencyBinCount;
    this.#buffer = new Uint8Array(this.#bins);
  }

  onSuccess(stream) {
    this.initialize()
    super.onSuccess(stream)
    const source = this.#audioCtx.createMediaStreamSource(stream);
    source.connect(this.#analyser)
    this.visualize()
    // echo playback:
    //this.#analyser.connect(this.#audioCtx.destination);
  }

  #soundBars = ".sound-bar"
  volumeBars(v) {
    if (document.readyState !== "complete") {
      window.addEventListener("load", e => this.volumeBars(v), {passive: true});
      return
    }

    this.#soundBars = document.querySelectorAll(this.#soundBars)
    this.volumeBars = v => { // v in {0, 1, 2, 3}
      console.assert(0 <= v && v <= this.#soundBars.length
        && v == Math.trunc(v));
      for(var i = 0; i < v; i++) {
        this.#soundBars[i].classList.add("active")
      }
      for(; i < this.#soundBars.length; i++) {
        this.#soundBars[i].classList.remove("active")
      }
    }
  }

  rms() {
    let total = 0;
    for (let i of this.#buffer) {
      total += Math.sqrt(i / 255)
    }
    return Math.pow(total / this.#bins, 2)
  }

  visualize() {
    requestAnimationFrame(() => this.visualize())
    this.#analyser.getByteFrequencyData(this.#buffer);
    this.volume(Math.log(this.rms()));
  }

  #cutoffs = [-8, -6, -4]
  volume(v) {
    for (var i = 0; i < this.#cutoffs.length; i++) {
      if (v < this.#cutoffs[i]){
        break
      }
    }
    this.volumeBars(i)
  }
}

class InteractiveRecorder extends MeteredRecorder {
  #audio
  #mic
  #steps = "#playback-wrapper, #recording-wrapper";
  constructor(audio) {
    super()
    new LoadQueue().add(() => {
      findButtons(this)
      this.#mic = document.getElementById("sound-wrapper")
      this.#steps = document.querySelectorAll(this.#steps);
    })
    this.#audio = audio
    const f = audio.initialize
    audio.initialize = () => {
      f.call(audio)
      audio.audio.addEventListener("ended", this.ready.bind(this))
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

  async complete() {
    if (this.state === "recording") {
      await this.stop().then(() => this.complete())
      return
    }
    this.nextButton.disabled = true;
    await this.#audio.result(1, k => {
      return this.upload(`/jnd/api/quick/result`).then(response => {
        if (!response.ok) this.debug(response.statusText);
        return response
      }).catch(e => {
        this.debug(e.message)
        console.error(e)
        return Promise.reject(e)
      })
    })
    this.highlight(0)
    this.#audio.play()
  }

  autostart() { return true; }

  activate() {
    this.create()
    this.start()
    resetPlaybackButton(this.playbackButton, "done");
    this.playbackButton.onclick = () => this.done()
    this.nextButton.onclick = () => this.complete()
    this.nextButton.disabled = false;
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
}

let audio = new AudioResults();
let recorder = new InteractiveRecorder(audio);

