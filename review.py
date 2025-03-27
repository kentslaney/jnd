import random, json
from storage import DatabaseBP
from flask import Blueprint, session, request, send_from_directory
from audio import upload_location

upload_url = lambda x: x and f"/api/review/upload/{x}"

def reviewable(db, query="1", args=()):
    return db.queryall(
            "SELECT audio_results.id, reply_filename, answer FROM audio_results"
            " LEFT JOIN audio_trials ON audio_results.trial=audio_trials.id "
            "WHERE audio_results.id NOT IN ("
            f"SELECT ref FROM review_annotations WHERE labeler=?) AND {query}",
            (session["user"],) + tuple(args))

def review_start(db):
    if "user" not in session:
        abort(400)
    elif "cur" in session:
        cur, q = map(json.loads, [session["cur"], session["q"]])
        return json.dumps({
            "cur": upload_url(cur[1]),
            "next": {1: upload_url(q[1])},
            "answer": [cur[2], q[2]],
            "name": session["username"]})
    q = reviewable(db)
    if len(q) > 1:
        q = random.choices(q, k=2)
    else:
        q += [[0, "", ""]] * (2 - len(q))
    session["cur"], session["q"] = map(json.dumps, q)
    return json.dumps({
        "cur": upload_url(q[0][1]),
        "next": {1: upload_url(q[1][1])},
        "answer": [q[0][2], q[1][2]],
        "name": session["username"]})

def review_result(db):
    if "user" not in session or "annotations" not in request.args:
        abort(400)
    db.execute(
            "INSERT INTO review_annotations (ref, data, labeler) VALUES "
            "(?, ?, ?)", (
                json.loads(session["cur"])[0], request.args["annotations"],
                session["user"]))
    cur = json.loads(session["q"])
    q = reviewable(db, "audio_results.id!=?", (cur[0],))
    if not q:
        q += [[0, "", ""]]
    q = random.choice(q)
    session["cur"], session["q"] = session["q"], json.dumps(q)
    return json.dumps({1: upload_url(q[1]), "answer": q[2]})

class ReviewBP(DatabaseBP):
    def __init__(self, db, name="review", url_prefix="/review"):
        Blueprint.__init__(self, name, __name__, url_prefix=url_prefix)
        self._route_db("/start")(review_start)
        self._route_db("/result", methods=["POST"])(review_result)
        self._route_db("/upload/<fname>")(self.upload)
        self._bind_db = db

    @property
    def _blueprint_db(self):
        return self._bind_db()

    def audio_lists(self, db):
        return "[]"

    def upload(self, db, fname):
        return send_from_directory(upload_location, fname)

