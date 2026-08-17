# Pixel

Pixel ist der Discord-Bot des Servers **zen arcade** – gebaut mit [discord.py](https://github.com/Rapptz/discord.py).

## Features

- 🎫 **Ticket-System** – Support- und Bewerbungs-Tickets per Panel, inklusive Claim/Close/Transcript/Delete
- 📈 **Level-System** – Text- & Voice-XP, Rangkarten, Leaderboard, konfigurierbar per Slash-Command
- 👋 **Onboarding** – automatische Rollenvergabe & generiertes Willkommensbild
- 🔢 **Zählspiel** – Counting-Channel mit Achievements
- 📝 **Mod-Log** – Logging von Message-Edits/-Deletes, Joins/Leaves/Kicks, Bans
- ⏰ **Bump-Reminder** – erinnert automatisch ans nächste `/bump` bei Disboard
- 🔢 **Number Guessing** – kleines Ratespiel per Slash-Command

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

