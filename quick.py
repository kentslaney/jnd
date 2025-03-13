import os, os.path, json, random, functools, uuid
from flask import (
    Blueprint, request, session, abort, redirect, Response, send_from_directory)
from utils import Database, relpath, DatabaseBP, mangle
from plot import scatter_results, logistic_results

# TODO: remove level count and count upwards now that it can be tracked per list
quick_levels = 6
quick_files = relpath("all_spin_index.csv")
upload_location = relpath("uploads")

# prefixed with quick to avoid namespace collisions with other APIs
class QuickDB(Database):
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        os.makedirs(upload_location, exist_ok=True)

    def db_init_hook(self):
        super().db_init_hook()
        assert os.path.exists(quick_files)
        with open(quick_files, "r") as f:
            experiments = [
                [part.strip() for part in line.split(",", 6)] for line in f]
        con = self.get()
        cur = con.cursor()
        cur.execute(
            "INSERT INTO quick_trials "
            "(active, lang, trial_number, level_number, snr, filename, answer) "
            "VALUES (0, '--', 1, -1, 0, 'invalid', 'invalid')")
        cur.executemany(
            "INSERT INTO quick_trials "
            "(active, lang, trial_number, level_number, snr, filename, answer) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)", experiments)
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

class AudioBP(DatabaseBP):
    audio_keys = (
        "id", "snr", "lang", "level_number", "trial_number", "filename",
        "answer")
    audio_trial_dict = staticmethod(lambda v: dict(zip(AudioBP.audio_keys, v)))
    audio_url = staticmethod(lambda v: v and "/jnd/quick/" + v)
    audio_done = [1, 0, "--", 0, 1, "", 1]

    def __init__(self, db, name="quick", url_prefix="/quick"):
        Blueprint.__init__(self, name, __name__, url_prefix=url_prefix)
        self._route_db("/lists")(self.quick_lists)
        self._route_db("/start")(self.quick_start)
        self._route_db("/result", methods=["POST"])(self.quick_result)
        self._route_db("/recognized")(self.quick_recognized)
        self._bind_db = db
        self.result_fields = tuple(zip(*sorted(self.result_fields().items())))

    @property
    def _blueprint_db(self):
        return self._bind_db()

    @mangle
    def async_(self, db, rowid, fpath, answer):
        raise NotImplementedError()

    @mangle
    def lists(self, db):
        langs = [i[0] for i in db.queryall(
                "SELECT DISTINCT lang FROM quick_trials WHERE level_number=1")]
        lists = [i[0] for i in db.queryall(
                "SELECT lang || '-' || trial_number FROM quick_trials WHERE "
                "level_number=1")]
        return json.dumps(langs + lists)

    @mangle
    def next(self, db, cur, done=None):
        left = json.loads(session["left"])
        session["left"] = json.dumps(left - 1)
        if left <= 1 or done and done():
            q = self.audio_done
            if left <= 1:
                self.async_(*done(True))
        else:
            level = quick_levels - left + 2
            q = db.queryone(
                    "SELECT * FROM quick_trials WHERE "
                    "level_number=? AND trial_number=? AND lang=?",
                    (level, cur['trial_number'], cur['lang']))
            if q is None:
                assert left == 2
                q = self.audio_done
        q = self.audio_trial_dict(q)
        session["q"] = json.dumps(q)
        return self.audio_url(q["filename"])

    @mangle
    def start(self, db):
        if "user" not in session:
            abort(400)
        elif "cur" in session:
            cur, q = map(lambda x: self.audio_url(json.loads(x)["filename"]), (
                session["cur"], session["q"]))
            return json.dumps({
                "cur": cur, "next": {1: q}, "name": session["username"],
                "has_results": json.loads(session["left"]) < quick_levels - 1})
        lang, trial_number = json.loads(session["requested"])
        if trial_number is not None:
            cur = [db.queryone(
                    "SELECT * from quick_trials WHERE "
                    "level_number=1 AND lang=? AND trial_number=?",
                    (lang, trial_number))]
        else:
            cur = db.queryall(
                "SELECT * FROM quick_trials WHERE "
                "lang=? AND active=1 AND level_number=1 AND "
                "trial_number NOT IN ("
                    "SELECT trial_number FROM quick_results "
                    "LEFT JOIN quick_trials "
                    "ON quick_results.trial=quick_trials.id "
                    "WHERE subject=? AND level_number=1)",
                (lang, session["user"]))
        if len(cur) == 0 or None in cur:
            abort(400)
        cur = self.audio_trial_dict(random.choice(cur))
        session["cur"] = json.dumps(cur)
        session["left"] = json.dumps(quick_levels)
        return json.dumps({
            "cur": self.audio_url(cur["filename"]), "has_results": False,
            "next": {1: self.next(db, cur)}, "name": session["username"]})

    @mangle
    def parse(self, db, rowid, fpath, answer, dump=False):
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

    @mangle
    def result(self, db):
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
        return json.dumps({1: self.next(
            db, json.loads(session["cur"]),
            self.parse(db, rowid, fpath, cur["answer"]))})

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

    @mangle
    def plotter(self, db, query="", args=()):
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

    @mangle
    def recognized(self, db):
        if "user" not in session:
            abort(400)
        return self.recognize(
            db, " WHERE quick_results.subject=?", (session["user"],))

    result_fields = staticmethod(lambda: {
            "time": "users.t",
            "subject": "quick_results.subject",
            "username": "users.username",
            "upload": "quick_results.reply_filename",
            "transcript": "quick_asr.data",
            "prompt": "quick_trials.filename",
            "answer": "quick_trials.answer",
            "trial_number": "quick_trials.trial_number",
        })

    @mangle
    def recognize(self, db, query="", args=()):
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

class AudioAnnotatedBP(AudioBP):
    def __init__(self, *a, **kw):
        fields = self.result_fields()
        fields["annotations"] = "quick_annotations.data"
        self.result_fields = lambda: fields
        super().__init__(*a, **kw)
        self._route_db("/reset", methods=["POST"])(self.quick_reset)
        self._route_db("/effort", methods=["POST"])(self.quick_effort)

    @mangle
    def plotter(self, db, query="", args=()):
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

    @mangle
    def parse(self, db, rowid, fpath, answer, dump=False, data=None):
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

    @mangle
    def start(self, db):
        res = json.loads(super().start(db))
        res["answer"] = [
                json.loads(session[i])["answer"] for i in ("cur", "q")]
        return json.dumps(res)

    @mangle
    def result(self, db):
        if "annotations" not in request.args:
            abort(400)
        res = json.loads(super().result(db))
        res["answer"] = json.loads(session["q"])["answer"]
        return json.dumps(res)

    @mangle
    def recognize(self, db, query="", args=()):
        res = super().recognize(db, (
            " LEFT JOIN quick_annotations ON "
                "quick_results.id = quick_annotations.ref"
            f"{query}"), args)
        res = json.loads(res)
        res = [{**i, "annotations": json.loads(i["annotations"])} for i in res]
        return json.dumps(res)

    @mangle
    def async_(self, *args):
        return self.parse(*args)

    @mangle
    def reset(self, db):
        session.pop("cur", None)
        session["requested"] = json.dumps([
            json.loads(session.pop("requested", None))[0], None])
        return ""

    @mangle
    def effort(self, db):
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

class AudioScatterBP:
    @staticmethod
    @bytes_png
    def flask_png(x, y):
        return scatter_results(x, y)

class AudioLogisticBP:
    @staticmethod
    @bytes_png
    def flask_png(x, y):
        return logistic_results(x, y) if len(x) > 1 else scatter_results(x, y)

class AudioNormalizedBP(AudioBP):
    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        from asr import whisper_normalizer
        self.normalizer = whisper_normalizer

    def proportion_correct(self, reply, answer):
        return super().proportion_correct(
            self.normalizer(reply["text"]),
            self.map_answer(self.normalizer, answer))

class AudioWhisperBP(AudioNormalizedBP):
    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        from asr import WhisperASR
        self.whisper_asr = WhisperASR()

    def asr(self, path, answer):
        return self.whisper_asr(path)

class AudioPromptedWhisperBP(AudioNormalizedBP):
    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        from asr import PromptedWhisperASR
        self.prompted_whisper_asr = PromptedWhisperASR()

    def asr(self, path, answer):
        return self.prompted_whisper_asr(
            path, answer.replace(",", " ").replace("/", " "))

# class AudioResultsBP(AudioWhisperBP):
# class AudioResultsBP(AudioPromptedWhisperBP):
class AudioResultsBP(AudioAnnotatedBP):
    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self._route_db("/plot")(self.quick_plot)
        self._route_db("/upload/<fname>")(self.upload)

    @mangle
    def recognized(self, db):
        if request.args.get("user", None) == "all":
            return self.recognize(db)
        if "user" not in session:
            abort(400)
        user = request.args.get("user", session["user"])
        return self.recognize(
            db, " WHERE quick_results.subject=?", (user,))

    @mangle
    def plot(self, db):
        user = request.args.get("user", session["user"])
        if user == "all":
            return self.plotter(db)
        return self.plotter(db, "quick_results.subject=?", (user,))

    def upload(self, db, fname):
        return send_from_directory(upload_location, fname)

class AudioWhisperDebugBP(AudioResultsBP):
    @mangle
    def next(self, db, cur, done=False):
        print(f'answer is "{cur["answer"]}"')
        return super().next(db, cur, done)

    def proportion_correct(self, reply, answer):
        res = super().proportion_correct(reply, answer)
        print(f'heard "{reply}": {res}')
        return res

    @mangle
    def async_(self, db, rowid, fpath, answer):
        return self.parse(db, rowid, fpath, answer, True)

# class AudioLogisticWhisperBP(AudioLogisticBP, AudioWhisperDebugBP):
# class AudioLogisticWhisperBP(AudioLogisticBP, AudioWhisperBP):
class AudioOutputBP(AudioLogisticBP, AudioResultsBP):
    pass

@mangle("quick")
class QuickOutputBP(AudioOutputBP):
    pass
