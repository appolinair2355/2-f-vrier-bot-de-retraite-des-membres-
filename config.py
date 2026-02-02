"""
Bot Telegram - Gestionnaire d'Accès Temporaire (Version Render)
Utilise python-telegram-bot (pas besoin de session Telethon)
"""

import os

# ═══════════════════════════════════════════════════════════════
# CONFIGURATION - REMPLACEZ CES VALEURS
# ═══════════════════════════════════════════════════════════════

# Token du bot (obtenu via @BotFather)
BOT_TOKEN = os.getenv("BOT_TOKEN", "VOTRE_TOKEN_ICI")

# Canal privé (ID commence par -100)
CHANNEL_ID = int(os.getenv("CHANNEL_ID", "-1001234567890"))

# Lien d'invitation du canal
CHANNEL_LINK = os.getenv("CHANNEL_LINK", "https://t.me/+VotreLienIci")

# Nom du canal
CHANNEL_NAME = os.getenv("CHANNEL_NAME", "Mon Canal Privé")

# IDs des administrateurs (séparés par des virgules)
# Exemple: "1190237801,1190237802"
ADMINS_STR = os.getenv("ADMINS", "1190237801")
ADMINS = [int(x.strip()) for x in ADMINS_STR.split(",") if x.strip()]

# ═══════════════════════════════════════════════════════════════
# CONFIGURATION SERVEUR
# ═══════════════════════════════════════════════════════════════
PORT = int(os.getenv("PORT", "10000"))

# ═══════════════════════════════════════════════════════════════
# CONSTANTES
# ═══════════════════════════════════════════════════════════════
MIN_DURATION_HOURS = 1
MAX_DURATION_HOURS = 750
DATA_FILE = "members.json"
CHECK_INTERVAL = 60  # Vérifier expirations toutes les 60 secondes
