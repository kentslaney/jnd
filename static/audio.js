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
  #loaded
  constructor(that) {
    this.#that = that
    this.loaded = document.readyState === "complete"
    if (!this.loaded) {
      let t = this
      window.addEventListener("load", () => this.load.call(t), {passive: true});
    }
  }

  load() {
    for (let i of this.#q) i();
    for (let j of this.#v) j();
    this.loaded = true;
  }

  add(f, arr) {
    const g = r => r.call(this.#that, f.call(this.#that))
    arr = arr === undefined ? this.#q : arr;
    return new Promise((resolve, reject) => {
      if (this.#loaded) g(resolve);
      else arr.push(() => g(resolve))
    })
  }

  // wait resolves after functions in q from add
  async wait(arg) {
    return this.add(() => arg, this.#v)
  }
}

class AudioPrefetch {
  audio;
  constructor(audio) {
    let q = new LoadQueue(this)

    q.add(() => {
      this.audio = audio
      if (typeof this.audio === 'string') {
        this.audio = document.querySelector(audio);
      }

      this.initialize()
    })

    this.#result_promise = this.require_retry(() => this.start()
      .then(response => {
        if (response.status == 400) { // landed without cookies
          window.location.href = "/jnd";
        }
        return response;
      }).then(apijson).then(data => {
        let { cur, next } = data;
        if (cur === "") { // clicked back after done.html
          window.location.href = "/jnd";
        } else {
            this.prefetch(Object.assign({0: cur}, next));
        }
        return Promise.resolve(data);
      }).then(a => q.wait.call(q, a)).then(data => {
        this.src(data["cur"]);
        // TODO: canplaythrough
        // https://developer.mozilla.org/en-US/docs/Web/HTML/Element/audio
        // using the prefetch url to stream on load ends up choppy as is
        //this.src(this.#prefetching[0]);
        return Promise.resolve(data)
      }).then(data => this.load.call(this, data)));
    q.add(this.sync_result)
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
      this.sync_result().then(() => window.location.href = "/jnd/done.html");
    } else {
      this.playback_debug(url); // TODO?: comment out for prod?
      this.audio.src = url;
      this.audio.play().catch(e => {
        console.error(e);
        this.ready();
      });
    }
  }

  playback_debug(url) {
    const debug = document.querySelector(this.debugQuery);
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
    let that = this;
    return f().catch(async function(e) {
      console.error(e)
      that.failed.call(that)
      await new Promise((resolve, reject) => {
        that.retrying.call(that, false)
        const call_retry = that.#retry = () => {
          that.retrying.call(that, true)
          that.#retry = pass;
          f().then(() => {
            resolve();
          }).catch(e => {
            that.retrying.call(that, false)
            that.#retry = call_retry;
          })
        }
        that.retries.call(that, call_retry)
      })
      that.redeemed()
    });
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

  start() { throw new Error("unimplemented") }
  submit(key) { throw new Error("unimplemented") }
  initialize() {}
  load(data) {}
  waiting() {}
  waited() {}
  failed() {}
  retries(f) {}
  retrying(still) {}
  redeemed() {}
  ready() {}
  debug(url) {}
}
