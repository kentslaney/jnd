window.addEventListener("load", e => {
  const showing = new URL(document.baseURI).searchParams.get("debug")
  if (showing === "true") {
    const results = document.getElementById("results")
    results.href = "/jnd/api/quick/plot?t=" + Date.now();
    for (const el of document.getElementsByClassName("debug")) {
      el.classList.remove("hidden")
    }
  }
}, { passive: true })

fetch("/jnd/api/quick/recognized")
  .then(response => response.json())
  .then(data => {
    if (data.length === 0) return;
    latest = data[data.length - 1]["trial_number"]
    document.getElementById("username").innerText = data[0]["username"]
    document.getElementById("trial_number").innerText = latest
    const [correct, total] = data.reduce((a, b) => {
      if (b["trial_number"] == latest) {
        return [
              a[0] + b["annotations"].filter(x => x).length,
              a[1] + b["annotations"].length
            ]
      } else {
        return a
      }
    }, [0, 0])
    const score = 25.5 - correct / total * 30
    document.getElementById("correct").innerText = correct
    document.getElementById("total").setAttribute(
        "data-total", total === 30 ? "" : total)
    const scale = 1e1, round = Math.round(score * scale) / scale
    document.getElementById("score").innerText = round.toString()
  })

function reset(e) {
  const api = "/jnd/api/quick/reset"
  const el = e.target
  e.target.classList.add("loading")
  fetch(api, {method: "POST" }).then(response => {
    if (response.ok) {
      window.location.href = "quick.html"
    } else {
      return Promise.reject(response)
    }
  }).catch(e => {
    el.classList.remove("loading")
    el.classList.add("failed")
  })
}

async function submit_effort() {
  const api = "/jnd/api/quick/reset"
  const value = parseInt(document.getElementById("effort").value)
  const statusCase = document.getElementById("effort-status")
  if (value < 1 || value > 10) return
  let url = URL.parse(api, window.location.href)
  url.searchParams.set("v", value)
  statusCase.innerText = "loading..."
  const status = await fetch(url, { method: "POST" })
    .then(() => "recorded").catch(() => "network error")
  statusCase.innerText = status
}
