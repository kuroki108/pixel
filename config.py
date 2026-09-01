import os


BOT_TOKEN: str = os.environ.get("DISCORD_TOKEN", "")

GUILD_ID: int = 1525603628235362354  # ID deines Servers "zen arcade"

# -------------------------------------------------------
# Admin-/Staff-Rollen
# -------------------------------------------------------

# Für Prefix-Commands (!selfroles, !cute_role, !set) via commands.has_any_role(*ADMIN_ROLES).
ADMIN_ROLES: tuple[int, ...] = (1531365140627456000, 1525603628339957945, 1531374771474923592)

# Für das Ticket-System (modules/ticket_system/permissions.py).
ADMIN_ROLE_ID: int = 1525603628339957945

# -------------------------------------------------------
# Ticket-System
# -------------------------------------------------------

SUPPORT_CATEGORY_ID: int = 1525603628977619062       # Kategorie für Support-Tickets
APPLICATION_CATEGORY_ID: int = 1525603628977619062   # Kategorie für Bewerbungs-Tickets

SUPPORT_STAFF_ROLE_ID: int = 1525603628339957943
APPLICATION_STAFF_ROLE_ID: int = 1525603628339957943

TRANSCRIPT_LOG_CHANNEL_ID: int = 1525603630256750789

MAX_OPEN_SUPPORT_TICKETS_PER_USER: int = 3
MAX_OPEN_APPLICATION_TICKETS_PER_USER: int = 1

# Präfix für automatisch generierte Kanalnamen
SUPPORT_CHANNEL_PREFIX: str = "support"
APPLICATION_CHANNEL_PREFIX: str = "bewerbung"

# Emojis für Panel-Buttons (frei anpassbar)
EMOJI_OPEN_TICKET = "🎫"
EMOJI_CLAIM = "🙋"
EMOJI_DELETE = "🗑️"
EMOJI_ADD_USER = "➕"
EMOJI_REMOVE_USER = "➖"
EMOJI_SUPPORTER = "🛠️"

# Serverfarbe für Embeds (Hex als int, z. B. 0x5865F2)
EMBED_COLOR: int = 0x2B2D31

# -------------------------------------------------------
# Onboarding (modules/onboarding.py)
# -------------------------------------------------------

WELCOME_CHANNEL_ID: int = 1525603628977619056

# Rollen, die neuen Mitgliedern automatisch bei Beitritt vergeben werden.
ONBOARDING_ROLE_IDS: list[int] = [
    1525603628318982325,  # Special
    1525603628298141788,  # About me
    1525603628256329917,  # Pings
    1525603628256329909,  # Gaming
    1527265648764522517,  # Asthatics
    1525603628298141789,  # Member
]

# -------------------------------------------------------
# Counting-Game (modules/counting.py)
# -------------------------------------------------------

COUNTING_CHANNEL_ID: int = 1525603629548179608

# -------------------------------------------------------
# Mod-/Audit-Log (modules/log.py)
# -------------------------------------------------------

MESSAGE_LOG_CHANNEL_ID: int = 1525603629929599154   # edits / deletes
MEMBER_LOG_CHANNEL_ID: int = 1529211146748428449    # join / leave / kick
MOD_LOG_CHANNEL_ID: int = 1529211176809136208       # ban / unban / timeout / mute

# -------------------------------------------------------
# Geburtstage (modules/birthday.py)
# -------------------------------------------------------

BIRTHDAY_CHANNEL_ID: int = 1525603629321683007

# -------------------------------------------------------
# Media-Threads (modules/media_threads.py)
# -------------------------------------------------------

MEDIA_CHANNEL_ID_1: int = 1525603629141200932
SELFIE_CHANNEL_ID_1: int = 1525603629321683005
# In diesem Channel wird kein Attachment verlangt (reiner Text erlaubt),
# aber trotzdem unter jeder Nachricht ein Thread erstellt.
VORSTELLUNG_CHANNEL_ID_1: int = 1525603629321683006
QOTD_CHANNEL_ID: int = 1544341620542017646  # Question of the Day

# -------------------------------------------------------
# Leveling (modules/lvl_system/cogs/leveling.py)
# -------------------------------------------------------

# Channels, in denen keine Text-/Voice-XP vergeben wird.
NO_TEXT_XP_CHANNEL_IDS: set[int] = {1525603629548179608, 1539262663404683384}
NO_VOICE_XP_CHANNEL_IDS: set[int] = {1525603629749240071, 1525603629929599151}

# -------------------------------------------------------
# Free Games (modules/free_games/)
# -------------------------------------------------------

FREEGAMES_CHANNEL_ID: int = 1544301732463382599

# Rolle, die bei neuen automatisch geposteten Angeboten gepingt wird.
FREEGAMES_PING_ROLE_ID: int = 1544301924973674578

FREEGAMES_CHECK_INTERVAL_MINUTES: int = 30
