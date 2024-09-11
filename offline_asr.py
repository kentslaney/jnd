import sqlite3, pathlib

basename = pathlib.Path(__file__).parents[0]
con = sqlite3.connect(str(basename / "experiments.db"))
cur = con.execute(
        "SELECT quick_results.id, reply_filename, answer "
        "FROM quick_results LEFT JOIN quick_trials "
        "ON quick_results.trial = quick_trials.id "
        "WHERE reply_asr IS NULL OR reply_asr = ''")
q = cur.fetchall()
cur.close()

import json
from asr import WhisperASR
from tqdm import tqdm
asr = WhisperASR()
for rowid, fname, ans in tqdm(q):
    out = asr(str(basename / "uploads" / fname))
    out = json.dumps(out)
    cur = con.cursor()
    cur.execute("UPDATE quick_results SET reply_asr=? WHERE id=?", (out, rowid))
    con.commit()
    cur.close()

