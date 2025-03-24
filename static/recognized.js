const params = new URL(document.baseURI).searchParams
const project = params.get("project")

fetch(`api/${project}/recognized${window.location.search}`)
  .then(response => response.json())
  .then(data => {
    let users = {}
    for (const row of data) {
      if (!(row["subject"] in users)) {
        users[row["subject"]] = {
          "id": row["subject"],
          "time": new Date(row["time"] + " UTC"),
          "username": row["username"],
          "results": []
        };
      }
      asr_data = row["transcript"] === null ? null :
        JSON.parse(row["transcript"]);
      users[row["subject"]]["results"].push({
        "prompt": `${project}/${row["prompt"]}`,
        "upload": `api/${project}/upload/${row["upload"]}`,
        "transcript": row["transcript"] === null ? null : asr_data["text"],
        "asr_data": asr_data,
        "answer": row["answer"].split(","),
        "annotations": row["annotations"]
      });
    }
    let entries = Object.entries(users)
      .sort(([a,], [b,]) => a - b).map(([,k]) => k);

    const [head, body] = Array.prototype.map.call(
      document.querySelectorAll(".template"), x => {
        let copy = x.cloneNode(true)
        copy.classList.remove("template")
        return copy
      })
    const parent = document.querySelector(".template").parentElement

    for (const user of entries) {
      user_head = parent.appendChild(head.cloneNode(true))
      let plot = document.createElement("a")
      plot.href = `api/${project}/plot?user=${user["id"]}`
      plot.innerText = user["username"]
      // plot.setAttribute("target", "_blank")
      user_head.querySelector(".username").appendChild(plot)
      const datestr = user["time"].toLocaleTimeString("en-US", {
        hour12: false, year: "numeric", month: "2-digit", day: "2-digit",
        timeZoneName: "short" });
      user_head.querySelector(".time").innerText = datestr

      for (const trial of user["results"]) {
        el = parent.appendChild(body.cloneNode(true))
        el.querySelector(".prompt").src = trial["prompt"]
        el.querySelector(".response").src = trial["upload"]
        el.querySelector(".transcript").innerText = trial["transcript"]
        const ans = el.querySelector(".answer")
        if (trial["annotations"] === undefined) {
          ans.innerText = trial["answer"].join(",")
        } else {
          for (let i = 0; i < trial["answer"].length; i++) {
            const container = ans.appendChild(document.createElement("span"))
            container.innerText = trial["answer"][i]
            const result = trial["annotations"][i]
            container.classList.add(result ? "correct": "incorrect")
          }
        }
      }
    }

    if((new URLSearchParams(window.location.search)).get("user") == "all") {
      let a = document.querySelector("#showall");
      a.href = `api/${project}/plot?user=all`
      // a.setAttribute("target", "_blank")
    }
  })
