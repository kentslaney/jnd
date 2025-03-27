class ReviewAudio extends AnnotatedAudio {
  initialize() {
    super.initialize()
    this.nextButton.onclick = () => this.result(1, k => {
      const res = JSON.stringify(this.aux_data())
      return fetch(
        `api/${this.project}/result?annotations=${res}`,
        {method: "POST"})
    })
  }

  aux_data() {
    return Array.from(document.querySelectorAll(".annotation-on")).map(
      x => x.checked)
  }
}

let audio = new ReviewAudio("review");
