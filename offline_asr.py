import sqlite3, pathlib
import json
from tqdm import tqdm

basename = pathlib.Path(__file__).parents[0]
con = sqlite3.connect(str(basename / "experiments.db"))

def quick_queue():
    cur = con.execute(
            "SELECT quick_results.id, reply_filename, answer "
            "FROM quick_results LEFT JOIN quick_trials "
            "ON quick_results.trial = quick_trials.id "
            "WHERE reply_asr IS NULL OR reply_asr = ''")
    q = cur.fetchall()
    cur.close()
    return q

def update(rowid, res):
    res = json.dumps(res)
    cur = con.cursor()
    cur.execute("UPDATE quick_results SET reply_asr=? WHERE id=?", (res, rowid))
    con.commit()
    cur.close()

def main(asr):
    for rowid, fname, ans in tqdm(quick_queue()):
        update(rowid, asr(str(basename / "uploads" / fname)))

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    models = [
            "tiny.en", "tiny",
            "base.en", "base",
            "small.en", "small",
            "medium.en", "medium",
            "large"]
    parser.add_argument("--model", default="large", choices=models, help=(
            "which whisper model size to use (default: large); see: "
            "https://github.com/openai/whisper#available-models-and-languages"))
    parser.add_argument(
            "--prompted", dest="asr", default="WhisperASR",
            action="store_const", const="PromptedWhisperASR", help=(
                "use the correct answer as the model prompt; can help accuracy "
                "but can also bias results towards correct"))
    args = parser.parse_args()
    import asr
    main(getattr(asr, args.asr)(args.model))

