import os.path, json, random
from flask import Blueprint, request, session, abort
from utils import Database, HeadlessDB, relpath

pitch_bp = Blueprint("pitch", __name__, url_prefix="/pitch")
db = HeadlessDB(relpath("experiments.db"), ["PRAGMA foreign_keys = ON"])

pitch_levels = 8
pitch_files = relpath("pitch_jnd_files.tsv")

class PitchDB(Database):
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        with self.app.app_context():
            assert pitch_levels <= db.queryone(
                "SELECT MAX(level_number) FROM pitch_trials WHERE active=1")[0]

    def db_init_hook(self):
        super().db_init_hook()
        assert os.path.exists(pitch_files)
        with open(pitch_files, "r") as f:
            experiments = [line.strip().split("\t") for line in f]
        con = self.get()
        cur = con.cursor()
        cur.executemany(
            ("INSERT INTO pitch_trials "
             "(f0, level_number, trial_number, filename, answer, active) "
             "values (?, ?, ?, ?, ?, 1)"), experiments)
        con.commit()
        # cur.execute(
        #     "INSERT INTO pitch_trials "
        #     "(f0, level_number, trial_number, filename, answer, active) "
        #     "SELECT 0, MAX(level_number) + 1, 0, 'cap.wav', 1, 1 "
        #     "FROM pitch_trials")
        # con.commit()
        with open(relpath("static", "pitches", "cap.wav"), "ab"):
            pass

pitch_keys = ("id", "f0", "level_number", "trial_number", "filename", "answer")
pitch_trial_dict = lambda v: dict(zip(pitch_keys, v))
pitch_url = lambda v: v and "/jnd/pitches/" + v
pitch_done = [0, 0, 0, 1, "", 1]

def pitch_next(cur, left, sign=None):
    if cur["trial_number"] == 0:
        left -= 1
        session["left"] = json.dumps(left)
        right = db.queryone(("SELECT * FROM pitch_trials WHERE active=1 AND "
                             "trial_number=1 AND level_number=? AND f0=?"),
                            (cur["level_number"], cur["f0"]))
        if right is None:
            abort(400)
        if left == 0:
            wrong = pitch_trial_dict(pitch_done)
        else:
            wrong = db.queryall(("SELECT * FROM pitch_trials WHERE active=1 "
                                 "AND trial_number=0 AND level_number=?"),
                                (max(cur["level_number"] - 1, 0),))
            wrong = pitch_trial_dict(random.choice(wrong))
    else:
        if left == 0:
            right, wrong = pitch_done, pitch_trial_dict(pitch_done)
        else:
            right = db.queryall(("SELECT * FROM pitch_trials WHERE active=1 "
                                "AND trial_number=0 AND level_number=?"),
                                (cur["level_number"] + 1,))
            if len(right) == 0:
                abort(400)
            right = random.choice(right)
            wrong = json.loads(session["neg" if sign == 1 else "pos"])
    right = pitch_trial_dict(right)

    pos, neg = (right, wrong) if cur["answer"] == 1 else (wrong, right)
    session["pos"], session["neg"] = json.dumps(pos), json.dumps(neg)
    return {-1: pitch_url(neg["filename"]), 1: pitch_url(pos["filename"])}

@pitch_bp.route("/start")
def pitch_start():
    if "user" not in session:
        abort(400)
    elif "cur" in session:
        cur, pos, neg = map(json.loads, (
            session["cur"], session["pos"], session["neg"]))
        return json.dumps({"cur": pitch_url(cur["filename"]), "next": {
            -1: pitch_url(neg["filename"]), 1: pitch_url(pos["filename"])}})
    cur = db.queryall(("SELECT * FROM pitch_trials WHERE active=1 AND "
                       "trial_number=0 AND level_number=0"))
    cur = pitch_trial_dict(random.choice(cur))
    session["cur"], session["left"] = json.dumps(cur), json.dumps(pitch_levels)
    return json.dumps({"cur": pitch_url(cur["filename"]),
                       "next": pitch_next(cur, json.loads(session["left"]))})

@pitch_bp.route("/result")
def pitch_result():
    sign = request.args.get("sign", None)
    if sign not in ("-1", "1") or "user" not in session:
        abort(400)
    sign = int(sign)

    cur, left = json.loads(session["cur"]), json.loads(session["left"])
    if cur["id"] == 0:
        # user submitted result for a finished state cookie
        # sqlite has its primary keys 1 indexed so there's no collisions
        abort(400)

    db.execute(("INSERT INTO pitch_results "
                "(subject, trial, guess, levels_left) VALUES (?, ?, ?, ?)"),
               (session["user"], cur["id"], sign, left))

    update = session["pos" if sign == 1 else "neg"]
    next_urls = pitch_next(json.loads(update), left, sign)
    session["cur"] = update
    return json.dumps(next_urls)
