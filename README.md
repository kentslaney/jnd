## useful commands
deploy server and detach process
```bash
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

Colab that synthesizes the needed CSV transcript files is at:
https://colab.research.google.com/drive/1EOPHV74jawtxrZSQh94Dp5AFAGFt0Pkn?usp=sharing

Google drive folder with all the segmented data:
https://drive.google.com/file/d/13jEsPhXe3BDUxHWO3Z0R3AMMfE6QDjAU/view?usp=drive_link

To add a new test do the following:
1) Add new spec, blueprint and database classes for the project to `audio.py`.
2) Add the blueprint to the projects list and the database to the ExperimentDB inheritance in `api.py`
3) Add new transcript to the metadata directory matching the path in the spec class (and migrate the database)
4) Add the audio files to the server, but not the repo
