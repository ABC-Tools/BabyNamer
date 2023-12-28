import json
from collections import OrderedDict

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
app.config['JSON_SORT_KEYS'] = False
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
    note all keys in the response json may be missing

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
        },
        "recommend_reason": "the name sounds great",
        "name_sentiments": {
            "sentiment": "disliked",
            "reason": "my neighbor uses this name"
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

    trend = ns.NAME_STATISTICS.get_yearly_trend(name, gender)
    meaning = nm.NAME_MEANING.get_yearly_trend(name, gender)
    similar_names = sn.SIMILAR_NAMES.get_yearly_trend(name, gender)

    output = {
        'trend': trend,
        'meaning': meaning,
        'similar_names': similar_names
    }

    # get last recommendation reason if there is one
    proposal_reason = redis_lib.get_proposal_for_name(session_id, name)
    if proposal_reason:
        output['recommend_reason'] = proposal_reason

    # get sentiment if there is any
    sentiment_dict = redis_lib.get_sentiment_for_name(session_id, name)
    if sentiment_dict:
        output[np.UserSentiments.get_url_param_name()] = sentiment_dict

    return jsonify(output)


@app.route("/babyname/suggest")
def suggest_names():
    """
    URL parameters:
    - session_id
    - source: default / popularity_ranking / cached / chatgpt
        -- default: let system decides
        -- popularity_ranking: based on last 3 years ranking of names; this is very fast
        -- cache: fetch from latest suggestions made by ChatGPT
        - chatgpt: fetch from chatgpt; this usually takes 20+ seconds
    - any URL parameters which are accepted by update_user_pref()
    - any URL parameters which are accepted by update_user_sentiments
    :return: name proposals
    {
        "Mike": "the name has a close relationship with China, ..."
        "John": "the name resonate well with George. ..."
    }
    """
    session_id = request.args.get('session_id', default="", type=str)
    if not session_id or not sid.verify_session_id(session_id):
        abort(400, "missing or invalid session id: {}".format(session_id))

    # suggestion from SSA popularity data or cache
    source = request.args.get('source', default="", type=str)
    cache_ts = redis_lib.get_last_proposal_time(session_id)
    if (source.lower() in ['cache'] and cache_ts) or \
            (source.lower() in ['default'] and cache_ts > redis_lib.get_last_pref_update_time(session_id)):
        proposal_dict = redis_lib.get_name_proposals(session_id)
        return jsonify(proposal_dict)
    elif source.lower() in ['popularity_ranking']:
        gender = request.args.get(np.GenderPref.get_url_param_name(), default="", type=str)
        top_names = ns.NAME_STATISTICS.get_popular_names(gender)
        resp_dict = OrderedDict()
        for i, name in enumerate(top_names):
            resp_dict[name] = 'Ranked {} most popular names in the past 3 years'.format(i + 1)
        return jsonify(resp_dict)

    # update user preferences
    update_user_pref()

    # Update user sentiments
    update_user_sentiments(raise_on_missing_param=False)

    # Fetch all preferences and sentiments from redis
    user_prefs = redis_lib.get_user_pref(session_id)
    user_sentiments = redis_lib.get_user_sentiments(session_id)

    # Fetch proposals from ChatGPT
    resp_dict = chat_completion.send_and_receive(user_prefs, user_sentiments)

    # Write a copy in redis for late references
    redis_lib.update_name_proposals(session_id, resp_dict)

    return jsonify(resp_dict)


@app.route("/babyname/update_user_pref")
def update_user_pref():
    """
    URL parameters:
        - session_id:
        - gender: boy/girl,
        - family_name: Tan
        - mother_name: Amy
        - father_name: Sam
        - sibling_names: ["Kaitlyn", "George"]
        - origin: China
        - names_to_avoid: ["Mike", "Allen"]
        - other: "whatever the user writes"
    :return:
    """
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
    if not all_prefs:
        return json.dumps({"msg": "success; no-op"})

    parsed_prefs = np.str_dict_to_class_dict(all_prefs)
    redis_lib.update_user_pref(session_id, parsed_prefs)

    return json.dumps({"msg": "success"})


@app.route("/babyname/get_user_pref")
def get_user_pref():
    """
    required URL parameter is session id

    :return: a dictionary like
    {
        'gender': 'boy',
        'names_to_avoid': '["George", "Mike", ...]' <-- the value is a dictionary
        ...,
    }
    """
    session_id = request.args.get('session_id', default="", type=str)
    if not session_id or not sid.verify_session_id(session_id):
        abort(400, "missing or invalid session id: {}".format(session_id))

    prefs = redis_lib.get_user_pref(session_id)
    native_prefs = np.class_dict_to_native_dict(prefs)
    return json.dumps(native_prefs)


@app.route("/babyname/update_user_sentiments")
def update_user_sentiments(raise_on_missing_param=True):
    """
    expect an input JSON like
    {
        "Aron": {"sentiment": "liked", "reason": "sounds good"},
        "Jasper": {"sentiment": "disliked", "reason": "my neighbor uses this name"},
        "Jayden": {"sentiment": "saved"}
    }
    :return: success
    """
    session_id = request.args.get('session_id', default="", type=str)
    if not session_id or not sid.verify_session_id(session_id):
        abort(400, "missing or invalid session id: {}".format(session_id))

    sentiments_str = request.args.get(np.UserSentiments.get_url_param_name(), default="", type=str)
    if not sentiments_str:
        if raise_on_missing_param:
            abort(400, "missing user sentiments in request")
        else:
            return json.dumps({"msg": "success; no-op"})

    sentiments_inst = np.UserSentiments.create(sentiments_str)
    redis_lib.update_user_sentiments(session_id, sentiments_inst)
    return json.dumps({"msg": "success"})


@app.route("/babyname/get_name_sentiments")
def get_name_sentiments():
    """
    required URL parameter is session id

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

    name_sentiments = redis_lib.get_user_sentiments(session_id)
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
