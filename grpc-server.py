#!/usr/bin/env python3

from concurrent import futures
import argparse
import base64
import io
import logging

import grpc
from PIL import Image

import lab6_pb2
import lab6_pb2_grpc

# base64 of the 1.6MB test image is ~2.2MB, which is over the 4MB default
# only once you add overhead -- bump the limit so large payloads are safe.
MAX_MESSAGE_LENGTH = 32 * 1024 * 1024


def imageDimensions(data):
    """Return an imageReply with the width/height of an in-memory image."""
    try:
        img = Image.open(io.BytesIO(data))
        return lab6_pb2.imageReply(width=img.size[0], height=img.size[1])
    except Exception:
        return lab6_pb2.imageReply(width=0, height=0)


class Lab6Servicer(lab6_pb2_grpc.Lab6Servicer):

    def add(self, request, context):
        return lab6_pb2.addReply(sum=request.a + request.b)

    def rawimage(self, request, context):
        # bytes field -- the image arrives as raw binary
        return imageDimensions(request.img)

    def dotproduct(self, request, context):
        a = request.a
        b = request.b

        if len(a) != len(b):
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details('vectors must be the same length')
            return lab6_pb2.dotProductReply(dotproduct=0)

        return lab6_pb2.dotProductReply(
            dotproduct=sum(x * y for x, y in zip(a, b))
        )

    def jsonimage(self, request, context):
        # string field -- the image arrives base64 encoded
        try:
            img = base64.b64decode(request.img)
        except Exception:
            img = b''
        return imageDimensions(img)


def serve(port):
    server = grpc.server(
        futures.ThreadPoolExecutor(max_workers=10),
        options=[
            ('grpc.max_send_message_length', MAX_MESSAGE_LENGTH),
            ('grpc.max_receive_message_length', MAX_MESSAGE_LENGTH),
        ]
    )
    lab6_pb2_grpc.add_Lab6Servicer_to_server(Lab6Servicer(), server)
    server.add_insecure_port(f'[::]:{port}')
    server.start()
    print(f"gRPC server listening on port {port}")
    server.wait_for_termination()


if __name__ == '__main__':
    logging.basicConfig()

    parser = argparse.ArgumentParser(description='gRPC server')

    parser.add_argument(
        '-p', '--port',
        type=int,
        default=50051,
        help='Port on which to run the server (default: 50051)'
    )

    args = parser.parse_args()

    serve(args.port)
