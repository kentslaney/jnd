import json, sqlite3, unicodedata
from flask import request, session
from utils import relpath, DatabaseBP
from pitch import PitchDB, PitchBP
from quick import QuickDB, QuickBP

# use multiple inheritance to add other DB hooks
class ExperimentDB(PitchDB, QuickDB):
    pass

class APIBlueprint(DatabaseBP):
    def __init__(self,
                 db_path=relpath("experiments.db"),
                 schema_path=relpath("schema.sql"),
                 name="api", url_prefix=None):
        super().__init__(db_path, schema_path, name, url_prefix)
        db = lambda: self._blueprint_db
        self.register_blueprint(PitchBP(db))
        self.register_blueprint(QuickBP(db))
        self._route_db("/username-available")(username_available)
        self._route_db("/set-username")(set_username)

    def _bind_db(self, app):
        super()._bind_db(app)
        self._blueprint_db = ExperimentDB(
            app, *self._db_paths, ["PRAGMA foreign_keys = ON"])
        app.config.update(SESSION_COOKIE_NAME="jnd")

        try:
            with open(relpath("secret_key"), "rb") as f:
                app.secret_key = f.read()
        except FileNotFoundError:
            import os
            with open(relpath("secret_key"), "wb") as f:
                secret = os.urandom(24)
                f.write(secret)
                app.secret_key = secret

username_blocks = ("L", "Nd", "Nl", "Pc", "Pd")
def username_rules(value: str):
    if not 0 < len(value) <= 512:
        return False
    for c in map(unicodedata.category, value):
        if not any(c.startswith(b) for b in username_blocks):
            return False
    return True

def username_available(db):
    checking = request.args.get("v")
    if checking is None or not username_rules(checking):
        return json.dumps(False)

    return json.dumps(not db.queryone(
        "SELECT EXISTS(SELECT 1 FROM users WHERE username=? LIMIT 1)",
        (checking,))[0])

def set_username(db):
    name = request.args.get("v")
    if name is None or not username_rules(name):
        return json.dumps(False)

    try:
        uid = db.execute("INSERT INTO users (username, ip) VALUES (?, ?)",
                         (name, request.remote_addr))
    except sqlite3.IntegrityError:
        return json.dumps(False)

    session.clear()
    session["user"] = uid
    return json.dumps(True)
