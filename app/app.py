import json
from http.client import HTTPException

import flask
import socket
import logging
import os

import app.openai_lib.chat_completion as chat_completion
import app.lib.redis as redis_lib

from flask_sock import Sock
from flask import request, abort, jsonify

from app.openai_lib.assistant import Assistant
from app.lib import name_statistics as ns
from app.lib import name_meaning as nm
from app.lib import similar_names as sn
from app.lib import name_pref as np
from app.lib import session_id as sid

app = flask.Flask(__name__)
sock = Sock(app)

SCHEMA_HOST = "http://localhost"


@app.errorhandler(Exception)
def handle_error(e):
    code = 500
    if isinstance(e, HTTPException):
        code = e.code
    logging.exception(e)
    return jsonify(error=str(e)), code


@app.route("/")
def index():
    logging.error('a logger test')
    return flask.render_template('home.html')


@app.route("/babyname/name_facts")
def get_name_frequency():
    name = request.args.get('name', default="", type=str)
    gender = request.args.get('gender', default="", type=str)
    if not name:
        abort(400, 'Missing name parameter')

    valid_male_gender = ['male', 'boy']
    valid_female_gender = ['female', 'girl']
    if gender and gender.lower() not in valid_male_gender and gender.lower() not in valid_female_gender:
        abort(400, 'Invalid gender: {}'.format(gender))

    trend = ns.NAME_FREQ.get(name, gender)
    meaning = nm.NAME_MEANING.get(name, gender)
    similar_names = sn.SIMILAR_NAMES.get(name, gender)
    output = {
        'trend': trend,
        'meaning': meaning,
        'similar_names': similar_names
    }
    return jsonify(output)


@app.route("/babyname/suggest")
def suggest_names():
    # Parse parameters
    all_prefs = []
    for pref_class in np.ALL_PREFERENCES:
        val = request.args.get(pref_class.get_url_param_name(), default="", type=str)
        if not val:
            if pref_class == np.GenderPref:
                abort(400, 'Missing name parameter')
            else:
                continue

        pref = pref_class.create(val)
        if pref is not None:
            all_prefs.append(pref)

    resp_dict = chat_completion.send_and_receive(all_prefs)

    return jsonify(resp_dict)


if os.environ.get("ENV") == "DEV":
    @app.route("/babyname/create_sid")
    def create_sid():
        logging.info("test")
        return sid.create_session_id()

    @app.route("/babyname/write_pref")
    def write_pref():
        logging.info("test 234")
        session_id = request.args.get('session_id', default="", type=str)
        if not session_id:
            abort(400, "missing session id")

        # Parse parameters
        all_prefs = {}
        for pref_class in np.ALL_PREFERENCES:
            val = request.args.get(pref_class.get_url_param_name(), default="", type=str)
            if not val:
                continue
            all_prefs[pref_class.get_url_param_name()] = val

        parsed_prefs = np.str_dict_to_class_dict(all_prefs)

        redis_lib.write_user_pref(session_id, parsed_prefs)

        return "success"

    @app.route("/babyname/get_pref")
    def get_pref():
        session_id = request.args.get('session_id', default="", type=str)
        if not session_id:
            abort(400, "missing session id")

        prefs = redis_lib.get_user_pref(session_id)
        native_prefs = np.class_dict_to_native_dict(prefs)
        return json.dumps(native_prefs)

    @sock.route('/echo')
    def echo(sock):
        logging.info('start socket')
        assistant = Assistant()

        try:
            while True:
                data = sock.receive()

                sock.send("Baby Namer is thinking... ")
                msg = assistant.send_and_receive(data)
                sock.send('Assistant: ' + msg)
        except Exception as e:
            logging.exception(e, exc_info=True)
            raise e


    @app.route("/list_ip")
    def list_ip():
        try:
            host_name = socket.gethostname()
            host_ip = socket.gethostbyname(host_name)
            return flask.render_template('index.html', host_name, host_ip)
        except:
            return flask.render_template('error.html')


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8080)
