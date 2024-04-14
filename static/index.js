// https://en.wikipedia.org/wiki/Unicode_character_property#General_Category
// valid username characters: letters, number digits, number letters,
//                            punctuation connectors, punctuation dashes
const username_re = /[^\p{L}\p{Nd}\p{Nl}\p{Pc}\p{Pd}\p{Zs}]/u;
// time to wait before checking API for username availibility
// avoids unnecessary requests for partially typed values
const debounce_ms = 200;
// request_controller cancels earlier API requests if a new one is made
let request_controller = null, previous_username = null;
function apijson(response) {
  if (!response.ok) {
    return Promise.reject(response)
  }
  return response.json()
}

function check_username() {
  const input = document.getElementById("username").value;
  const output = document.getElementById("username-status");
  const submit = document.getElementById("submit");
  // avoids checking on key up for the shift key, for example
  if (input === previous_username) return;
  previous_username = input;
  let invalid;
  if (input === "") {
    output.innerText = "";
    submit.disabled = true;
  } else if (input.length > 512) {
    output.innerText = "Too long";
    submit.disabled = true;
  } else if (invalid = input.match(username_re)) {
    // specify "whitespace" for invisible error specifics
    const char_type = invalid[0].match(/\p{Zs}/u) ? "whitespace " : "";
    output.innerText = `Invalid ${char_type}character "${invalid[0]}"`;
    submit.disabled = true;
  } else {
    output.innerText = "";
    submit.disabled = false;
    if (request_controller !== null) {
      request_controller.abort();
    }
    request_controller = new AbortController();
    const signal = request_controller.signal;
    setTimeout(() => {
      if (signal.aborted) return;
      output.innerText = "checking availability...";
      const query = encodeURIComponent(input);
      request = fetch(`/jnd/api/username-available?v=${query}`, { signal })
        .then(apijson).then((data) => {
          if (data) {
            output.innerText = "";
            submit.disabled = false;
          } else {
            output.innerText = "Username not available";
            submit.disabled = true;
          }
        }).catch((error) => {
          if (!signal.aborted) {
            output.innerText = "Couldn't reach the server";
          }
        });
    }, debounce_ms);
  }
}

function claim_username() {
  const input = document.getElementById("username").value;
  const output = document.getElementById("username-status");
  const submit = document.getElementById("submit");
  if (request_controller !== null) {
    request_controller.abort();
  }
  request_controller = new AbortController();
  const signal = request_controller.signal;
  submit.disabled = true;
  const query = encodeURIComponent(input);
  request = fetch(`/jnd/api/set-username?v=${query}`, { signal })
    .then(apijson).then((data) => {
      if (data) {
        // window.location.href = "/jnd/pitch.html";
        window.location.href = "/jnd/quick.html";
        submit.disabled = false;
      } else {
        output.innerText = "Username not available";
      }
    }).catch((error) => {
      if (!signal.aborted) {
        output.innerText = "Couldn't reach the server";
        submit.disabled = false;
      }
    })
}

// catches autofilled values
window.addEventListener("load", check_username);
fetch("/jnd/api/authorized", { method: "POST" }).then(apijson).catch(e => {
  if (e.status === 401) {
    window.location.href = "/login?next=" + encodeURIComponent(
      window.location.href)
  }
})

let recorder
window.addEventListener("load", () => {
  let samples = document.getElementById("samples")
  for (const el of document.getElementsByClassName("playback-interface")) {
    const src = el.getAttribute("data-src")
    if (src === null) continue
    let audio = document.createElement("audio")
    audio.addEventListener("canplaythrough", ((el, audio) => () => {
      el.classList.remove("load")
      el.classList.add("play")
      let playing = false
      const f = () => {
        playing = !playing
        el.classList.remove(playing ? "play" : "pause")
        el.classList.add(playing ? "pause" : "play")
        if (playing) audio.play()
        else audio.pause()
      }
      el.addEventListener("click", f)
      audio.addEventListener("ended", f)
    })(el, audio))
    audio.src = src
    audio.setAttribute("preload", "")
    samples.appendChild(audio)
  }
  recorder = new DiscretelyTunedRecorder(".sound-dot")
})

