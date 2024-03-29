uwsgi --ini "$( dirname -- "$0" )/uwsgi.ini"
# source env/bin/activate
# nohup sh server.sh &
# ps x | grep [s]erver | cut -f2 -d' ' | xargs kill && killall uwsgi
# FLASK_APP="debug:app" flask run -p 8088

