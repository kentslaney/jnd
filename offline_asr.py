import sqlite3, pathlib
import json
from tqdm import tqdm

basename = pathlib.Path(__file__).parents[0]
con = sqlite3.connect(str(basename / "experiments.db"))

def quick_queue():
    cur = con.execute(
            "SELECT quick_results.id, reply_filename, answer "
            "FROM quick_results "
            "LEFT JOIN quick_trials ON quick_results.trial = quick_trials.id "
            "LEFT JOIN quick_asr ON quick_results.id=quick_asr.ref "
            "WHERE quick_asr.data IS NULL OR quick_asr.data = ''")
    q = cur.fetchall()
    cur.close()
    return q

def update(rowid, res):
    res = json.dumps(res)
    cur = con.cursor()
    cur.execute("INSERT INTO quick_asr (ref, data) VALUES (?, ?)", (rowid, res))
    con.commit()
    cur.close()

def main(asr):
    for rowid, fname, ans in tqdm(quick_queue()):
        update(rowid, asr(str(basename / "uploads" / fname)))

def deduplicate(**kw):
    dup, sep = "json_extract(data, '$.' || ?) = ?", " AND "
    clause = sep.join((dup,) * len(kw))
    args = sum(kw.items(), ())
    cur = con.cursor()
    cur.execute("DELETE FROM quick_asr WHERE " + clause, args)
    con.commit()
    cur.close()

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
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    if args.force:
        model_type = "default" if args.asr == "WhisperASR" else "prompted"
        deduplicate(model_name=args.model, model_type=model_type)
    import asr
    main(getattr(asr, args.asr)(args.model))

