import json
import os

_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "config.json")

with open(_CONFIG_PATH, "r", encoding="utf-8") as _f:
    cfg: dict = json.load(_f)
