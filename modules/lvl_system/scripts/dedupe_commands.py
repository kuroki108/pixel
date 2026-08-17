"""Delete duplicate slash-commands (same name) globally and for DEV_GUILD_ID.

Requires `DISCORD_TOKEN` env var to be set.
"""
import os
import sys
import requests
from collections import defaultdict

API = "https://discord.com/api/v10"


def get_headers(token: str):
    return {"Authorization": f"Bot {token}"}


def get_app_id(token: str) -> str:
    r = requests.get(f"{API}/oauth2/applications/@me", headers=get_headers(token))
    r.raise_for_status()
    return r.json()["id"]


def list_commands(app_id: str, token: str, guild_id: str | None = None):
    h = get_headers(token)
    if guild_id:
        url = f"{API}/applications/{app_id}/guilds/{guild_id}/commands"
    else:
        url = f"{API}/applications/{app_id}/commands"
    r = requests.get(url, headers=h)
    r.raise_for_status()
    return r.json()


def delete_command(app_id: str, token: str, command_id: str, guild_id: str | None = None):
    h = get_headers(token)
    if guild_id:
        url = f"{API}/applications/{app_id}/guilds/{guild_id}/commands/{command_id}"
    else:
        url = f"{API}/applications/{app_id}/commands/{command_id}"
    r = requests.delete(url, headers=h)
    r.raise_for_status()


def dedupe(app_id: str, token: str, guild_id: str | None = None):
    cmds = list_commands(app_id, token, guild_id)
    by_name = defaultdict(list)
    for c in cmds:
        by_name[c.get("name")].append(c)

    removed = 0
    for name, items in by_name.items():
        if len(items) <= 1:
            continue
        # keep the first, delete the rest
        to_delete = items[1:]
        for d in to_delete:
            try:
                delete_command(app_id, token, d["id"], guild_id)
                print(f"Deleted {('guild ' + guild_id) if guild_id else 'global'} command {d['id']} ({name})")
                removed += 1
            except Exception as e:
                print("Failed to delete", d.get("id"), e)
    return removed


def main():
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        print("Missing DISCORD_TOKEN env var")
        sys.exit(2)

    app_id = get_app_id(token)

    total_removed = 0

    print("Checking global commands...")
    total_removed += dedupe(app_id, token, guild_id=None)

    dev_gid = os.getenv("DEV_GUILD_ID")
    if dev_gid:
        print(f"Checking dev guild {dev_gid} commands...")
        total_removed += dedupe(app_id, token, guild_id=dev_gid)

    print(f"Done. Removed {total_removed} duplicate command(s).")


if __name__ == "__main__":
    main()
