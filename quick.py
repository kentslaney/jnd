import os, os.path, json, random
from flask import Blueprint, request, session, abort, redirect, Response
from utils import Database, relpath, DatabaseBP
from werkzeug.wrappers import Response
from matplotlib import pyplot

quick_levels = 6
quick_files = relpath("all_spin_index.csv")
upload_location = relpath("uploads")

class QuickDB(Database):
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        os.makedirs(upload_location, exist_ok=True)

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
        # levels 1 indexed
        assert quick_levels <= self.queryone(
            "SELECT MAX(level_number) FROM quick_trials WHERE active=1")[0]

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
        q = db.queryall(
            "SELECT * FROM quick_trials WHERE active=1 AND level_number=?",
            (cur["level_number"] + 1,))
        if len(q) == 0:
            abort(Reponse("out of levels", code=400))
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
        return json.dumps({
            "cur": cur, "next": {1: q}, "name": session["username"],
            "has_results": json.loads(session["left"]) < quick_levels - 1})
    cur = db.queryall(
        "SELECT * FROM quick_trials WHERE active=1 AND level_number=1")
    if len(cur) == 0:
        abort(400)
    cur = quick_trial_dict(random.choice(cur))
    session["cur"], session["left"] = json.dumps(cur), json.dumps(quick_levels)
    return json.dumps({
        "cur": quick_url(cur["filename"]), "next": {1: quick_next(db, cur)},
        "name": session["username"], "has_results": False})

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
    session["cur"] = session["q"]
    return json.dumps({1: quick_next(
        db, json.loads(session["cur"]),
        completion_condition(reply, cur["answer"]))})

# delayed by one level because of preloading
def completion_condition(reply, answer):
    return proportion_correct(reply, answer) == 0

def proportion_correct(reply, answer):
    reply = set(reply.split(" "))
    correct, total = 0, 0
    for options in answer.split(","):
        for option in options.split("/"):
            total += 1
            if option in reply:
                correct += 1
    return correct / max(total, 1)

def quick_plot(db):
    results = db.queryall(
        "SELECT quick_trials.snr, quick_results.reply_asr, "
        "quick_trials.answer FROM quick_results LEFT JOIN quick_trials "
        "ON quick_results.trial=quick_trials.id WHERE quick_results.subject=?",
         (session["user"],))
    if len(results) == 0:
        abort(400)
    results = [(snr, proportion_correct(*score)) for snr, *score in results]
    png_bytes = results_png(*zip(*results))
    return Response(png_bytes, mimetype='image/png')

class QuickBP(DatabaseBP):
    def __init__(self, db, name="quick", url_prefix="/quick"):
        # don't want to import (loads model) if BP isn't constructed
        global asr, results_png
        Blueprint.__init__(self, name, __name__, url_prefix=url_prefix)
        self._route_db("/start")(quick_start)
        self._route_db("/result", methods=["POST"])(quick_result)
        self._route_db("/plot")(quick_plot)
        self._bind_db = db
        from asr import asr, results_png

    @property
    def _blueprint_db(self):
        return self._bind_db()

