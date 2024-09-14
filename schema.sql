/* Table that describes one user.
 */
 CREATE TABLE users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  username TEXT NOT NULL UNIQUE,
  ip TEXT,
  t TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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

/* Table that describes all QuickSIN stimuli, lists the stimulus wave
 * file, and contains the expected keywords (comma separated, with homonyms
 * separated by /).
 */
CREATE TABLE quick_trials (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  snr INTEGER,
  level_number INTEGER, /* one indexed */
  trial_number INTEGER, /* in the current level, which trial number */
  filename TEXT, /* basename, not path */
  answer TEXT,
  active BOOLEAN NOT NULL CHECK(active IN(0,1)) /* version control */
);

/* Table that describes one trial (play one sound, get one response.)
 * points to user name and trial information (above).  The ASR response
 * links to entries in this table.
 */
CREATE TABLE quick_results (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  subject INTEGER,
  trial INTEGER,
  reply_filename TEXT,
  t TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY(subject) REFERENCES users(id),
  FOREIGN KEY(trial) REFERENCES quick_trials(id)
);

/* Table that describes the ASR response for a user trial.  Contains the ASR
 * response, and is keyed to the quick_results above.
 */
CREATE TABLE quick_asr (
  ref INTEGER,
  data TEXT,
  FOREIGN KEY(ref) REFERENCES quick_results(id)
);

/* Table that describes which words that the audiologist identified as being
 * correctly spoken by the patient.  (We want to compare these results to the
 * ASR results in the quick_asr table.) Entries in this table are tied to the
 * quick_results table above.
 */
CREATE TABLE quick_annotations (
  ref INTEGER,
  data TEXT,
  FOREIGN KEY(ref) REFERENCES quick_results(id)
)

