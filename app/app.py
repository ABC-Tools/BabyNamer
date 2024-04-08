import time

from werkzeug.exceptions import HTTPException

import json
import flask
import socket
import logging
import os

from flask_sock import Sock
from flask import request, abort, jsonify, g

import app.lib.redis as redis_lib
from app.lib.name_sentiments import UserSentiments
from app.lib import name_sentiments as sentiments
from app.openai_lib.assistant import Assistant
from app.lib import name_statistics as ns
from app.lib import name_meaning as nm
from app.lib import similar_names as sn
from app.lib import name_pref as np
from app.lib import session_id as sid
from app.lib import origin_and_short_meaning as osm
from app.lib.common import canonicalize_gender, canonicalize_name
from app.lib import name_rating as nr

import app.procedure.suggest_names as suggest_names_proc

app = flask.Flask(__name__)
app.config['JSON_SORT_KEYS'] = False
sock = Sock(app)


@app.before_request
def logging_before():
    # Store the start time for the request
    g.start_time = time.perf_counter()


@app.after_request
def after_request(response):
    latency = int((time.perf_counter() - g.start_time) * 1000)
    logging.info('End latency of request ({endpoint}) is {latency}ms.'.format(
        endpoint=request.path, latency=latency))
    return response


@app.errorhandler(Exception)
def handle_error(e):
    code = 500
    if isinstance(e, HTTPException):
        code = e.code

    logging.exception(e)
    return jsonify(error=str(e)), code


@app.route("/")
def index():
    return flask.render_template('mainpage.html')
    # return 'success'


@app.route("/babyname/privacy_notice")
def privacy_notice():
    return flask.render_template('privacy.html')


@app.route("/babyname/tos")
def term_of_service():
    return flask.render_template('tos.html')


@app.route("/babyname/name_facts")
def get_name_facts():
    """
    note all keys in the response json may be missing

    :return: a json object like
    {
        "origin": "Hebrew",
        "short_meaning": "Rest, Peace"
        "meaning": "The name George is typically used as a nickname for names such as ...",
        "similar_names":[
            "Liam",
            "Elijah",
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
    name = canonicalize_name(name)

    try:
        gender = canonicalize_gender(gender)
    except ValueError as e:
        abort(400, 'Invalid gender: {}'.format(gender))
    if not gender:
        gender = ns.NAME_STATISTICS.guess_gender(name)

    logging.info('[data] user {} request names facts for {}'.format(session_id, name))

    origin, short_meaning = osm.ORIGIN_SHORT_MEANING.get(name, gender)
    trend = ns.NAME_STATISTICS.get_yearly_trend(name, gender)
    meaning = nm.NAME_MEANING.get(name, gender)
    similar_names = sn.SIMILAR_NAMES.get(name, gender)

    output = {
        'gender': str(gender),
        'origin': origin,
        'short_meaning': short_meaning,
        'meaning': meaning,
        'similar_names': similar_names,
        'trend': trend
    }

    # get last recommendation reason if there is one
    proposal_reason = redis_lib.get_proposal_reason_for_name(session_id, name)
    if proposal_reason:
        output['recommend_reason'] = proposal_reason

    # get sentiment if there is any
    sentiment_dict = redis_lib.get_sentiment_for_name(session_id, name)
    if sentiment_dict:
        output[UserSentiments.get_url_param_name()] = sentiment_dict

    _, rank = ns.NAME_STATISTICS.get_frequency_and_rank(name, gender)
    if rank < 100000:
        output['rank'] = rank

    feature_scores = nr.NAME_RATING.get_feature_scores(name, gender)
    if feature_scores:
        output['features'] = feature_scores

    return jsonify(output)


@app.route("/babyname/suggest")
def suggest_names():
    """
    URL parameters:
    - session_id: required
    - gender: required
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
    gender = request.args.get(np.GenderPref.get_url_param_name(), default="", type=str)
    gender = canonicalize_gender(gender)
    if not gender:
        abort(400, "missing the required parameter of gender")

    # update user preferences
    pref_resp_msg = update_user_pref(func_call=True, delete_before_updating=True)

    # Update user sentiments
    update_user_sentiments(func_call=True)

    # if user preference is not updated and there is previous proposals, use the previous proposals
    if 'no-op' in pref_resp_msg.get('msg', ''):
        last_proposals = redis_lib.get_displayed_names(session_id, max_count=20)
        if last_proposals:
            return jsonify(last_proposals)

    start_ts = time.time()
    suggested_names = suggest_names_proc.suggest(session_id, gender, filter_displayed_names=False)
    logging.info('Compute recommended name using {} seconds'.format(time.time() - start_ts))

    resp_dict = {
        'suggested_names': suggested_names,
        'page_no': 0
    }
    return jsonify(resp_dict)


@app.route("/babyname/refresh")
def suggest_more():
    session_id = request.args.get('session_id', default="", type=str)
    if not session_id or not sid.verify_session_id(session_id):
        abort(400, "missing or invalid session id: {}".format(session_id))

    gender = request.args.get(np.GenderPref.get_url_param_name(), default="", type=str)
    gender = canonicalize_gender(gender)
    if not gender:
        abort(400, "missing the required parameter of gender")

    last_suggest_no = request.args.get('last_suggest_no', default=0, type=int)

    # Update user sentiments
    update_user_sentiments(func_call=True)

    start_ts = time.time()
    suggested_names = suggest_names_proc.suggest(session_id, gender, filter_displayed_names=True)
    logging.info('Compute recommended name using {} seconds'.format(time.time() - start_ts))

    resp_dict = {
        'suggested_names': suggested_names,
        'page_no': 0
    }
    return jsonify(resp_dict)


@app.route("/babyname/update_user_pref")
def update_user_pref(func_call=False, delete_before_updating=False):
    """
    URL parameters:
        - session_id: required
        - gender: boy/girl, required
        - family_name: Tan
        - mother_name: Amy
        - father_name: Sam
        - * sibling_names: ["Kaitlyn", "George"]
        - * origin: China
        - names_to_avoid: ["Mike", "Allen"]
        - * other: "whatever the user writes"
        - * 'popularity_option': "Popular" / "Unique"
        - * 'style_option': "Classic"/"Modern",
        - 'maturity_option': "Mature"/"Youthful"
        - * 'formality_option': "Formal"/"Casual"
        - 'class_option': "Noble"/"Grassroots "
        - 'environment_option': "Urban"/"Natural"
        - 'moral_option': "Wholesome"/"Tactful"
        - * 'strength_option': "Strong"/"Delicate"
        - 'texture_option': "Refined"/"Rough"
        - 'creativity_option': "Creative"/"Practical"
        - * 'complexity_option': "Simple"/"Complex"
        - 'tone_option': "Serious"/"Cute"
        - 'intellectual_option': "Intellectual"/"Modest"
    :return:
    """
    session_id = request.args.get('session_id', default="", type=str)
    if not session_id or not sid.verify_session_id(session_id):
        if func_call:
            return {"msg": "failure"}
        else:
            abort(400, "missing or invalid session id: {}".format(session_id))

    # Parse parameters
    all_prefs = {}
    for pref_class in np.ALL_PREFERENCES:
        val = request.args.get(pref_class.get_url_param_name(), default="", type=str)
        if not val:
            continue
        all_prefs[pref_class.get_url_param_name()] = val
    logging.info('[data] Preferences from session {} is: {}'.format(session_id, json.dumps(all_prefs)))

    if not all_prefs or (len(all_prefs) == 1 and all_prefs.get(np.GenderPref.get_url_param_name(), None)):
        resp = {"msg": "success; no-op"}
        return json.dumps(resp) if not func_call else resp

    parsed_prefs = np.str_dict_to_class_dict(all_prefs)
    redis_lib.update_user_pref(session_id, parsed_prefs, delete_before_updating=delete_before_updating)

    resp = {"msg": "success"}
    return jsonify({"msg": "success"}) if not func_call else resp


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
    return jsonify(native_prefs)


@app.route("/babyname/update_user_sentiments")
def update_user_sentiments(func_call=False):
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

    sentiments_str = request.args.get(UserSentiments.get_url_param_name(), default="", type=str)
    if not sentiments_str:
        if func_call:
            return json.dumps({"msg": "success; no-op"})
        else:
            abort(400, "missing user sentiments in request")

    logging.info('[data] sentiments from session {}: {}'.format(session_id, sentiments_str))
    sentiments_inst = UserSentiments.create(sentiments_str)
    redis_lib.update_user_sentiments(session_id, sentiments_inst)

    resp = {"msg": "success"}
    return jsonify(resp) if not func_call else resp


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

    name_sentiments_by_sentiments = sentiments.name_sentiments_by_sentiments(name_sentiments)
    return jsonify(name_sentiments_by_sentiments)


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
