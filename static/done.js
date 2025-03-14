window.addEventListener("load", e => {
  const params = new URL(document.baseURI).searchParams
  const debug = params.get("debug")
  const project = params.get("project")
  if (debug === "true") {
    const results = document.getElementById("results")
    results.href = `/jnd/api/${project}/plot?t=${Date.now()}`;
    document.getElementById("recognized").href =
      `recognized.html?project=${project}`
    for (const el of document.getElementsByClassName("debug")) {
      el.classList.remove("hidden")
    }
  }
}, { passive: true })

function reset(e) {
  const params = new URL(document.baseURI).searchParams
  const project = params.get("project")
  const api = `/jnd/api/${project}/reset`
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

