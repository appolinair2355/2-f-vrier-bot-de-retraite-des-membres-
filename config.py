"""
Bot Telegram Multi-Canaux - Gestionnaire d'Accès Temporaire
Configuration centralisée pour plusieurs canaux indépendants
"""

import os

# ═══════════════════════════════════════════════════════════════
# IDENTIFIANTS API TELEGRAM (Globaux)
# ═══════════════════════════════════════════════════════════════
API_ID = int(os.getenv("API_ID", "29177661"))
API_HASH = os.getenv("API_HASH", "a8639172fa8d35dbfd8ea46286d349ab")
BOT_TOKEN = os.getenv("BOT_TOKEN", "123456789:ABCdefGHIjklMNOpqrSTUvwxyz")

# ═══════════════════════════════════════════════════════════════
# CONFIGURATION SERVEUR
# ═══════════════════════════════════════════════════════════════
PORT = int(os.getenv("PORT", "10000"))

# ═══════════════════════════════════════════════════════════════
# CONSTANTES
# ═══════════════════════════════════════════════════════════════
MIN_DURATION_HOURS = 1
MAX_DURATION_HOURS = 750
DATA_FILE = "channels_data.json"
SESSION_FILE = "bot_multi.session"
CHECK_INTERVAL = 60  # Vérifier toutes les minutes

# ═══════════════════════════════════════════════════════════════
# SUPER ADMIN (Créateur du bot - a accès à tout)
# ═══════════════════════════════════════════════════════════════
SUPER_ADMIN_ID = int(os.getenv("SUPER_ADMIN_ID", "1190237801"))
