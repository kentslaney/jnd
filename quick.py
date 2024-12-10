import os, os.path, json, random, functools, uuid
from flask import (
    Blueprint, request, session, abort, redirect, Response, send_from_directory)
from utils import Database, relpath, DatabaseBP
from plot import scatter_results, logistic_results

quick_levels = 6
quick_files = relpath("all_spin_index.csv")
upload_location = relpath("uploads")
disabled_lists = (3, 4, 5, 7, 9)

class QuickDB(Database):
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        os.makedirs(upload_location, exist_ok=True)

    def db_init_hook(self):
        super().db_init_hook()
        assert os.path.exists(quick_files)
        with open(quick_files, "r") as f:
            experiments = [
                [part.strip() for part in line.split(",", 4)] for line in f]
        con = self.get()
        cur = con.cursor()
        cur.execute(
            "INSERT INTO quick_trials "
            "(trial_number, level_number, snr, filename, answer, active) "
            "VALUES (1, -1, 0, 'invalid', 'invalid', 0)")
        cur.executemany(
            "INSERT INTO quick_trials "
            "(trial_number, level_number, snr, filename, answer, active) "
            "VALUES (?, ?, ?, ?, ?, 1)", experiments)
        # Python formatting alright since disabled_levels isn't user input
        cur.execute(
                "UPDATE quick_trials SET active=0 WHERE trial_number IN "
                f"({','.join(map(str, disabled_lists))})")
        con.commit()
        # levels 1 indexed
        assert quick_levels <= self.queryone(
            "SELECT MAX(level_number) FROM quick_trials WHERE active=1")[0]

    def _username_hook(self):
        res = getattr(super(), "_username_hook", lambda: None)()
        self.execute(
                "INSERT INTO user_info (user, info_key, value) "
                "VALUES (?, 'test-type', ?)",
                (int(session["user"]), request.args.get("t", "unknown")))
        return res

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
    quick_done = [1, 0, 0, 1, "", 1]

    def __init__(self, db, name="quick", url_prefix="/quick"):
        Blueprint.__init__(self, name, __name__, url_prefix=url_prefix)
        self._route_db("/start")(self.quick_start)
        self._route_db("/result", methods=["POST"])(self.quick_result)
        self._route_db("/recognized")(self.quick_recognized)
        self._bind_db = db
        self.result_fields = tuple(zip(*sorted(self.result_fields().items())))

    @property
    def _blueprint_db(self):
        return self._bind_db()

    def quick_async(self, db, rowid, fpath, answer):
        raise NotImplementedError()

    def quick_next(self, db, cur, done=None):
        left = json.loads(session["left"])
        session["left"] = json.dumps(left - 1)
        if left <= 1 or done and done():
            q = self.quick_done
            if left <= 1:
                self.quick_async(*done(True))
        else:
            lists = json.loads(session["lists"])
            level = quick_levels - (left - 2) // lists
            if level == 1:
                q = db.queryall(
                    "SELECT * FROM quick_trials WHERE level_number=1 AND "
                    "active=1 AND trial_number NOT IN ("
                        "SELECT trial_number FROM quick_results "
                        "LEFT JOIN quick_trials "
                        "ON quick_results.trial=quick_trials.id "
                        "WHERE subject=?)",
                    (session["user"],))
                if len(q) == 0:
                    abort(Response("out of levels", code=400))
                q = random.choice(q)
            else:
                # TODO: stick with a single list the whole way through
                # TODO: this may repeat the same list when preloading w/o result
                q = db.queryone(
                    "SELECT * FROM quick_trials WHERE level_number=? AND "
                    "active=1 AND trial_number NOT IN ("
                        "SELECT trial_number FROM quick_results "
                        "LEFT JOIN quick_trials "
                        "ON quick_results.trial=quick_trials.id "
                        "WHERE subject=? AND level_number=?)",
                    (level, session["user"], session["user"], level))
                if q is None: # preloading one, just has to match
                    assert level == 2
                    q = db.queryone(
                        "SELECT * FROM quick_trials WHERE level_number=2 AND "
                        "active=1 AND trial_number=?",
                        (cur["trial_number"],))
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
        try:
            lists = int(json.loads(session["meta"]).get("l", "1"))
        except ValueError:
            abort(400)
        session["lists"] = json.dumps(lists)
        session["left"] = json.dumps(quick_levels * lists)
        return json.dumps({
            "cur": self.quick_url(cur["filename"]), "has_results": False,
            "next": {1: self.quick_next(db, cur)}, "name": session["username"]})

    def quick_parse(self, db, rowid, fpath, answer, dump=False):
        def wrapped(dump=False):
            if dump:
                return (db, rowid, fpath, answer)
            reply = self.asr(fpath, answer)
            db.execute(
                "INSERT INTO quick_asr (ref, data) VALUES (?, ?)",
                (rowid, json.dumps(reply)))
            return self.completion_condition(reply, answer)
        if dump:
            return wrapped()
        return wrapped

    def quick_result(self, db):
        if "user" not in session or "file" not in request.files:
            abort(400)
        file = request.files["file"]
        if file.filename == "":
            abort(400)
        cur = json.loads(session["cur"])
        fname = f"sin_{session['user']}_{cur['id']}_{uuid.uuid4()}"
        fpath = os.path.join(upload_location, fname)
        file.save(fpath)
        rowid = db.execute(
            "INSERT INTO quick_results "
            "(subject, trial, reply_filename) VALUES (?, ?, ?)",
            (session["user"], cur["id"], fname))
        session["cur"] = session["q"]
        return json.dumps({1: self.quick_next(
            db, json.loads(session["cur"]),
            self.quick_parse(db, rowid, fpath, cur["answer"]))})

    # delayed by one level because of preloading
    def completion_condition(self, reply, answer):
        return self.proportion_correct(reply, answer) == 0

    def proportion_correct(self, reply, answer):
        reply = set(reply.split(" "))
        correct, total = 0, 0
        for options in answer.split(","):
            total += 1
            for option in options.split("/"):
                if option in reply:
                    correct += 1
                    break
        return correct / max(total, 1)

    @staticmethod
    def map_answer(f, answer, delimitors=",/"):
        sep = ([len(s) for s in answer.split(d)] for d in delimitors)
        sep = sorted((sum(i[:j + 1]) + j, d) for i, d in zip(
            sep, delimitors) for j in range(len(i)))
        sep = zip([(0, '')] + [(i + 1, d) for i, d in sep[:-1]], (
            i[0] for i in sep[:-1]))
        return "".join(j + f(answer[i:k]) for (i, j), k in sep)

    def quick_plotter(self, db, query="", args=()):
        results = db.queryall(
            "SELECT quick_trials.snr, quick_asr.data, "
            "quick_trials.answer FROM quick_results "
            "LEFT JOIN quick_trials ON quick_results.trial=quick_trials.id "
            "LEFT JOIN quick_asr ON quick_results.id=quick_asr.ref "
            "WHERE quick_asr.data IS NOT NULL"
            f"{query and ' AND ' + query}", args)
        if len(results) == 0:
            abort(400)
        results = [(snr, self.proportion_correct(
            json.loads(reply), answer)) for snr, reply, answer in results]
        return self.flask_png(*zip(*results))

    def quick_recognized(self, db):
        if "user" not in session:
            abort(400)
        return self.quick_recognize(
            db, " WHERE quick_results.subject=?", (session["user"],))

    result_fields = staticmethod(lambda: {
            "time": "users.t",
            "subject": "quick_results.subject",
            "username": "users.username",
            "upload": "quick_results.reply_filename",
            "transcript": "quick_asr.data",
            "prompt": "quick_trials.filename",
            "answer": "quick_trials.answer",
        })

    def quick_recognize(self, db, query="", args=()):
        transcription = db.queryall(
            "SELECT "
                f"{','.join(self.result_fields[1])} "
            "FROM quick_results "
                "LEFT JOIN quick_trials ON quick_results.trial=quick_trials.id "
                "LEFT JOIN users ON subject=users.id "
                "LEFT JOIN quick_asr ON quick_results.id=quick_asr.ref"
            f"{query}", args)
        keys = self.result_fields[0]
        return json.dumps([dict(zip(keys, i)) for i in transcription])

    def asr(self, path):
        raise NotImplementedError()

    def flask_png(self, x, y):
        raise NotImplementedError()

class QuickAnnotatedBP(QuickBP):
    def __init__(self, *a, **kw):
        fields = self.result_fields()
        fields["annotations"] = "quick_annotations.data"
        self.result_fields = lambda: fields
        super().__init__(*a, **kw)
        self._route_db("/reset", methods=["POST"])(self.quick_reset)
        self._route_db("/effort", methods=["POST"])(self.quick_effort)

    def quick_plotter(self, db, query="", args=()):
        results = db.queryall(
            "SELECT quick_trials.snr, quick_annotations.data "
            "FROM quick_results "
            "LEFT JOIN quick_trials ON quick_results.trial=quick_trials.id "
            "LEFT JOIN quick_annotations ON "
            "quick_results.id=quick_annotations.ref "
            "WHERE quick_annotations.data IS NOT NULL "
            "AND quick_annotations.data != ''"
            f"{query and ' AND ' + query}", args)
        if len(results) == 0:
            abort(400)
        results = [(snr, json.loads(data)) for snr, data in results]
        results = [(snr, sum(data) / len(data)) for snr, data in results]
        return self.flask_png(*zip(*results))

    def quick_parse(self, db, rowid, fpath, answer, dump=False, data=None):
        def wrapped(dump=False):
            nonlocal data
            data = data or request.args["annotations"]
            if dump:
                return (db, rowid, fpath, answer, True, data)
            db.execute(
                "INSERT INTO quick_annotations (ref, data) VALUES (?, ?)",
                (rowid, data))
            return False # audiologist can end test when they want to
        if dump:
            return wrapped()
        return wrapped

    def quick_start(self, db):
        res = json.loads(super().quick_start(db))
        res["answer"] = [
                json.loads(session[i])["answer"] for i in ("cur", "q")]
        return json.dumps(res)

    def quick_result(self, db):
        if "annotations" not in request.args:
            abort(400)
        res = json.loads(super().quick_result(db))
        res["answer"] = json.loads(session["q"])["answer"]
        return json.dumps(res)

    def quick_recognize(self, db, query="", args=()):
        res = super().quick_recognize(db, (
            " LEFT JOIN quick_annotations ON "
                "quick_results.id = quick_annotations.ref"
            f"{query}"), args)
        res = json.loads(res)
        res = [{**i, "annotations": json.loads(i["annotations"])} for i in res]
        return json.dumps(res)

    def quick_async(self, *args):
        return self.quick_parse(*args)

    def quick_reset(self, db):
        session.pop("cur", None)
        return ""

    def quick_effort(self, db):
        if "user" not in session or "v" not in request.args:
            abort(400)
        try:
            effort = int(effort).get("v")
        except ValueError:
            abort(400)
        db.execute(
            "INSERT INTO user_info (user, info_key, value) "
            "VALUES (?, 'effort', ?)",
            (int(session["user"]), effort))
        return ""

class QuickScatterBP:
    @staticmethod
    @bytes_png
    def flask_png(x, y):
        return scatter_results(x, y)

class QuickLogisticBP:
    @staticmethod
    @bytes_png
    def flask_png(x, y):
        return logistic_results(x, y) if len(x) > 1 else scatter_results(x, y)

class QuickNormalizedBP(QuickBP):
    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        from asr import whisper_normalizer
        self.normalizer = whisper_normalizer

    def proportion_correct(self, reply, answer):
        return super().proportion_correct(
            self.normalizer(reply["text"]),
            self.map_answer(self.normalizer, answer))

class QuickWhisperBP(QuickNormalizedBP):
    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        from asr import WhisperASR
        self.whisper_asr = WhisperASR()

    def asr(self, path, answer):
        return self.whisper_asr(path)

class QuickPromptedWhisperBP(QuickNormalizedBP):
    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        from asr import PromptedWhisperASR
        self.prompted_whisper_asr = PromptedWhisperASR()

    def asr(self, path, answer):
        return self.prompted_whisper_asr(
            path, answer.replace(",", " ").replace("/", " "))

# class QuickResultsBP(QuickWhisperBP):
# class QuickResultsBP(QuickPromptedWhisperBP):
class QuickResultsBP(QuickAnnotatedBP):
    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self._route_db("/plot")(self.quick_plot)
        self._route_db("/upload/<fname>")(self.upload)

    def quick_recognized(self, db):
        if user == "all":
            return self.quick_recognize(db)
        if "user" not in session:
            abort(400)
        user = request.args.get("user", session["user"])
        return self.quick_recognize(
            db, " WHERE quick_results.subject=?", (user,))

    def quick_plot(self, db):
        user = request.args.get("user", session["user"])
        if user == "all":
            return self.quick_plotter(db)
        return self.quick_plotter(db, "quick_results.subject=?", (user,))

    def upload(self, db, fname):
        return send_from_directory(upload_location, fname)

class QuickWhisperDebugBP(QuickResultsBP):
    def quick_next(self, db, cur, done=False):
        print(f'answer is "{cur["answer"]}"')
        return super().quick_next(db, cur, done)

    def proportion_correct(self, reply, answer):
        res = super().proportion_correct(reply, answer)
        print(f'heard "{reply}": {res}')
        return res

    def quick_async(self, db, rowid, fpath, answer):
        return self.quick_parse(db, rowid, fpath, answer, True)

# class QuickLogisticWhisperBP(QuickLogisticBP, QuickWhisperDebugBP):
# class QuickLogisticWhisperBP(QuickLogisticBP, QuickWhisperBP):
class QuickOutputBP(QuickLogisticBP, QuickResultsBP):
    pass

