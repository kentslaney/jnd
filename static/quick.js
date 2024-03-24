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
    super.result(key, k => f(k).then(data => {
      this.#backlogged -= 1;
      return data
    }));
  }

  retries(f) {
    this.nextButton.onclick = f
  }

  retrying(still) {
    if (this.#backlogged === 2) {
      resetPlaybackButton(this.playbackButton, still ? "load" : "error");
      this.nextButton.disabled = still
    }
  }

  redeemed() {
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

class Recording {
  #chunks = [];

  #mediaRecorder
  constructor(mediaRecorder) {
    this.#mediaRecorder = mediaRecorder
  }

  recieve(e) {
    this.#chunks.push(e.data)
  }

  // TODO?: start uploading audio stream as it's recorded?
  //        it would interfere with the ability to rerecord so unclear
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
        throw new DOMException("user denied mic permissions", {cause: e});
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
    this.#mediaRecorder.start(); // TODO?: catch err?
  }

  #stopping
  #stopped() { if (this.#stopping !== undefined) this.#stopping(true); }
  #stopnt() { if (this.#stopping !== undefined) this.#stopping(false); }

  stop() {
    this.#stopnt()
    this.#mediaRecorder.stop();
    let that = this;
    return new Promise((resolve, reject) => {
      that.#stopping = worked => {
        (worked ? resolve : reject).call(that);
        that.#stopping = undefined;
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
    this.debug(v)
    for (var i = 0; i < this.#cutoffs.length; i++) {
      if (v < this.#cutoffs[i]){
        break
      }
    }
    this.volumeBars(i)
  }

  debug(v) {
    //document.getElementById("footer").innerText = v;
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
    let that = this
    audio.initialize = () => {
      f.call(audio)
      audio.audio.addEventListener("ended", () => that.ready())
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
    await this.#audio.result(1, k => this.upload(`/jnd/api/quick/result`));
    this.highlight(0)
    this.#audio.play()
  }

  // TODO?: user option? pause instead of restart recording?
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

let audio = new Audio();
let recorder = new InteractiveRecorder(audio);

