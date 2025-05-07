## useful commands
deploy server and detach process
```bash
conda activate quicksin # Or whatever environment you use
nohup sh server.sh & tail -f nohup.out
```
kill server and uwsgi processes
```bash
ps x | grep [s]erver | sed 's/^ \+\([0-9]\+\).*/\1/g' | xargs kill && \
killall uwsgi && watch 'ps x'
```
staging server that skips audio in favor of logged answers
```bash
FLASK_APP="debug:app" flask run -p 8088 --debug
```

To run offline ASR on the collected utterances (From Kent's account):
```bash
  source ~kent/env/bin/activate
  python3 offline_asr.py --model tiny.en
```

[Colab that synthesizes the needed CSV transcript files](
https://colab.research.google.com/drive/1EOPHV74jawtxrZSQh94Dp5AFAGFt0Pkn?usp=sharing)

[Google drive folder with all the segmented data](
https://drive.google.com/drive/folders/1XfQn3eAjBY6h9Q7wruck7zqJVS7cCEQG)
And within that the Web_Audio folder has the renamed data we play to subjects.

## Adding tests
1) Add new transcript to `metadata` matching the path in the spec class below
2) In `projects.py`, add a new spec, blueprint and database classes for the
project
3) In `api.py`, add the blueprint to `APIBlueprint.projects` and the new
database class to the `ExperimentDB` parents
4) run `python migrate.py projects.[ProjectDBClass]`
5) Add the audio files to `static/audio/[project]/*.wav`
6) Add `static/[project].html` and replace the project name in the inline script
tag and add `static/[project]_done.html`

## OAuth
1) update owner id in `protected.py`:
```
malcolmslaney@gmail.com 110909794990702804159
mslaney@stanford.edu    100987618575971262389
Varsha Mysore Athreya   114354889327043931514
Matthew Fitzgerald      101607400393342786056
```

2) update `protected.py`'s value for `login_required.prefix` to the real
subdomain

3) [login client](https://github.com/kentslaney/login/) (as a sibling to jnd):
```
git clone git@github.com:kentslaney/login
```

4) [Google OAuth credentials page](
https://console.cloud.google.com/apis/credentials) Web application replacing
`sub.domain.tld` with the subdomain used in `protected.py`
```
Authorized JavaScript origins: https://sub.domain.tld
Authorized redirect URIs: https://sub.domain.tld/login/google/authorized
```

5) put the resulting credentials in `login/run/credentials.json`:
```
{
    "google|facebook|github": {"id": "username", "secret": "API key"},
}
```

6) with the environment running the QuickSIN server:
```bash
pip install -e path/to/login # ../login probably
```

7) in `login`
```bash
sh server.sh start
```

8) change `server.sh` from `uwsgi.ini` to `login.ini` and start the QuickSIN
server

9) go to `/login/access/view/invite`, check the audio group, remove the
`invitees` value if you want the invite to work for more than one person,
and change the redirect URL to `/jnd`, then you can distribute the invite
