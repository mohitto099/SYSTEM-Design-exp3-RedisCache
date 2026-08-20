import http.server
import socketserver
import os
import json
import time
import redis

PORT = 8000
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
CACHE_TTL = 60  # Cache key expiration time in seconds

# Initialize Redis Connection
cache = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)


def simulated_database_query(user_id):
    """Simulates an expensive database query (JOINs across posts, users, likes)."""
    time.sleep(0.200)  # 200ms DB processing delay
    return [
        {"post_id": 101, "author": "Alice", "content": "System design with Redis!", "timestamp": "10:00 AM"},
        {"post_id": 102, "author": "Bob", "content": "Docker Desktop setup complete.", "timestamp": "10:05 AM"},
        {"post_id": 103, "author": "Charlie", "content": "Cache-Aside pattern yields 60x speedup.", "timestamp": "10:10 AM"}
    ]


class SocialFeedHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        start_time = time.time()
        path = self.path

        # ---------------------------------------------------------------
        # ENDPOINT 1: Direct Uncached Database Access
        # ---------------------------------------------------------------
        if path == "/feed/uncached":
            feed_data = simulated_database_query(user_id=101)
            elapsed_ms = (time.time() - start_time) * 1000
            response = {
                "source": "PRIMARY_DATABASE",
                "latency_ms": round(elapsed_ms, 2),
                "feed": feed_data
            }
            self._send_json(200, response)

        # ---------------------------------------------------------------
        # ENDPOINT 2: Cache-Aside Pattern Implementation
        # ---------------------------------------------------------------
        elif path == "/feed/cached":
            cache_key = "feed:user_101"
            cached_feed = cache.get(cache_key)
            if cached_feed:
                # --- CACHE HIT ---
                elapsed_ms = (time.time() - start_time) * 1000
                response = {
                    "source": "REDIS_CACHE_HIT",
                    "latency_ms": round(elapsed_ms, 2),
                    "feed": json.loads(cached_feed)
                }
            else:
                # --- CACHE MISS ---
                feed_data = simulated_database_query(user_id=101)
                # Write to Redis with expiration (TTL)
                cache.setex(cache_key, CACHE_TTL, json.dumps(feed_data))
                elapsed_ms = (time.time() - start_time) * 1000
                response = {
                    "source": "DATABASE_MISS_STORED_TO_CACHE",
                    "latency_ms": round(elapsed_ms, 2),
                    "feed": feed_data
                }
            self._send_json(200, response)

        # ---------------------------------------------------------------
        # ENDPOINT 3: Cache Invalidation (Flush)
        # ---------------------------------------------------------------
        elif path == "/cache/flush":
            cache.flushall()
            self._send_json(200, {"status": "Cache Flushed Successfully"})

        else:
            self._send_json(404, {"error": "Endpoint not found"})

    def _send_json(self, status_code, payload):
        self.send_response(status_code)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(payload).encode('utf-8'))

    def log_message(self, format, *args):
        return  # Suppress default HTTP logs


if __name__ == "__main__":
    print(f"Social Feed API active on port {PORT}...")
    print(f"Connecting to Redis at {REDIS_HOST}:{REDIS_PORT}...")
    with socketserver.TCPServer(("", PORT), SocialFeedHandler) as httpd:
        httpd.serve_forever()
