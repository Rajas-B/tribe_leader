
# app/runtime/redis_persistence.py
from redis import Redis
from langgraph.checkpoint.redis import RedisSaver

def build_checkpointer():
    client = Redis(host="localhost", port=6379, decode_responses=False)
    checkpointer = RedisSaver(redis_client=client)
    checkpointer.setup()   # important: init indices once [2](https://outlook.office365.com/owa/?ItemID=AQMkAGE0YWVmOGYyLWY5NTQtNDEyNS1hZWY5LTNiZDdmNmU4Zjg2MQBGAAADEqxKCnJmS0yRBtvKGl3H7QcAGwr1kfcUFUSxiA7l2%2fZcwQAAAgEMAAAArGWcXW6p5EmPZe9qtiGYhAACVTGgxQAAAA%3d%3d&exvsurl=1&viewmodel=ReadMessageItem)[9](https://outlook.office365.com/owa/?ItemID=AQMkAGE0YWVmOGYyLWY5NTQtNDEyNS1hZWY5LTNiZDdmNmU4Zjg2MQBGAAADEqxKCnJmS0yRBtvKGl3H7QcAGwr1kfcUFUSxiA7l2%2fZcwQAAAgEMAAAArGWcXW6p5EmPZe9qtiGYhAACzvlUcgAAAA%3d%3d&exvsurl=1&viewmodel=ReadMessageItem)
    return checkpointer
