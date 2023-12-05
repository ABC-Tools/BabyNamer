import flask
import socket
import logging

from flask_sock import Sock
from flask import request, abort, jsonify

from  openai_lib.assistant import Assistant
from lib import name_statistics as ns

app = flask.Flask(__name__)
sock = Sock(app)

SCHEMA_HOST = "http://localhost"


@app.route("/")
def index():
    logging.error('a logger test')
    return flask.render_template('home.html')


@app.route("/get_name_frequency")
def get_name_frequency():
    name = request.args.get('name', default="", type=str)
    gender = request.args.get('gender', default="", type=str)
    if not name or not gender:
        abort(400, 'Missing name or gender parameter')

    valid_male_gender = ['male', 'M', 'Male', "MALE"]
    valid_female_gender = ['female', 'F', 'Female', 'FEMALE']
    if gender not in valid_male_gender and gender not in valid_female_gender:
        abort(400, 'Invalid gender: {}'.format(gender))

    if gender in valid_male_gender:
        canonical_gender = 'M'
    else:
        canonical_gender = 'F'

    try:
        trend = ns.NAME_FREQ.get(name, canonical_gender)
    except ValueError as e:
        logging.error('Unable to find trending for: {}, {}'.format(name, canonical_gender))
        abort(404, 'Unable to find trending for: {}, {}'.format(name, canonical_gender))

    return jsonify(trend)


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
