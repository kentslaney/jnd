def relpath(*args):
    return os.path.join(os.path.dirname(os.path.realpath(__file__)), *args)

# http://flask.pocoo.org/docs/0.11/patterns/sqlite3/
import sqlite3, os.path
from flask import g

class Database:
    # creates database if it doesn't exist; set up by schema
    def __init__(self, app, database, schema, init=[]):
        self.database = os.path.abspath(database)
        self.init = init
        if not os.path.exists(database):
            with app.app_context():
                db = self.get()
                with app.open_resource(schema, mode='r') as f:
                    db.cursor().executescript(f.read())
                db.commit()
                self.db_init_hook()

        self.app = app
        app.teardown_appcontext(lambda e: self.close())

    # returns a database connection
    def get(self):
        db = getattr(g, "_database", None)
        if db is None:
            db = g._database = sqlite3.connect(self.database)
            for i in self.init:
                self.execute(i)
        return db

    def queryall(self, query, args=()):
        cur = self.get().execute(query, args)
        rv = cur.fetchall()
        cur.close()
        return rv

    def queryone(self, query, args=()):
        cur = self.get().execute(query, args)
        rv = cur.fetchone()
        cur.close()
        return rv

    def execute(self, query, args=()):
        con = self.get()
        cur = con.cursor()
        cur.execute(query, args)
        con.commit()
        res = cur.lastrowid
        cur.close()
        return res or None

    def close(self):
        db = getattr(g, '_database', None)
        if db is not None:
             db.close()

    def db_init_hook(self):
        pass

from flask import Blueprint
import functools

# TODO?: redo? document?
class DatabaseBP(Blueprint):
    def __init__(self, db_path, schema_path, name, url_prefix=None):
        super().__init__(name, __name__, url_prefix=url_prefix)
        self._db_paths = (db_path, schema_path)
        self.record(lambda setup: self._bind_db(setup.app))

    def _route_db(self, *a, **kw):
        def wrapper(f):
            @functools.wraps(f)
            def wrapped(*ra, **kra):
                return f(self._blueprint_db, *ra, **kra)
            return self.route(*a, **kw)(wrapped)
        return wrapper

    def _bind_db(self, app):
        self._blueprint_db = None

def mangle(f):
    f.mangle = True
    return f

def mangles(cls):
    for i, j in zip(cls.__mro__[:-1], cls.__mro__[1:]):
        for k in dir(i):
            v = getattr(i, k)
            if v == getattr(j, k, object()) or not hasattr(v, "mangle"):
                continue
            def closure(f):
                prefix = lambda cls: cls.__name__.lower() + "_"
                mangled = prefix(cls) + f.__name__
                def wrapper(self, *a, **kw):
                    stack = getattr(self, "mangler", None)
                    self.mangler = cls
                    res = f(self, *a, **kw)
                    if stack is None:
                        del self.mangler
                    else:
                        self.mangler = stack
                    return res
                wrapper.__name__ = mangled
                setattr(i, mangled, wrapper)

                def router(self, *a, **kw):
                    if hasattr(self, "mangler"):
                        return getattr(self, prefix(self.mangler) + f.__name__)(
                                *a, **kw)
                    return f(self, *a, **kw)
                setattr(cls, k, router)
            closure(v)
    return cls

'''
class Parent:
    @mangle
    def a(self):
        print(0, self.mangler.__name__, end=" ")

    @mangle
    def b(self):
        print(3, end=" ")
        self.a()

class Intermediary(Parent):
    @mangle
    def a(self):
        print(1, end=" ")
        super().a()

@mangles
class Child0(Parent):
    pass

@mangles
class Child1(Intermediary):
    def child1_a(self):
        print(2, end=" ")
        super().child1_a()

class Mixture(Child0, Child1):
    pass

obj = Mixture()

print('child0_a')
obj.child0_a() # 0 Child0
print('\nchild0_b')
obj.child0_b() # 3 0 Child0
print('\nchild1_a')
obj.child1_a() # 2 1 0 Child1
print('\nchild1_b')
obj.child1_b() # 3 2 1 0 Child1
print()
'''
