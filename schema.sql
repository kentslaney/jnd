CREATE TABLE users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  username TEXT NOT NULL UNIQUE,
  ip TEXT /* probably superfluous spam mitigation */
);
CREATE TABLE pitch_trials (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  f0 INTEGER, /* base frequency */
  level_number INTEGER, /* zero indexed */
  trial_number INTEGER, /* in the current level, which trial number */
  filename TEXT, /* basename, not path */
  answer INTEGER, /* 1 for pitch goes up otherwise -1 */
  active BOOLEAN NOT NULL CHECK(active IN(0,1)) /* version control */
);
CREATE TABLE pitch_results (
  subject INTEGER,
  trial INTEGER,
  guess INTEGER,
  levels_left INTEGER, /* in case of doubled requests */
  FOREIGN KEY(subject) REFERENCES users(id),
  FOREIGN KEY(trial) REFERENCES pitch_trials(id)
);
CREATE TABLE quick_trials (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  snr INTEGER,
  level_number INTEGER, /* one indexed */
  trial_number INTEGER, /* in the current level, which trial number */
  filename TEXT, /* basename, not path */
  answer TEXT,
  active BOOLEAN NOT NULL CHECK(active IN(0,1)) /* version control */
);
CREATE TABLE quick_results (
  subject INTEGER,
  trial INTEGER,
  reply_filename TEXT,
  reply_asr TEXT,
  FOREIGN KEY(subject) REFERENCES users(id),
  FOREIGN KEY(trial) REFERENCES quick_trials(id)
);

