import sys, os, importlib
from storage import relpath
from flask import Flask

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("qualname")
    parser.add_argument(
            "database", nargs='?', default=relpath("experiments.db"))
    args = parser.parse_args()

    assert "." in args.qualname
    assert os.path.exists(args.database)
    module, attr = args.qualname.rsplit(".", 1)

    sys.path.insert(0, relpath())
    db = getattr(importlib.import_module(module), attr)

    app = Flask(__name__)
    with app.app_context():
        db(app, args.database, None).db_init_hook()
