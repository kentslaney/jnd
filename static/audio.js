function apijson(response) {
  if (!response.ok) {
    return Promise.reject(response)
  }
  return response.json();
}

const pass = () => {};

class LoadQueue {
  #q = []
  #v = []
  #that
  // binds this in function context to that given below
  constructor(that) {
    this.#that = that
    if (!this.loaded) {
      window.addEventListener("load", this.load.bind(this), {passive: true});
    }
    this.wait = this.wait.bind(this)
  }

  get loaded() {
    return document.readyState === "complete"
  }

  load() {
    for (let i of this.#q) i();
    for (let j of this.#v) j();
  }

  add(f, other, arr) {
    const that = other === undefined ? this.#that : other
    if (that === undefined) {
      var g = r => r(f())
    } else {
      var g = r => r.call(that, f.call(that))
    }

    arr = arr === undefined ? this.#q : arr;
    const preloaded = this.loaded
    if (preloaded) {
      var res = g(x => x)
    }
    return new Promise(((resolve, reject) => {
      if (preloaded) resolve(res)
      else if (this.loaded) g(resolve);
      else arr.push(() => g(resolve))
    }).bind(this))
  }

  // wait resolves after functions in q from add
  async wait(arg) {
    return this.add(() => arg, undefined, this.#v)
  }
}

class AudioPrefetch {
  audio;
  loadq
  constructor(audio) {
    this.loadq = new LoadQueue(this)

    this.loadq.add(() => {
      this.audio = audio
      if (typeof this.audio === 'string') {
        this.audio = document.querySelector(audio);
      }
      this.audio.addEventListener("canplaythrough", e => this.loaded())
      this.initialize()
    })

    this.#result_promise = this.require_retry(() => this.start()
      .then(response => {
        if (response.status == 400) { // landed without cookies
          this.restart()
        }
        return response;
      }).then(apijson).then(data => {
        let { cur, next } = data;
        if (cur === "") { // clicked back after done.html
          this.restart()
        } else {
            this.prefetch(Object.assign({0: cur}, next));
        }
        return Promise.resolve(data);
      }).then(this.loadq.wait).then(data => {
        this.load.call(this, data)
        return data
      }).then(data => {
        this.src(this.#prefetching[0]);
        return Promise.resolve(data)
      }));
    this.loadq.add(this.sync_result)
  }

  // prefetching keeps either the remote URL or blob URL for each
  // url_map maps from remote URLs to blob URLs
  #prefetching = {};
  #next_abort = {};
  #url_map = {};
  #result_promise = null;
  // prefetches both of the next possible audio files
  // empty string means that the test is done if they choose that option
  prefetch(next) { // next = {-1: URL|"", [0: cur URL,] 1: URL|""}
    let keep_abort = {}
    // deallocate prefetched resources that aren't reused
    const keep = new Set(Object.values(next));
    for (const i in this.#url_map) {
      if (!keep.has(i)) {
        URL.revokeObjectURL(i);
        delete this.#url_map[i];
      }
    }
    for (const i in this.#next_abort) {
      if (keep.has(this.#prefetching[i])) {
        // find key in next with the value that matches next[i]
        for (const [k, v] of Object.entries(next)) {
          if (v === this.#prefetching[i]) {
            keep_abort[k] = this.#next_abort[i]
          }
        }
      } else {
        this.#next_abort[i].abort()
      }
    }
    this.#next_abort = Object.assign({}, keep_abort);
    this.#prefetching = next;
    for (const i in next) {
      if (next[i] in this.#url_map) {
        this.#prefetching[i] = this.#url_map[next[i]];
        continue;
      }
      if (next[i] === "" || i in keep_abort || i === 0) continue;
      let abort = this.#next_abort[i] = new AbortController();
      fetch(next[i], { signal: abort.signal })
        .then(response => response.arrayBuffer())
        .then(((i, url) => buffer => {
          const blob = new Blob([buffer], { type: "audio/wav" });
          this.#url_map[url] = this.#prefetching[i] = URL.createObjectURL(blob);
        })(i, next[i]));
    }
  }

  src(url) {
    if (url === "") {
      this.sync_result().then(this.done.bind(this));
    } else {
      this.playback_debug(url);
      this.loading()
      this.audio.src = url;
    }
  }

  playback_debug(url) {
    this.debug(this.get_real_url(url));
  }

  get_real_url(uri) {
    const url = Object.entries(this.#url_map).find(v => v[1] === uri);
    return url === undefined ? uri : url[0]
  }

  // returns a promise for the current result_promise to finish
  sync_result() {
    if (this.#result_promise !== null) {
      const o = {};
      const waiting = () => this.waiting.call(this);
      const waited = () => this.waited.call(this);
      let result = this.#result_promise;
      return Promise.race([result, o]).then(async function(v) {
        if (v === o) {
          try {
            waiting()
            await result;
          } finally {
            waited()
          }
        }
      });
    }
  }

  // asks the user to rety f until it returns a promise that resolves
  #retry = pass;
  require_retry(f) {
    return f().catch((async function(e) {
      //console.error(e)
      this.failed.call(this)
      await new Promise(((resolve, reject) => {
        this.retrying.call(this, false)
        const call_retry = this.#retry = (() => {
          this.retrying.call(this, true)
          this.#retry = pass;
          f().then(() => {
            resolve();
          }).catch(e => {
            this.retrying.call(this, false)
            this.#retry = call_retry;
          })
        }).bind(this)
        this.retries.call(this, call_retry)
      }).bind(this))
      this.recovered()
    }).bind(this));
  }

  async result(key, f=undefined) {
    this.#retry();
    await this.sync_result();

    const url = this.#prefetching[key];
    this.#result_promise = this.require_retry(() => {
      return (f === undefined ? this.submit(key) : f(key))
          .then(apijson)
          .then((data) => this.prefetch(Object.assign(data, {0: url})));
    })
    this.src(url);
  }

  // called once audio can start playing
  // attempts to autoplay by default
  loaded() {
    this.audio.play().catch(e => {
      if (e.name === "NotAllowedError") {
        console.error(e);
        this.ready();
      } else {
        Promise.reject(e)
      }
    });
  }

  start() { throw new Error("unimplemented") } // get 3 URLs from API
  submit(key) { throw new Error("unimplemented") } // submit results
  done() {} // done with test
  restart() {} // send user to start
  initialize() {} // called after page load
  load(data) {} // called after data from start() is returned
  loading() {} // called while audio is buffering
  waiting() {} // user is waiting for server response to results
  waited() {} // server responded with results
  failed() {} // results query to the server failed
  retries(f) {} // the user's next interaction should be f
  retrying(still) {} // retrying results submission or not, based on still
  recovered() {} // results successfully uploaded after failing
  ready() {} // audio loaded but autoplay prevented; requires interaction
  debug(url) {} // called with the currently playing URL on audio src change
}

class Recording {
  chunks = [];
  #streaming
  #chunkID = 0
  #blockID = -1
  #queue = 0
  #_semaphore = 0
  #block = undefined
  #blocking = false
  #resolve = () => {}
  #total = 0
  #mediaRecorder

  // streaming is WS URL, messageHandler recieves WS events
  constructor(mediaRecorder, streaming, messageHandler) {
    this.#mediaRecorder = mediaRecorder;
    if (streaming !== undefined) {
      let ready;
      this.#blocking = true
      this.#block = new Promise((resolve, reject) => { ready = resolve })
      this.#streaming = new WebSocket(streaming);
      this.#streaming.addEventListener("open", () => {
        ready()
        this.#blocking = false
      })
      this.#streaming.addEventListener("message", messageHandler)
      mediaRecorder.addEventListener("start", this.reset.bind(this))
      mediaRecorder.addEventListener("stop", this.wait.bind(this))
    }
    mediaRecorder.addEventListener("start", this.clear.bind(this))
    mediaRecorder.addEventListener("dataavailable", this.recieve.bind(this))
  }

  get #semaphore() {
    return this.#_semaphore
  }

  set #semaphore(v) {
    this.#_semaphore = v
    if (v === 0) this.#resolve()
  }

  async recieve(e) {
    this.chunks.push(e.data)
    this.#total = e.data.size
    if (this.#streaming) this.stream(e)
  }

  async blob() {
    return new Blob(this.chunks, { type: this.#mediaRecorder.mimeType });
  }

  clear() {
    this.chunks = []
  }

  async reset(e) {
    if (this.#block !== undefined) {
      this.#blocking = true
      await this.#block
    }
    this.#chunkID = this.#queue;
    this.#queue = 0;
    this.#blockID += 1;
    this.#total = 0
  }

  async wait(e) {
    if (this.#blocking) await this.#block
    let ready
    this.#block = new Promise((resolve, reject) => {
      ready = resolve
    })
    this.#resolve = () => {
      ready()
      this.#resolve = () => {}
      this.#blocking = false
    }
  }

  async stream(e) {
    let chunk
    if (this.#blocking) {
      chunk = this.#queue++
      await this.#block
    } else {
      chunk = this.#chunkID++
    }
    const block = this.#blockID
    this.#semaphore += 1
    // timecode isn't guaranteed to start at 0 so chunk is needed
    const data = new Blob([Uint32Array.of(block, chunk, e.timecode), e.data])
    return new Promise(() => {
      // shouldn't be able to fail
      this.#streaming.send(data)
    }).finally(() => {
      this.#semaphore -= 1
    })
  }

  // resolution based on timeslice param of MediaRecorder.start
  get progress() {
    const lastsEnd = this.#total / this.#mediaRecorder.audioBitsPerSecond
    if (!this.#streaming) return lastsEnd
    return [
      lastsEnd - this.#streaming.bufferedAmount / this.#total,
      lastsEnd
    ]
  }
}

class SecureRecording extends Recording {
  #key
  constructor(...args) {
    super(...args)
    this.#key = this.public().then(apijson).then(key => {
      return window.crypto.subtle.importKey(
        "jwk",
        key,
        {
          name: "RSA-OAEP",
          hash: "SHA-256",
        },
        true,
        ["encrypt"],
      );
    })
  }

  public() {
    throw new Exception("unimplemented")
  }

  // TODO: stream encrypted chunks with single header
  async encrypt(bytes) {
    const salt = window.crypto.getRandomValues(new Uint8Array(16))
    const shared = window.crypto.getRandomValues(new Uint8Array(16))
    const secret = await window.crypto.subtle.importKey(
      "raw",
      shared,
      "PBKDF2",
      false,
      ["deriveBits", "deriveKey"],
    )
    const secure = await window.crypto.subtle.deriveKey(
      {
        name: "PBKDF2",
        salt,
        iterations: 100000,
        hash: "SHA-256",
      },
      secret,
      { name: "AES-GCM", length: 256 },
      true,
      ["encrypt", "decrypt"],
    );

    const handshake = new Uint8Array(await window.crypto.subtle.encrypt(
      {
        name: "RSA-OAEP"
      },
      await this.#key,
      shared
    ));

    const cyphertext = new Uint8Array(await window.crypto.subtle.encrypt(
      {
        name: "AES-GCM",
        iv: window.crypto.getRandomValues(new Uint8Array(12))
      },
      secure,
      bytes
    ));

    return new Uint8Array([...salt, ...handshake, ...cyphertext]);
  }

  async blob() {
    return new Blob(
      [await this.encrypt(await super.blob().then(x => x.arrayBuffer()))])
  }
}

class SecureRecordingMock extends SecureRecording {
  asymmetric
  public() {
    if (this.asymmetric === undefined) {
      this.asymmetric = window.crypto.subtle.generateKey(
        {
          name: "RSA-OAEP",
          modulusLength: 4096,
          publicExponent: new Uint8Array([1, 0, 1]),
          hash: "SHA-256",
        },
        true,
        ["encrypt", "decrypt"]
      );
    }
    return this.asymmetric.then(key =>
      window.crypto.subtle.exportKey("jwk", key.publicKey)).then(key => {
        return {
          "ok": true,
          "json": () => new Promise((resolve, reject) => resolve(key))
        }
      })
  }
}

class Recorder {
  #timeslice
  #streaming
  #recording
  // timeslice is frequency of data events in ms, streaming is WS URL
  constructor(timeslice, streaming) {
    this.#timeslice = timeslice
    this.#streaming = streaming
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

  storage = Recording
  #mediaRecorder
  onSuccess(stream) {
    this.#mediaRecorder = new MediaRecorder(stream);
    this.#mediaRecorder.addEventListener("stop", this.#stopped.bind(this))
    this.#recording = new this.storage(
      this.#mediaRecorder, this.#streaming, this.messaged.bind(this))
  }

  messaged(e) {}

  start() {
    this.#stopnt()
    try {
      this.#mediaRecorder.start(this.#timeslice);
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

  async result(url, headers) {
    let data = new FormData()
    data.append('file', await this.#recording.blob(), 'file')
    return [url, {...headers, method: "POST", body: data}]
  }

  get state() {
    return this.#mediaRecorder.state
  }

  debug(v) {}
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

  volume(v) {}
}

class DiscretelyTunedRecorder extends MeteredRecorder {
  #soundBars
  constructor(soundBars, timeslice, streaming) {
    super(timeslice, streaming)
    this.#soundBars = soundBars
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

  volumeBars(v) {
    if (document.readyState !== "complete") {
      window.addEventListener("load", e => this.volumeBars(v), {passive: true});
      return
    }

    this.#soundBars = document.querySelectorAll(this.#soundBars)
    console.assert(this.#soundBars.length <= this.#cutoffs.length)
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
}

