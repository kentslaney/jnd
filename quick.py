import os, os.path, json, random, functools
from flask import Blueprint, request, session, abort, redirect, Response
from utils import Database, relpath, DatabaseBP
from plot import scatter_png, logistic_png

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

def saved_png(path):
    def decorator(f):
        def load_path(*a, **kw):
            f(*a, **kw)
            with open(path, 'rb') as fp:
                return fp.read()
        return functools.wraps(f)(bytes_png(load_path))
    return decorator

def bytes_png(f):
    @functools.wraps(f)
    def flask_response(*a, **kw):
        return Response(f(*a, **kw), mimetype='image/png')
    return flask_response

class QuickBP(DatabaseBP):
    quick_keys = (
        "id", "snr", "level_number", "trial_number", "filename", "answer")
    quick_trial_dict = staticmethod(lambda v: dict(zip(QuickBP.quick_keys, v)))
    quick_url = staticmethod(lambda v: v and "/jnd/quick/" + v)
    quick_done = [0, 0, 0, 1, "", 1]

    def __init__(self, db, name="quick", url_prefix="/quick"):
        Blueprint.__init__(self, name, __name__, url_prefix=url_prefix)
        self._route_db("/start")(self.quick_start)
        self._route_db("/result", methods=["POST"])(self.quick_result)
        self._route_db("/plot")(self.quick_plot)
        self._bind_db = db

    @property
    def _blueprint_db(self):
        return self._bind_db()

    def quick_next(self, db, cur, done = False):
        left = json.loads(session["left"])
        session["left"] = json.dumps(left - 1)
        if left == 1 or done:
            q = self.quick_done
        else:
            q = db.queryall(
                "SELECT * FROM quick_trials WHERE active=1 AND level_number=?",
                (cur["level_number"] + 1,))
            if len(q) == 0:
                abort(Response("out of levels", code=400))
            q = random.choice(q)
        q = self.quick_trial_dict(q)
        session["q"] = json.dumps(q)
        return self.quick_url(q["filename"])

    def quick_start(self, db):
        if "user" not in session:
            abort(400)
        elif "cur" in session:
            cur, q = map(lambda x: self.quick_url(json.loads(x)["filename"]), (
                session["cur"], session["q"]))
            return json.dumps({
                "cur": cur, "next": {1: q}, "name": session["username"],
                "has_results": json.loads(session["left"]) < quick_levels - 1})
        cur = db.queryall(
            "SELECT * FROM quick_trials WHERE active=1 AND level_number=1")
        if len(cur) == 0:
            abort(400)
        cur = self.quick_trial_dict(random.choice(cur))
        session["cur"] = json.dumps(cur)
        session["left"] = json.dumps(quick_levels)
        return json.dumps({
            "cur": self.quick_url(cur["filename"]), "has_results": False,
            "next": {1: self.quick_next(db, cur)}, "name": session["username"]})

    def quick_result(self, db):
        if "user" not in session or "file" not in request.files:
            abort(400)
        file = request.files["file"]
        if file.filename == "":
            abort(400)
        cur = json.loads(session["cur"])
        fname = f"sin_{session['user']}_{cur['id']}"
        fpath = os.path.join(upload_location, fname)
        file.save(fpath)
        reply = self.asr(fpath)
        db.execute(
            "INSERT INTO quick_results "
            "(subject, trial, reply_filename, reply_asr) VALUES (?, ?, ?, ?)",
            (session["user"], cur["id"], fname, reply))
        session["cur"] = session["q"]
        return json.dumps({1: self.quick_next(
            db, json.loads(session["cur"]),
            self.completion_condition(reply, cur["answer"]))})

    # delayed by one level because of preloading
    def completion_condition(self, reply, answer):
        return self.proportion_correct(reply, answer) == 0

    def proportion_correct(self, reply, answer):
        reply = set(reply.split(" "))
        correct, total = 0, 0
        for options in answer.split(","):
            for option in options.split("/"):
                total += 1
                if option in reply:
                    correct += 1
        return correct / max(total, 1)

    def quick_plot(self, db):
        results = db.queryall(
            "SELECT quick_trials.snr, quick_results.reply_asr, "
            "quick_trials.answer FROM quick_results LEFT JOIN quick_trials "
            "ON quick_results.trial=quick_trials.id "
            "WHERE quick_results.subject=?", (session["user"],))
        if len(results) == 0:
            abort(400)
        results = [(snr, self.proportion_correct(
            *score)) for snr, *score in results]
        return self.flask_png(*zip(*results))

    @staticmethod
    def asr(path):
        raise NotImplementedError()

    @staticmethod
    def flask_png(x, y):
        raise NotImplementedError()

class QuickScatterBP:
    @staticmethod
    @bytes_png
    def flask_png(x, y):
        return scatter_png(x, y)

class QuickLogisticBP:
    @staticmethod
    @bytes_png
    def flask_png(x, y):
        return logistic_png(x, y)

class QuickWhisperBP(QuickBP):
    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        # don't want to import (loads model) if BP isn't constructed
        from asr import asr
        self.asr = asr

class QuickLogisticWhisperBP(QuickLogisticBP, QuickWhisperBP):
    pass

