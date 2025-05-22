import sys, os, importlib, json, subprocess
from storage import relpath
from flask import Flask

def main(qualname, database, rewrite):
    assert "." in qualname
    assert os.path.exists(database)
    module, attr = qualname.rsplit(".", 1)

    sys.path.insert(0, relpath())
    db = getattr(importlib.import_module(module), attr)

    app = Flask(__name__)
    db = db(app, database, None)
    with app.app_context():
        if rewrite:
            db.upserting = True
        db.db_init_hook()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("qualname", nargs='?')
    parser.add_argument("--database", default=relpath("experiments.db"))
    parser.add_argument("--rewrite", action="store_true")
    args = parser.parse_args()
    if args.qualname is not None:
        main(args.qualname, args.database, args.rewrite)
        exit(0)
    from audio import AudioDB
    with open(relpath("migrations.json")) as fp:
        migrations = json.load(fp)
    commits = AudioDB.commits()
    app = Flask(__name__)
    db = AudioDB(app, args.database, None)
    with app.app_context():
        commit = db.queryone(
                "SELECT count(*) FROM sqlite_master WHERE type='table' AND "
                "name='version'")[0]
        commit = db.queryone("SELECT hash FROM version")[0] if commit else \
                commits[-1]
        commits = commits[:commits.index(commit) + 1]
        migrations = [i for i in migrations if any(
                j.startswith(i[0]) for j in commits)]
        for base, *cmds in migrations:
            for cmd, *args in cmds:
                if cmd == "table":
                    pos, full = next(
                            (n, i) for n, i in enumerate(commits)
                            if i.startswith(base))
                    update = None if pos == 0 else commits[pos - 1]
                    update = f"git show {update}:schema.sql" if update else \
                            "cat schema.sql"
                    for arg in args:
                        create = subprocess.check_output(
                                f"{update} | "
                                "grep -zoP 'CREATE( TEMP(ORARY|)|) TABLE "
                                f"(IF NOT EXISTS |){arg}[^;]*'",
                                shell=True, cwd=relpath())
                        db.execute(create.rstrip(b'\x00').decode())
                elif cmd == "cmd":
                    db.execute("".join(args))
                elif cmd == "update":
                    for arg in args:
                        main(arg, args.database, args.rewrite)
        db.db_init_hook()
