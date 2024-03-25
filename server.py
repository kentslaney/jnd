from api import APIBlueprint
from werkzeug.middleware.proxy_fix import ProxyFix
from flask import Flask

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1)
app.register_blueprint(APIBlueprint())

if __name__ == "__main__":
    app.run(host="unix:///tmp/audio.experiments.api.sock")

