import json
import os
from typing import Optional

_DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "tickets.json")


class TicketDatabase:
    def __init__(self, path: str):
        self._path = path
        self._data: dict[str, dict] = self._load()

    def _load(self) -> dict:
        if os.path.exists(self._path):
            with open(self._path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def _save(self):
        os.makedirs(os.path.dirname(self._path), exist_ok=True)
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2, ensure_ascii=False)

    def get(self, ticket_id: str) -> Optional[dict]:
        return self._data.get(str(ticket_id))

    def set(self, ticket_id: str, data: dict):
        self._data[str(ticket_id)] = data
        self._save()

    def update(self, ticket_id: str, fields: dict):
        self._data.setdefault(str(ticket_id), {}).update(fields)
        self._save()

    def delete(self, ticket_id: str):
        self._data.pop(str(ticket_id), None)
        self._save()

    def all(self) -> dict[str, dict]:
        return dict(self._data)

    def next_id(self) -> int:
        return max((int(k) for k in self._data), default=0) + 1

    def find_open(self, user_id: int, guild_id: int) -> Optional[dict]:
        for tid, tdata in self._data.items():
            if (str(tdata.get("user_id")) == str(user_id)
                    and str(tdata.get("guild_id")) == str(guild_id)
                    and tdata.get("status") == "open"):
                return {**tdata, "_id": tid}
        return None


db = TicketDatabase(_DB_PATH)
