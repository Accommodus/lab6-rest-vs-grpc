#!/usr/bin/env python3

from flask import Flask, request, Response
import jsonpickle
from PIL import Image
import io
import base64
import argparse

# Initialize the Flask application
app = Flask(__name__)

import logging
log = logging.getLogger('werkzeug')
log.setLevel(logging.DEBUG)


def jsonResponse(response):
    """Pickle a dict and wrap it in a JSON Flask Response."""
    response_pickled = jsonpickle.encode(response)
    return Response(
        response=response_pickled,
        status=200,
        mimetype="application/json"
    )


def imageDimensions(data):
    """Return the width/height of an in-memory JPG/PNG image."""
    try:
        ioBuffer = io.BytesIO(data)
        img = Image.open(ioBuffer)

        return {
            'width': img.size[0],
            'height': img.size[1]
        }
    except:
        return {'width': 0, 'height': 0}


@app.route('/api/add/<int:a>/<int:b>', methods=['GET', 'POST'])
def add(a, b):
    response = {'sum': str(a + b)}
    return jsonResponse(response)


@app.route('/api/rawimage', methods=['POST'])
def rawimage():
    r = request

    # Convert the data to a PIL image type so we can extract dimensions
    return jsonResponse(imageDimensions(r.data))


@app.route('/api/dotproduct', methods=['POST'])
def dotproduct():
    r = request

    try:
        data = r.get_json()
        a = data['a']
        b = data['b']

        if len(a) != len(b):
            response = {'error': 'vectors must be the same length'}
        else:
            response = {'dotproduct': sum(x * y for x, y in zip(a, b))}
    except Exception as e:
        response = {'error': str(e)}

    return jsonResponse(response)


@app.route('/api/jsonimage', methods=['POST'])
def jsonimage():
    r = request

    # The image arrives as a base64 string inside a JSON object so that the
    # binary data survives being part of a valid JSON document.
    try:
        data = r.get_json()
        img = base64.b64decode(data['image'])
    except Exception:
        img = b''

    return jsonResponse(imageDimensions(img))


if __name__ == '__main__':
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description='Flask REST server'
    )

    parser.add_argument(
        '-p', '--port',
        type=int,
        default=5000,
        help='Port on which to run the server (default: 5000)'
    )

    args = parser.parse_args()

    # Start Flask app
    app.run(host='0.0.0.0', port=args.port, threaded=True)
