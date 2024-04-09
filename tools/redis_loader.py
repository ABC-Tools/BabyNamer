import logging
import os
import redis

from app.lib.common import Gender

redis_host = os.environ.get("REDISHOST", "10.49.86.211")
redis_port = int(os.environ.get("REDISPORT", 6379))
redis_client = redis.StrictRedis(host=redis_host, port=redis_port, charset="utf-8", decode_responses=True)

