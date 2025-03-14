const params = new URL(document.baseURI).searchParams
const project = params.get("project")

fetch(`/jnd/api/${project}/recognized`)
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

