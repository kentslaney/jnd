function apijson(response) {
  if (!response.ok) {
    return Promise.reject(response)
  }
  return response.json();
}

const pass = () => {};

class AudioPrefetch {
  static audioQuery = "#playing"
  static debugQuery = "#filename-debug"

  constructor() {
    window.addEventListener("load", () => {
      this.result_promise = this.require_retry(() => this.start()
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
              this.play(cur);
              this.prefetch(Object.assign(next, {0: cur}));
          }
          return Promise.resolve(data);
        }).then(this.initialize));
      this.sync_result();
    })
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
    for (const i in this.url_map) {
      if (!keep.has(i)) {
        URL.revokeObjectURL(i);
        delete this.url_map[i];
      }
    }
    for (const i in this.next_abort) {
      if (keep.has(this.prefetching[i])) {
        // find key in next with the value that matches next[i]
        for (const [k, v] of Object.entries(next)) {
          if (v === this.prefetching[i]) {
            keep_abort[k] = this.next_abort[i]
          }
        }
      } else {
        this.next_abort[i].abort()
      }
    }
    this.next_abort = Object.assign({}, keep_abort);
    this.prefetching = next;
    for (const i in next) {
      if (next[i] in this.url_map) {
        this.prefetching[i] = this.url_map[next[i]];
        continue;
      }
      if (next[i] === "" || i in keep_abort || i === 0) continue;
      let abort = this.next_abort[i] = new AbortController();
      fetch(next[i], { signal: abort.signal })
        .then(response => response.arrayBuffer())
        .then(((i, url) => buffer => {
          const blob = new Blob([buffer], { type: "audio/wav" });
          this.url_map[url] = this.prefetching[i] = URL.createObjectURL(blob);
        })(i, next[i]));
    }
  }

  play(url) {
    if (url === "") {
      this.sync_result().then(() => window.location.href = "/jnd/done.html");
    } else {
      this.playback_debug(url);
      const audio = document.querySelector(this.audioQuery);
      audio.src = url;
      audio.play();
    }
  }

  playback_debug(url) {
    const debug = document.querySelector(this.debugQuery);
    debug.innerText = this.get_real_url(url);
  }

  get_real_url(uri) {
    const url = Object.entries(this.url_map).find(v => v[1] === uri);
    return url === undefined ? uri : url[0]
  }

  // returns a promise for the current result_promise to finish
  sync_result() {
    if (this.result_promise !== null) {
      const o = {};
      return Promise.race([this.result_promise, o]).then(async function(v) {
        if (v === o) {
          this.waiting()
          await this.result_promise;
          this.waited()
        }
      });
    }
  }

  // asks the user to rety f until it returns a promise that resolves
  #retry = pass;
  require_retry(f) {
    return f().catch(async function(e) {
      console.error(e)
      this.failed()
      await new Promise((resolve, reject) => {
        this.retrying(false)
        const call_retry = this.retry = () => {
          this.retrying(true)
          this.retry = pass;
          f().then(() => {
            resolve();
          }).catch(e => {
            this.retrying(false)
            this.retry = call_retry;
          })
        }
        this.retries(call_retry)
      })
      this.success()
    });
  }

  async result(key, f=undefined) {
    this.retry();
    await this.sync_result();

    const url = this.prefetching[key];
    this.result_promise = this.require_retry(() => {
      return (f === undefined ? this.submit(key) : f(key))
          .then(apijson)
          .then((data) => this.prefetch(Object.assign(data, {0: url})));
    })
    this.play(url);
  }

  start() { throw new Error("unimplemented") }
  submit(key) { throw new Error("unimplemented") }
  initialize(data) {}
  waiting() {}
  waited() {}
  failed() {}
  success() {}
  retries(f) {}
  retrying(still) {}
}
