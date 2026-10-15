# Lab 6 - REST vs gRPC

## How to run

Dependencies are managed with `uv` (see `pyproject.toml`).

```
uv sync

# REST  (default port 5000)
uv run rest-server.py
uv run rest-client.py <host> <add|rawImage|dotProduct|jsonImage> <reps> [-d]

# gRPC  (default port 50051)
uv run grpc-server.py
uv run grpc-client.py <host> <add|rawImage|dotProduct|jsonImage> <reps> [-d]
```

The gRPC stubs (`lab6_pb2.py`, `lab6_pb2_grpc.py`) are checked in. To regenerate
them from `lab6.proto`:

```
uv run python -m grpc_tools.protoc -I. --python_out=. --pyi_out=. --grpc_python_out=. lab6.proto
```

## Measurements

All numbers are **milliseconds per operation**, measured with `time.perf_counter()`
over many repetitions and divided by the repetition count.

Test setup (GCP project `lab2-url-lister`, all `e2-standard-2`, Debian 12, all
traffic over **internal** 10.x addresses on the default VPC):

| Column | Client | Server |
|---|---|---|
| Local | `lab6-client` (us-west1-a) | same host, `localhost` |
| Same-Zone | `lab6-client` (us-west1-a, 10.138.0.18) | `lab6-server` (us-west1-a, 10.138.0.17) |
| Different Region | `lab6-client` (us-west1-a) | `lab6-euro` (europe-west3-a, 10.156.0.2) |

Repetitions: 1000 for `add`/`dotproduct` and 100 for the image endpoints in the
Local and Same-Zone columns; 100 and 20 respectively for the Different-Region
column, to keep the running time manageable. `ping` used 20 packets.

|  Method 	| Local  	| Same-Zone  	|  Different Region 	|
|---	|---	|---	|---	|
|   REST add	|   2.909	|   3.075	|  342.359	|
|   gRPC add	|   0.747	|   1.053	|  165.150  	|
|   REST rawimg	|   5.234	|   6.896	|  1414.522 	|
|   gRPC rawimg	|   9.843  |   10.854	|  279.548  	|
|   REST dotproduct	|   3.400	|   3.479	|  345.737	|
|   gRPC dotproduct	|   0.833	|   1.119	|  164.854  	|
|   REST jsonimg	|   26.753	|   28.086	|  1562.457 	|
|   gRPC jsonimg	|   25.147  |   24.091	|  282.545  	|
|   PING        |   0.053   |   0.384  |   159.907    |

## Observations

**Latency is the whole story, and the difference comes from TCP connection reuse.**
On the lightweight calls (`add`, `dotproduct`) the payload is a few hundred bytes, so
essentially all of the measured time is protocol overhead. Locally and within a zone
gRPC is roughly 3x faster than REST (0.75–1.1 ms vs 2.9–3.5 ms) — at a 0.05–0.38 ms
RTT the network is free, so this gap is pure software cost: Flask/Werkzeug parsing an
HTTP/1.1 text request and `requests` building a fresh connection each call, versus
gRPC's compiled protobuf serialization over an already-open HTTP/2 stream.

Across regions the structural difference dominates. The raw RTT to Frankfurt is
**159.9 ms**, and gRPC `add` costs **165.2 ms** — essentially one RTT plus ~5 ms of
overhead, which is the floor you can achieve. REST `add` costs **342.4 ms**, almost
exactly *two* RTTs. That extra RTT is the TCP three-way handshake: the REST client
opens a new connection for every single query, so it pays a full round trip before it
can even send the request, then another for the request/response. gRPC opens one
channel up front and multiplexes all 100 queries over it, amortizing the handshake to
nothing. Note that `dotproduct` costs the same as `add` in every column — 100 floats
is small enough that it is still a pure latency measurement, not a bandwidth one.

**For the large payloads, bandwidth and encoding matter and the ranking flips locally.**
With a 1.6 MB image, `rawimage` is the one case where REST *beats* gRPC locally
(5.2 ms vs 9.8 ms): over loopback there is no network cost to save, and gRPC's
protobuf framing and HTTP/2 flow control on a multi-megabyte message cost more than
Flask simply handing over `request.data`. Over the WAN that reverses dramatically —
REST `rawimg` takes **1414 ms** versus **280 ms** for gRPC. Repeatedly opening a new
TCP connection per request means every REST image transfer restarts in TCP slow
start and never reaches full window size, while gRPC's long-lived connection keeps a
wide congestion window and streams at full speed.

`jsonimage` is the most expensive endpoint everywhere (24–28 ms locally) because
base64 inflates the 1.6 MB image to ~2.2 MB *and* both sides pay to encode/decode
it, on top of JSON parsing a 2.2 MB string. That ~20 ms penalty over `rawimage` is
almost entirely client/server CPU, which is why gRPC and REST are nearly tied in the
Local and Same-Zone columns — both are bottlenecked on the same base64 and JSON work,
not on the transport. Over the WAN the transport reasserts itself and gRPC is again
~5.5x faster. The lesson is that `rawimage` is the right design: sending binary as
binary avoids a ~37% size increase and a lot of pointless CPU, and gRPC gets this for
free with its `bytes` type.
