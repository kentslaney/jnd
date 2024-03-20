function start() {
  return fetch("/jnd/api/quick/start")
}

function initialize(data) {
  let { name } = data;
  document.getElementById("username").firstElementChild.innerText = name;
}

if (!navigator.mediaDevices.getUserMedia) {
  console.error("media devices API unsupported")
}

const constraints = { audio: true };
let chunks = [];

let volume;
window.addEventListener("load", () => {
  sounds = [".sound-bar.first", ".sound-bar.second", ".sound-bar.third"]
  sounds = sounds.map(x => document.querySelector(x))
  volume = v => { // v in {0, 1, 2, 3}
    console.assert(0 <= v && v <= 1);
    v = Math.min(Math.trunc(v * (sounds.length + 1)), sounds.length)
    for(var i = 0; i < v; i++) {
      sounds[i].classList.add("active")
    }
    for(; i < sounds.length; i++) {
      sounds[i].classList.remove("active")
    }
  }
  // https://developer.mozilla.org/en-US/docs/Web/API/AnalyserNode/getByteFrequencyData
  // https://codepen.io/huooo/pen/xJNPOL
  volume(1)
})

let onSuccess = function (stream) {
  const mediaRecorder = new MediaRecorder(stream);

  const record = document.getElementById("record")
  const start = function () {
    mediaRecorder.start();
    record.setAttribute("value", "stop")
    record.onclick = stop;
  }

  const stop = function () {
    mediaRecorder.stop();
    record.setAttribute("value", "start")
    record.onclick = start;
  }

  record.onclick = start

  mediaRecorder.onstop = function (e) {
    const blob = new Blob(chunks, { type: mediaRecorder.mimeType });
    chunks = [];
    var data = new FormData()
    data.append('file', blob , 'file')
    result(1, (k) =>
      fetch(`/jnd/api/quick/result`, {method: "POST", body: data}))
  }

  // TODO: start uploading audio stream as it's recorded
  mediaRecorder.ondataavailable = function (e) {
    chunks.push(e.data);
  };
}

navigator.mediaDevices.getUserMedia(constraints).then(onSuccess)
  .catch(e => {
    throw new DOMException("User denied mic permissions", {cause: e});
  });

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
})
