import os


BOT_TOKEN: str = os.environ.get("DISCORD_TOKEN", "")

GUILD_ID: int = 1525603628235362354  # ID deines Servers "zen arcade"

# -------------------------------------------------------
# Admin-/Staff-Rollen
# -------------------------------------------------------

# Für Prefix-Commands (!selfroles, !cute_role, !set) via commands.has_any_role(*ADMIN_ROLES).
ADMIN_ROLES: tuple[int, ...] = (1531365140627456000, 1525603628339957945, 1531374771474923592)


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

MESSAGE_LOG_CHANNEL_ID: int = 1525603629929599154
MEMBER_LOG_CHANNEL_ID: int = 1529211146748428449
MOD_LOG_CHANNEL_ID: int = 1529211176809136208


# -------------------------------------------------------
# Media-Threads (modules/media_threads.py)
# -------------------------------------------------------

MEDIA_CHANNEL_ID_1: int = 1525603629141200932
SELFIE_CHANNEL_ID_1: int = 1525603629321683005

# In diesem Channel wird kein Attachment verlangt (reiner Text erlaubt),
# aber trotzdem unter jeder Nachricht ein Thread erstellt.

VORSTELLUNG_CHANNEL_ID_1: int = 1525603629321683006
QOTD_CHANNEL_ID: int = 1544341620542017646  # Question of the Day