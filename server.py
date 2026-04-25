#!/usr/bin/env python3
"""
C Train countdown server.
Fetches the MTA ACE GTFS-Realtime feed, filters for northbound C trains
at stop A42N, and serves the next arrivals in minutes as JSON.

Setup:
    pip3 install -r requirements.txt
    python3 server.py

Endpoint:
    GET http://localhost:5001/arrivals  ->  [3, 8, 14]
"""

import os
import time
import urllib.request
import json
from http.server import HTTPServer, BaseHTTPRequestHandler
from google.transit import gtfs_realtime_pb2

# ── Config ────────────────────────────────────────────────────────────────────

# Note: the %2F encoding in the path is required — /nyct/gtfs-ace returns 403
FEED_URL  = "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-ace"
STOP_ID   = "A42N"    # Clinton-Washington, northbound platform
ROUTE_ID  = "C"
PORT      = int(os.environ.get("PORT", 5001))
CACHE_TTL = 20        # seconds between feed fetches

_cache_time      = 0
_cached_arrivals = []


# ── Feed parsing ──────────────────────────────────────────────────────────────

def fetch_arrivals():
    """Return sorted list of minutes until next C trains at A42N."""
    with urllib.request.urlopen(FEED_URL, timeout=10) as resp:
        raw = resp.read()

    feed = gtfs_realtime_pb2.FeedMessage()
    feed.ParseFromString(raw)

    now = time.time()
    arrivals = []

    for entity in feed.entity:
        if not entity.HasField("trip_update"):
            continue
        if entity.trip_update.trip.route_id != ROUTE_ID:
            continue
        for stu in entity.trip_update.stop_time_update:
            if stu.stop_id != STOP_ID:
                continue
            t = stu.arrival.time or stu.departure.time
            if t <= 0:
                continue
            minutes = int((t - now) / 60)
            if minutes > 0:
                arrivals.append(minutes)

    arrivals.sort()
    return arrivals[:4]


def get_arrivals_cached():
    global _cache_time, _cached_arrivals
    if time.time() - _cache_time > CACHE_TTL:
        _cached_arrivals = fetch_arrivals()
        _cache_time = time.time()
        print(f"[{time.strftime('%H:%M:%S')}] Refreshed: {_cached_arrivals} min")
    return _cached_arrivals


# ── HTTP handler ──────────────────────────────────────────────────────────────

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != "/arrivals":
            self.send_response(404)
            self.end_headers()
            return
        try:
            arrivals = get_arrivals_cached()
            body = json.dumps(arrivals).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", len(body))
            self.end_headers()
            self.wfile.write(body)
        except Exception as e:
            print(f"Error: {e}")
            self.send_response(500)
            self.end_headers()
            self.wfile.write(str(e).encode())

    def log_message(self, fmt, *args):
        pass   # suppress per-request logs; we print on cache refresh


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print(f"C Train server — stop {STOP_ID}, route {ROUTE_ID}")
    print(f"Listening on http://0.0.0.0:{PORT}/arrivals")
    HTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
