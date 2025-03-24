from flask import Flask, Blueprint, redirect
from api import APIBlueprint

app_prefix = "/"

bp = Blueprint("main", __name__, url_prefix=app_prefix)
bp.register_blueprint(APIBlueprint(url_prefix="/api"))

@bp.route("/")
def index():
    return app.send_static_file("index.html")

app = Flask(__name__, static_url_path=app_prefix)
app.register_blueprint(bp)

@app.route("/")
def root():
    return redirect(app_prefix)

if __name__ == "__main__":
    app.run(port=8080, debug=True)

