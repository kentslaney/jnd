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
        this.src(this.#prefetching[0]);
        return Promise.resolve(data)
      }).then(data => this.load.call(this, data)));
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

