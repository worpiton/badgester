import os, json

devservers = json.loads(os.environ.get("devservers"))
devids = json.loads(os.environ.get("devids"))

bottoken = os.environ.get("bottoken")
roblosecurity = os.environ.get("roblosecurity")