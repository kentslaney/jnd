// prefetching keeps either the remote URL or blob URL for each
// url_map maps from remote URLs to blob URLs
let prefetching = {}, next_abort = {}, url_map = {}, result_promise = null;
// prefetches both of the next possible audio files
// empty string means that the test is done if they choose that option
// TODO: a generic audio prefetch class per URL might be more reusable
function prefetch(next) { // next = {-1: URL|"", [0: cur URL,] 1: URL|""}
  let keep_abort = {}
  // deallocate prefetched resources that aren't reused
  const keep = new Set(Object.values(next));
  for (const i in url_map) {
    if (!keep.has(i)) {
      URL.revokeObjectURL(i);
      delete url_map[i];
    }
  }
  for (const i in next_abort) {
    if (keep.has(prefetching[i])) {
      // find key in next with the value that matches next[i]
      for (const [k, v] of Object.entries(next)) {
        if (v === prefetching[i]) {
          keep_abort[k] = next_abort[i]
        }
      }
    } else {
      next_abort[i].abort()
    }
  }
  next_abort = Object.assign({}, keep_abort);
  prefetching = next;
  for (const i in next) {
    if (next[i] in url_map) {
      prefetching[i] = url_map[next[i]];
      continue;
    }
    if (next[i] === "" || i in keep_abort || i === 0) continue;
    let abort = next_abort[i] = new AbortController();
    fetch(next[i], { signal: abort.signal })
      .then(response => response.arrayBuffer())
      .then(((i, url) => buffer => {
        const blob = new Blob([buffer], { type: "audio/wav" });
        url_map[url] = prefetching[i] = URL.createObjectURL(blob);
      })(i, next[i]));
  }
}

function apijson(response) {
  if (!response.ok) {
    throw Error(response.statusText);
  }
  return response.json();
}

window.addEventListener("load", () => {
  result_promise = require_retry(() => start()
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
          play(cur);
          prefetch(Object.assign(next, {0: cur}));
      }
    }));
  sync_result();
})

function play(url) {
  if (url === "") {
    sync_result().then(() => window.location.href = "/jnd/done.html");
  } else {
    playback_debug(url);
    const audio = document.getElementById("playing");
    audio.src = url;
    audio.play();
  }
}

function playback_debug(url) {
  const debug = document.getElementById("filename-debug");
  debug.innerText = get_real_url(url);
}

function get_real_url(uri) {
  const url = Object.entries(url_map).find(v => v[1] === uri);
  return url === undefined ? uri : url[0]
}

// returns a promise for the current result_promise to finish
function sync_result() {
  const answers = document.getElementsByClassName("answer");
  const waiting = document.getElementById("waiting");

  if (result_promise !== null) {
    const o = {};
    return Promise.race([result_promise, o]).then(async function(v) {
      if (v === o) {
        for (const i of answers) i.disabled = true;
        waiting.classList.remove("hidden");
        await result_promise;
        for (const i of answers) i.disabled = false;
        waiting.classList.add("hidden");
      }
    });
  }
}

// asks the user to rety f until it returns a promise that resolves
const pass = () => {};
let retry = pass;
function require_retry(f) {
  const failed = document.getElementById("failed");
  const retry_button = document.getElementById("retry");

  return f().catch(async function(e) {
    console.error(e)
    failed.classList.remove("hidden");
    await new Promise((resolve, reject) => {
      retry_button.disabled = false;
      const call_retry = retry_button.onclick = retry = () => {
        retry_button.disabled = true;
        retry = pass;
        f().then(() => {
          resolve();
        }).catch(e => {
          retry_button.disabled = false;
          retry = call_retry;
        })
      }
    })
    failed.classList.add("hidden");
  });
}

async function result(key, f=undefined) {
  retry();
  await sync_result();

  const url = prefetching[key];
  result_promise = require_retry(() => {
    return (f === undefined ? submit(key) : f(key))
        .then(apijson)
        .then((data) => prefetch(Object.assign(data, {0: url})));
  })
  play(url);
}

function start() {
  throw new Error("unimplemented")
}

function submit(key) {
  throw new Error("unimplemented")
}
