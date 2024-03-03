import os, os.path, json, random
from flask import Blueprint, request, session, abort
from utils import Database, relpath, DatabaseBP

quick_levels = 6
quick_files = relpath("all_spin_index.csv")
upload_location = relpath("uploads")

class QuickDB(Database):
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        os.makedirs(upload_location, exist_ok=True)
        with self.app.app_context():
            assert quick_levels <= self.queryone(
                "SELECT MAX(level_number) FROM quick_trials WHERE active=1")[0]

    def db_init_hook(self):
        super().db_init_hook()
        assert os.path.exists(quick_files)
        with open(quick_files, "r") as f:
            experiments = [[part.strip() for part in line.split(",", 4)]
                           for line in f]
        con = self.get()
        cur = con.cursor()
        cur.executemany(
            ("INSERT INTO quick_trials "
             "(trial_number, level_number, snr, filename, answer, active) "
             "values (?, ?, ?, ?, ?, 1)"), experiments)
        con.commit()

quick_keys = ("id", "snr", "level_number", "trial_number", "filename", "answer")
quick_trial_dict = lambda v: dict(zip(quick_keys, v))
quick_url = lambda v: v and "/jnd/quick/" + v
quick_done = [0, 0, 0, 1, "", 1]

def quick_next(db, cur, done = False):
    left = json.loads(session["left"])
    session["left"] = json.dumps(left - 1)
    if left == 0 or done:
        q = quick_done
    else:
        q = db.queryall(("SELECT * FROM quick_trials WHERE active=1 "
                        "AND level_number=?"),
                        (cur["level_number"] + 1,))
        if len(q) == 0:
            abort(400)
        q = random.choice(q)
    q = quick_trial_dict(q)
    session["q"] = json.dumps(q)
    return quick_url(q["filename"])

def quick_start(db):
    if "user" not in session:
        abort(400)
    elif "cur" in session:
        cur, q = map(lambda x: quick_url(json.loads(x)["filename"]), (
            session["cur"], session["q"]))
        return json.dumps({"cur": cur, "next": {1: q}})
    cur = db.queryall(("SELECT * FROM quick_trials WHERE active=1 AND "
                       "level_number=1"))
    cur = quick_trial_dict(random.choice(cur))
    session["cur"], session["left"] = json.dumps(cur), json.dumps(quick_levels)
    return json.dumps({
        "cur": quick_url(cur["filename"]), "next": {1: quick_next(db, cur)}})

def quick_result(db):
    if "user" not in session or "file" not in request.files:
        abort(400)
    file = request.files["file"]
    if file.filename == "":
        abort(400)
    cur = json.loads(session["cur"])
    fname = f"sin_{session['user']}_{cur['id']}"
    fpath = os.path.join(upload_location, fname)
    file.save(fpath)
    reply = asr(fpath)
    db.execute(
        "INSERT INTO quick_results "
        "(subject, trial, reply_filename, reply_asr) VALUES (?, ?, ?, ?)",
        (session["user"], cur["id"], fname, reply))
    reply = set(reply.split(" "))
    correct = 0
    for options in cur["answer"].split(","):
        for option in options.split("/"):
            if option in reply:
                correct += 1
    session["cur"] = session["q"]
    return json.dumps({1: quick_next(
        db, json.loads(session["cur"]), correct == 0)})

class QuickBP(DatabaseBP):
    def __init__(self, db, name="quick", url_prefix="/quick"):
        global asr
        Blueprint.__init__(self, name, __name__, url_prefix=url_prefix)
        self._route_db("/start")(quick_start)
        self._route_db("/result", methods=["POST"])(quick_result)
        self._bind_db = db
        from asr import asr

    @property
    def _blueprint_db(self):
        return self._bind_db()
