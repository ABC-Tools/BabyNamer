import flask
import socket
import logging

import openai_lib.prompt as prompt_lib
import openai_lib.chat_completion as chat_completion

from flask_sock import Sock
from flask import request, abort, jsonify

from openai_lib.assistant import Assistant
from lib import name_statistics as ns
from lib import name_meaning as nm

app = flask.Flask(__name__)
sock = Sock(app)

SCHEMA_HOST = "http://localhost"


@app.route("/")
def index():
    logging.error('a logger test')
    return flask.render_template('home.html')


@app.route("/babyname/name_facts")
def get_name_frequency():
    name = request.args.get('name', default="", type=str)
    gender = request.args.get('gender', default="", type=str)
    if not name:
        abort(400, 'Missing name or gender parameter')

    valid_male_gender = ['male', 'boy']
    valid_female_gender = ['female', 'girl']
    if gender and gender.lower() not in valid_male_gender and gender.lower() not in valid_female_gender:
        abort(400, 'Invalid gender: {}'.format(gender))

    trend = ns.NAME_FREQ.get(name, gender)
    meaning = nm.NAME_MEANING.get(name, gender)
    output = {
        'trend': trend,
        'meaning': meaning
    }
    return jsonify(output)


@app.route("/babyname/suggest")
def suggest_names():
    user_param = {}

    # Parse parameters
    for key, meta_info in prompt_lib.PARAM_TEMPLATES.items():
        val = request.args.get(key, default="", type=str)
        if not val:
            continue

        user_param[key] = val

    # validate parameters
    valid, error_msg = prompt_lib.validate_prompt_input(user_param)
    if not valid:
        abort(400, error_msg)

    resp_dict = chat_completion.send_and_receive(user_param)

    return jsonify(resp_dict)


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
