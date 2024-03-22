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

// TODO: autoplay success
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

  retries(f) {
    this.nextButton.onclick = f
  }

  retrying(still) {
    // TODO: only display while blocked
    resetPlaybackButton(this.playbackButton, still ? "load" : "error");
    this.nextButton.disabled = still
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

  // TODO: start uploading audio stream as it's recorded
  blob() {
    return new Blob(this.#chunks, { type: this.#mediaRecorder.mimeType });
  }
}

class Recorder {
  #soundBars = [".sound-bar.first", ".sound-bar.second", ".sound-bar.third"];
  volumeBars(v) {
    if (document.readyState !== "complete") {
      window.addEventListener("load", e => this.volumeBars(v), {passive: true});
      return
    }

    this.#soundBars = this.#soundBars.map(x => document.querySelector(x))
    this.volumeBars = v => { // v in {0, 1, 2, 3}
      console.assert(0 <= v && v <= this.#soundBars.length
        && v == Math.trunc(v));
      v = Math.min(Math.trunc(v * (sounds.length + 1)), sounds.length)
      for(var i = 0; i < v; i++) {
        sounds[i].classList.add("active")
      }
      for(; i < sounds.length; i++) {
        sounds[i].classList.remove("active")
      }
    }
  }

  #mic
  constructor() {
    new LoadQueue().add(() => {
      findButtons(this)
      this.#mic = document.getElementById("sound-wrapper")
    })
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
    this.#mediaRecorder.ondataavailable = e => this.recieve.call(this, e)
  }

  #recording
  create() {
    this.#recording = new Recording(this.#mediaRecorder)
  }

  start() {
    this.#stopnt()
    this.#mediaRecorder.start(); // TODO catch err?
    this.#mic.classList.add("active")
  }

  #stopping
  #stopped() { if (this.#stopping !== undefined) this.#stopping(true); }
  #stopnt() { if (this.#stopping !== undefined) this.#stopping(false); }

  stop() {
    this.#stopnt()
    this.#mic.classList.remove("active")
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

class InteractiveRecorder extends Recorder {
  #audio
  constructor(audio) {
    super()
    this.#audio = audio
    const f = audio.initialize
    let that = this
    audio.initialize = () => {
      f.call(audio)
      audio.audio.addEventListener("ended", () => that.ready())
    }
  }

  async complete() {
    if (this.state === "recording") {
      await this.stop().then(() => this.complete())
      return
    }
    this.nextButton.disabled = true;
    await this.#audio.result(1, k => this.upload(`/jnd/api/quick/result`));
    this.#audio.play()
  }

  autostart() { return true; }
  // TODO: user option? pause instead of restart recording?

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
    // TODO switch activation row
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

