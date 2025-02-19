from api import APIBlueprint
from werkzeug.middleware.proxy_fix import ProxyFix
from flask import Flask
from flask_modular_login import login_required, AccessNamespace

group = AccessNamespace("audio", "google", "100312806121431583241")

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1)
app.register_blueprint(login_required(APIBlueprint(), group=group))

if __name__ == "__main__":
    app.run(host="unix:///tmp/audio.experiments.api.sock")

