window.addEventListener("load", e => {
  const params = new URL(document.baseURI).searchParams
  const debug = params.get("debug")
  const project = params.get("project")
  if (debug === "true") {
    const results = document.getElementById("results")
    results.href = `api/${project}/plot?t=${Date.now()}`;
    document.getElementById("recognized").href =
      `recognized.html?project=${project}`
    for (const el of document.getElementsByClassName("debug")) {
      el.classList.remove("hidden")
    }
  }
}, { passive: true })

function reset(e) {
  const project = new URL(document.baseURI).searchParams.get("project")
  const api = `api/${project}/reset`
  const el = e.target
  e.target.classList.add("loading")
  fetch(api, {method: "POST" }).then(response => {
    if (response.ok) {
      window.location.href = `${project}.html`
    } else {
      return Promise.reject(response)
    }
  }).catch(e => {
    el.classList.remove("loading")
    el.classList.add("failed")
  })
}

async function submit_effort() {
  const project = new URL(document.baseURI).searchParams.get("project")
  const api = `api/${project}/reset`
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
