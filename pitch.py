import os.path, json, random
from flask import Blueprint, request, session, abort
from store import Database, relpath, DatabaseBP

pitch_levels = 8
pitch_files = relpath("metadata/pitch_jnd_files.csv")

class PitchDB(Database):
    def db_init_hook(self):
        super().db_init_hook()
        assert os.path.exists(pitch_files), "please run generate_pitches.py"
        with open(pitch_files, "r") as f:
            experiments = [
                [part.strip() for part in line.split(",")] for line in f]
        con = self.get()
        cur = con.cursor()
        cur.executemany(
            ("INSERT INTO pitch_trials "
             "(f0, level_number, trial_number, filename, answer, active) "
             "values (?, ?, ?, ?, ?, 1)"), experiments)
        con.commit()
        # levels 0 indexed
        assert pitch_levels - 1 <= self.queryone(
            "SELECT MAX(level_number) FROM pitch_trials WHERE active=1")[0]

pitch_keys = ("id", "f0", "level_number", "trial_number", "filename", "answer")
pitch_trial_dict = lambda v: dict(zip(pitch_keys, v))
pitch_url = lambda v: v and "pitches/" + v
pitch_done = [0, 0, 0, 1, "", 1]

def pitch_next(db, cur, left, sign=None):
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

def pitch_start(db):
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
    return json.dumps({
        "cur": pitch_url(cur["filename"]),
        "next": pitch_next(db, cur, json.loads(session["left"]))})

def pitch_result(db):
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
    next_urls = pitch_next(db, json.loads(update), left, sign)
    session["cur"] = update
    return json.dumps(next_urls)

class PitchBP(DatabaseBP):
    def __init__(self, db, name="pitch", url_prefix="/pitch"):
        Blueprint.__init__(self, name, __name__, url_prefix=url_prefix)
        self._route_db("/start")(pitch_start)
        self._route_db("/result")(pitch_result)
        self._bind_db = db

    @property
    def _blueprint_db(self):
        return self._bind_db()

    def audio_lists(self, db):
        return "[]"
