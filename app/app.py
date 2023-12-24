import json
from werkzeug.exceptions import HTTPException

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
    return flask.render_template('home.html')


@app.route("/babyname/name_facts")
def get_name_facts():
    """
    :return: a json object like
    {
        "meaning": "The name George is typically used as a nickname for names such as ...",
        "similar_names":[
            "gudren",
            "guinevieve",
            ...
        ],
        "trend":{
            "1880": "26",
            ...
            "2021": "7"
        }
    }
    """
    session_id = request.args.get('session_id', default="", type=str)
    if not session_id or not sid.verify_session_id(session_id):
        abort(400, "missing or invalid session id: {}".format(session_id))

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

    # get last recommendation reason if there is one
    last_name_proposals = redis_lib.get_name_proposals(session_id)
    if last_name_proposals and name in last_name_proposals and last_name_proposals[name]:
        output['recommend_reason'] = last_name_proposals[name]

    return jsonify(output)


@app.route("/babyname/suggest")
def suggest_names():
    session_id = request.args.get('session_id', default="", type=str)
    if not session_id or not sid.verify_session_id(session_id):
        abort(400, "missing or invalid session id: {}".format(session_id))

    # if no refresh and there is proposal available, return last proposal
    proposal_refresh_strategy = request.args.get('proposal_refresh', default="", type=str)
    if proposal_refresh_strategy.lower() in ['no_refresh'] and redis_lib.get_last_proposal_time() > 0:
        proposal_dict = redis_lib.get_name_proposals(session_id)
        return jsonify(proposal_dict)

    # Parse preferences parameters
    all_prefs = {}
    for pref_class in np.ALL_PREFERENCES:
        val = request.args.get(pref_class.get_url_param_name(), default="", type=str)
        if not val:
            continue
        all_prefs[pref_class.get_url_param_name()] = val

    # Parse preferences
    parsed_prefs = np.str_dict_to_class_dict(all_prefs)
    # update the preferences in redis first
    redis_lib.update_user_pref(session_id, parsed_prefs)

    # Fetch all preferences from redis
    all_prefs = redis_lib.get_user_pref(session_id)

    # Fetch proposals from ChatGPT
    resp_dict = chat_completion.send_and_receive(all_prefs)

    # Write a copy in redis for late references
    redis_lib.update_name_proposals(session_id, resp_dict)

    return jsonify(resp_dict)


@app.route("/babyname/update_pref")
def update_pref():
    session_id = request.args.get('session_id', default="", type=str)
    if not session_id or not sid.verify_session_id(session_id):
        abort(400, "missing or invalid session id: {}".format(session_id))

    # Parse parameters
    all_prefs = {}
    for pref_class in np.ALL_PREFERENCES:
        val = request.args.get(pref_class.get_url_param_name(), default="", type=str)
        if not val:
            continue
        all_prefs[pref_class.get_url_param_name()] = val

    parsed_prefs = np.str_dict_to_class_dict(all_prefs)

    redis_lib.update_user_pref(session_id, parsed_prefs)

    return json.dumps({"msg": "success"})


@app.route("/babyname/get_pref")
def get_pref():
    """
    :return: a dictionary like
    {
        'gender': 'boy',
        'names_to_avoid': '["George", "Mike", ...]' <-- the value is a dictionary
        ...,
        'name_sentiments': {
            "Aron": {"sentiment": "liked", "reason": "sounds good"},
            "Jasper": {"sentiment": "disliked", "reason": "my neighbor uses this name"},
            "Jayden": {"sentiment": "saved"}
        }
    }
    """
    session_id = request.args.get('session_id', default="", type=str)
    if not session_id or not sid.verify_session_id(session_id):
        abort(400, "missing or invalid session id: {}".format(session_id))

    prefs = redis_lib.get_user_pref(session_id)
    native_prefs = np.class_dict_to_native_dict(prefs)
    return json.dumps(native_prefs)


@app.route("/babyname/get_name_sentiments")
def get_name_sentiments():
    """
    :return: a dictionary like
    {
        "liked": [
            {
                "name": "George",
                "reason": "blah"
            },
            {
                "name": "Mike",
                "reason": "what..."
            }
        ],
        "disliked": [
            {
                "name": "Kayden",
                "reason": "blah"
            },
            {
                "name": "Allen",
                "reason": "what..."
            }
        ]
    }
    """
    session_id = request.args.get('session_id', default="", type=str)
    if not session_id or not sid.verify_session_id(session_id):
        abort(400, "missing or invalid session id: {}".format(session_id))

    name_sentiments = redis_lib.get_name_sentiments(session_id)
    if not name_sentiments:
        return {}

    name_sentiments_by_sentiments = np.name_sentiments_by_sentiments(name_sentiments)
    return json.dumps(name_sentiments_by_sentiments)


if os.environ.get("ENV") == "DEV":
    @app.route("/babyname/create_sid")
    def create_sid():
        logging.info("test")
        return sid.create_session_id()

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
