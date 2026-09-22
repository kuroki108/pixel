# Pixel

Pixel ist der Discord-Bot des Servers **zen arcade** – gebaut mit [discord.py](https://github.com/Rapptz/discord.py).

## Features

- 👋 **Onboarding** – automatische Rollenvergabe & Willkommens-Embed
- 🔢 **Zählspiel** – Counting-Channel mit Achievements
- 📝 **Mod-Log** – Logging von Message-Edits/-Deletes, Joins/Leaves/Kicks, Bans
- 🧵 **Media-Threads** – automatische Threads für Medien- und Vorstellungsbereiche

## Setup

```bash
git clone <repo-url>
cd pixel
pip install -r requirements.txt
```

Discord-Token hinterlegen:

```bash
cp .env.example .env
# DISCORD_TOKEN=dein_token in der .env eintragen
```

Bot starten:

```bash
python bot.py
```

## Konfiguration

Alle server-spezifischen IDs (Rollen, Kanäle, Kategorien) liegen in [`config.py`](config.py) sowie am Kopf der jeweiligen Module in [`modules/`](modules/). Für den eigenen Server einfach anpassen.

---

