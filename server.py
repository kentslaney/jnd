import json, sqlite3, unicodedata
from werkzeug.middleware.proxy_fix import ProxyFix
from flask import Flask, request, session, abort
from utils import relpath
from pitch import PitchDB, pitch_bp

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1)
app.register_blueprint(pitch_bp)

# use multiple inheritance to add other DB hooks
class ExperimentDB(PitchDB):
    pass

db = ExperimentDB(
    app,
    relpath("experiments.db"),
    relpath("schema.sql"),
    ["PRAGMA foreign_keys = ON"])

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

@app.route("/username-available")
def username_available():
    checking = request.args.get("v")
    if checking is None or not username_rules(checking):
        return json.dumps(False)

    return json.dumps(not db.queryone(
        "SELECT EXISTS(SELECT 1 FROM users WHERE username=? LIMIT 1)",
        (checking,))[0])

@app.route("/set-username")
def set_username():
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

#if __name__ == "__main__":
#    app.run(host="unix:///tmp/kent.slaney.org.jnd.sock")
