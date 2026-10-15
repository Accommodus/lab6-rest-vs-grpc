#!/usr/bin/env python3

from __future__ import print_function

import argparse
import base64
import random
import time

import grpc

import lab6_pb2
import lab6_pb2_grpc

IMAGE_FILE = 'Flatirons_Winter_Sunrise_edit_2.jpg'
VECTOR_LENGTH = 100
MAX_MESSAGE_LENGTH = 32 * 1024 * 1024


def doAdd(stub, debug=False):
    response = stub.add(lab6_pb2.addMsg(a=5, b=10))

    if debug:
        print("Sum is", response.sum)


def doRawImage(stub, debug=False):
    img = open(IMAGE_FILE, 'rb').read()

    response = stub.rawimage(lab6_pb2.rawImageMsg(img=img))

    if debug:
        print("Width", response.width, "Height", response.height)


def doDotProduct(stub, debug=False):
    a = [random.random() for _ in range(VECTOR_LENGTH)]
    b = [random.random() for _ in range(VECTOR_LENGTH)]

    response = stub.dotproduct(lab6_pb2.dotProductMsg(a=a, b=b))

    if debug:
        print("Dot product is", response.dotproduct)
        # protobuf 'float' is single precision, so expect a small difference
        print("Locally computed:", sum(x * y for x, y in zip(a, b)))


def doJsonImage(stub, debug=False):
    img = open(IMAGE_FILE, 'rb').read()

    # the jsonImageMsg carries a string, so base64 encode the binary data
    encoded = base64.b64encode(img).decode('utf-8')

    response = stub.jsonimage(lab6_pb2.jsonImageMsg(img=encoded))

    if debug:
        print("Width", response.width, "Height", response.height)


# ---------------------------------------------------------
# Parse command-line arguments
# ---------------------------------------------------------

parser = argparse.ArgumentParser(
    description='gRPC client for measuring server operations'
)

parser.add_argument(
    'host',
    help='IP address or hostname of the gRPC server'
)

parser.add_argument(
    'cmd',
    choices=['add', 'rawImage', 'dotProduct', 'jsonImage'],
    help='Operation to perform'
)

parser.add_argument(
    'reps',
    type=int,
    help='Number of repetitions for measurement'
)

parser.add_argument(
    '-p', '--port',
    type=int,
    default=50051,
    help='Server port (default: 50051)'
)

parser.add_argument(
    '-d', '--debug',
    action='store_true',
    help='Print the response from the server'
)

args = parser.parse_args()


addr = f"{args.host}:{args.port}"

print(f"Running {args.reps} reps against {addr}")

operations = {
    'add': doAdd,
    'rawImage': doRawImage,
    'dotProduct': doDotProduct,
    'jsonImage': doJsonImage,
}

operation = operations[args.cmd]

# One channel is opened and reused for every repetition -- this is the key
# structural difference from the REST client, which builds a new TCP
# connection for each request.
with grpc.insecure_channel(
    addr,
    options=[
        ('grpc.max_send_message_length', MAX_MESSAGE_LENGTH),
        ('grpc.max_receive_message_length', MAX_MESSAGE_LENGTH),
    ]
) as channel:
    stub = lab6_pb2_grpc.Lab6Stub(channel)

    start = time.perf_counter()

    for x in range(args.reps):
        operation(stub, debug=args.debug)

    delta = ((time.perf_counter() - start) / args.reps) * 1000
    print("Took", delta, "ms per operation")
