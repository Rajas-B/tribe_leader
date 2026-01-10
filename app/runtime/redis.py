
# app/runtime/redis.py
from redis import Redis
from langgraph.checkpoint.redis import RedisSaver
from langgraph.store.redis import RedisStore

def build_redis():
    client = Redis(host="localhost", port=6379, decode_responses=False)

    checkpointer = RedisSaver(redis_client=client)
    checkpointer.setup()  # must run once per env [2](https://pypi.org/project/langgraph-checkpoint-redis/)[7](https://bing.com/search?q=langgraph-checkpoint-redis+RedisSaver+setup+example+python)

    store = RedisStore(redis_client=client)
    store.setup()         # optional long-term store; you may keep vector DB separate [6](https://github.com/redis-developer/langgraph-redis)
    return checkpointer, store
