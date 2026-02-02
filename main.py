"""
Bot Telegram Multi-Canaux - Gestionnaire d'Accès Temporaire
Gère plusieurs canaux privés indépendamment avec leurs propres admins
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from aiohttp import web
from telethon import TelegramClient, events
from telethon.tl.functions.channels import InviteToChannel, EditBanned
from telethon.tl.types import ChatBannedRights
from telethon.errors import UserPrivacyRestrictError, UserNotMutualContactError

from config import (
    API_ID, API_HASH, BOT_TOKEN, PORT, MIN_DURATION_HOURS, MAX_DURATION_HOURS,
    DATA_FILE, SESSION_FILE, CHECK_INTERVAL, SUPER_ADMIN_ID
)

# Configuration du logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════
# VARIABLES GLOBALES
# ═══════════════════════════════════════════════════════════════

# Formulaires en cours (par utilisateur)
# {user_id: {"step": "...", "channel_id": "...", "data": {...}}}
pending_users = {}

# Étapes de création/modification de canal (par admin)
# {admin_id: {"step": 1|2|3|4, "action": "create|edit", "channel_id": "...", "data": {...}}}
channel_steps = {}

# Client Telethon
bot = TelegramClient(SESSION_FILE, API_ID, API_HASH)

# ═══════════════════════════════════════════════════════════════
# FONCTIONS DE GESTION DES DONNÉES
# ═══════════════════════════════════════════════════════════════

def load_data():
    """Charge les données depuis le fichier JSON"""
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        initial_data = {
            "channels": {},  # {channel_id: {name, link, admins, members, created_at}}
            "global_admins": [SUPER_ADMIN_ID]  # Admins qui peuvent tout gérer
        }
        save_data(initial_data)
        return initial_data
    except json.JSONDecodeError:
        logger.error("Erreur de lecture JSON")
        initial_data = {"channels": {}, "global_admins": [SUPER_ADMIN_ID]}
        save_data(initial_data)
        return initial_data


def save_data(data):
    """Sauvegarde les données dans le fichier JSON"""
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def format_time_remaining(seconds):
    """Formate le temps restant"""
    if seconds <= 0:
        return "Expiré"
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    if hours >= 24:
        days = hours // 24
        remaining_hours = hours % 24
        if remaining_hours > 0:
            return f"{days}j {remaining_hours}h"
        return f"{days}j"
    elif hours > 0:
        return f"{hours}h {minutes}m" if minutes > 0 else f"{hours}h"
    return f"{minutes}m"


def is_super_admin(user_id):
    """Vérifie si l'utilisateur est le super admin"""
    data = load_data()
    return user_id == SUPER_ADMIN_ID or user_id in data.get("global_admins", [])


def is_channel_admin(user_id, channel_id):
    """Vérifie si l'utilisateur est admin d'un canal spécifique"""
    data = load_data()
    if is_super_admin(user_id):
        return True
    channel = data.get("channels", {}).get(str(channel_id))
    if channel:
        return user_id in channel.get("admins", [])
    return False


def get_user_channels(user_id):
    """Retourne la liste des canaux où l'utilisateur est admin"""
    data = load_data()
    if is_super_admin(user_id):
        return list(data.get("channels", {}).keys())
    
    user_channels = []
    for channel_id, channel_data in data.get("channels", {}).items():
        if user_id in channel_data.get("admins", []):
            user_channels.append(channel_id)
    return user_channels


def get_channel_info(channel_id):
    """Retourne les infos d'un canal"""
    data = load_data()
    return data.get("channels", {}).get(str(channel_id))


# ═══════════════════════════════════════════════════════════════
# SERVEUR WEB KEEP-ALIVE
# ═══════════════════════════════════════════════════════════════

async def handle(request):
    data = load_data()
    channels_count = len(data.get("channels", {}))
    total_members = sum(len(ch.get("members", {})) for ch in data.get("channels", {}).values())
    return web.Response(text=f"🤖 Bot Multi-Canaux - {channels_count} canal(aux) - {total_members} membre(s)")


async def start_web_server():
    app = web.Application()
    app.router.add_get('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', PORT)
    await site.start()
    logger.info(f"🌐 Serveur web démarré sur le port {PORT}")


# ═══════════════════════════════════════════════════════════════
# TÂCHE DE VÉRIFICATION DES EXPIRATIONS (Multi-canaux)
# ═══════════════════════════════════════════════════════════════

async def check_expirations():
    """Vérifie et supprime les membres expirés de tous les canaux"""
    while True:
        try:
            data = load_data()
            current_time = int(datetime.now().timestamp())
            
            for channel_id_str, channel_data in data.get("channels", {}).items():
                channel_id = int(channel_id_str)
                members_to_remove = []
                
                for user_id_str, member_data in channel_data.get("members", {}).items():
                    user_id = int(user_id_str)
                    expires_at = member_data.get("expires_at", 0)
                    
                    if expires_at <= current_time:
                        members_to_remove.append((user_id, user_id_str))
                
                # Supprimer les membres expirés
                for user_id, user_id_str in members_to_remove:
                    try:
                        await bot(EditBanned(
                            channel_id,
                            user_id,
                            ChatBannedRights(until_date=None, view_messages=True)
                        ))
                        
                        del channel_data["members"][user_id_str]
                        
                        # Notifier l'utilisateur
                        try:
                            await bot.send_message(
                                user_id,
                                f"⏰ **Votre accès a expiré.**\n\n"
                                f"Canal: {channel_data.get('name', 'Inconnu')}\n"
                                f"Pour renouveler, contactez un administrateur."
                            )
                        except:
                            pass
                        
                        logger.info(f"Membre {user_id} retiré du canal {channel_id}")
                        
                    except Exception as e:
                        logger.error(f"Erreur retrait {user_id} de {channel_id}: {e}")
            
            save_data(data)
            
        except Exception as e:
            logger.error(f"Erreur check_expirations: {e}")
        
        await asyncio.sleep(CHECK_INTERVAL)


# ═══════════════════════════════════════════════════════════════
# CLAVIERS INLINE (Boutons)
# ═══════════════════════════════════════════════════════════════

def get_main_menu_keyboard(user_id):
    """Retourne le clavier du menu principal"""
    from telethon import Button
    
    if is_super_admin(user_id):
        return [
            [Button.inline("📋 Mes Canaux", b"my_channels")],
            [Button.inline("➕ Créer un Canal", b"create_channel")],
            [Button.inline("❓ Aide", b"help")]
        ]
    
    channels = get_user_channels(user_id)
    if channels:
        return [
            [Button.inline("📋 Mes Canaux", b"my_channels")],
            [Button.inline("❓ Aide", b"help")]
        ]
    
    return [[Button.inline("❓ Aide", b"help")]]


def get_channels_keyboard(user_id):
    """Retourne le clavier avec la liste des canaux"""
    from telethon import Button
    
    data = load_data()
    buttons = []
    
    if is_super_admin(user_id):
        channels = data.get("channels", {})
    else:
        channels = {k: v for k, v in data.get("channels", {}).items() 
                   if user_id in v.get("admins", [])}
    
    for channel_id, channel_data in channels.items():
        name = channel_data.get("name", f"Canal {channel_id}")
        member_count = len(channel_data.get("members", {}))
        buttons.append([Button.inline(
            f"{name} ({member_count} membres)", 
            f"channel_{channel_id}".encode()
        )])
    
    buttons.append([Button.inline("🔙 Retour", b"main_menu")])
    return buttons


def get_channel_actions_keyboard(channel_id, user_id):
    """Retourne le clavier des actions pour un canal"""
    from telethon import Button
    
    buttons = [
        [Button.inline("📊 Statistiques", f"stats_{channel_id}".encode())],
        [Button.inline("👥 Liste des membres", f"list_{channel_id}".encode())],
        [Button.inline("⚙️ Paramètres", f"settings_{channel_id}".encode())],
        [Button.inline("🔗 Obtenir le lien", f"link_{channel_id}".encode())]
    ]
    
    if is_super_admin(user_id) or is_channel_admin(user_id, channel_id):
        buttons.insert(2, [Button.inline("➕ Ajouter un admin", f"addadmin_{channel_id}".encode())])
        buttons.insert(3, [Button.inline("🗑️ Purge", f"purge_{channel_id}".encode())])
    
    buttons.append([Button.inline("🔙 Retour", b"my_channels")])
    return buttons


# ═══════════════════════════════════════════════════════════════
# GESTIONNAIRE DE COMMANDES
# ═══════════════════════════════════════════════════════════════

@bot.on(events.NewMessage(pattern='/start'))
async def handle_start(event):
    """Menu principal"""
    user_id = event.sender_id
    
    await event.respond(
        "🤖 **Bot Multi-Canaux - Gestionnaire d'Accès**\n\n"
        "Bienvenue! Ce bot vous permet de gérer l'accès temporaire "
        "à plusieurs canaux privés.\n\n"
        "👤 **Votre ID:** `{}`\n".format(user_id),
        buttons=get_main_menu_keyboard(user_id)
    )


@bot.on(events.CallbackQuery)
async def handle_callback(event):
    """Gère les clics sur les boutons"""
    user_id = event.sender_id
    data = event.data.decode()
    
    if data == "main_menu":
        await event.edit(
            "🤖 **Menu Principal**\n\n"
            "Sélectionnez une option:",
            buttons=get_main_menu_keyboard(user_id)
        )
    
    elif data == "my_channels":
        channels = get_user_channels(user_id)
        if not channels and not is_super_admin(user_id):
            await event.answer("❌ Vous n'avez accès à aucun canal.", alert=True)
            return
        
        await event.edit(
            "📋 **Mes Canaux**\n\n"
            "Sélectionnez un canal:",
            buttons=get_channels_keyboard(user_id)
        )
    
    elif data == "create_channel":
        if not is_super_admin(user_id):
            await event.answer("❌ Accès refusé.", alert=True)
            return
        
        channel_steps[user_id] = {"step": 1, "action": "create", "data": {}}
        await event.edit(
            "➕ **Créer un nouveau canal**\n\n"
            "**Étape 1/4:** Entrez l'ID du canal Telegram\n"
            "(Format: `-1001234567890`)\n\n"
            "💡 *Ajoutez* @RawDataBot *à votre canal pour obtenir l'ID*"
        )
    
    elif data.startswith("channel_"):
        channel_id = data.replace("channel_", "")
        channel_info = get_channel_info(channel_id)
        
        if not channel_info:
            await event.answer("❌ Canal non trouvé.", alert=True)
            return
        
        if not is_super_admin(user_id) and not is_channel_admin(user_id, channel_id):
            await event.answer("❌ Accès refusé.", alert=True)
            return
        
        member_count = len(channel_info.get("members", {}))
        admin_count = len(channel_info.get("admins", []))
        
        await event.edit(
            f"📢 **{channel_info.get('name', 'Canal')}**\n\n"
            f"🆔 ID: `{channel_id}`\n"
            f"👥 Membres: {member_count}\n"
            f"👤 Admins: {admin_count}\n"
            f"🔗 Lien: {channel_info.get('link', 'Non défini')}\n\n"
            f"🕐 Créé le: {channel_info.get('created_at', 'Inconnu')}",
            buttons=get_channel_actions_keyboard(channel_id, user_id)
        )
    
    elif data.startswith("stats_"):
        channel_id = data.replace("stats_", "")
        channel_info = get_channel_info(channel_id)
        
        if not channel_info:
            return
        
        members = channel_info.get("members", {})
        total = len(members)
        active = sum(1 for m in members.values() if m.get("expires_at", 0) > datetime.now().timestamp())
        expired = total - active
        
        await event.edit(
            f"📊 **Statistiques - {channel_info.get('name')}**\n\n"
            f"👥 Total membres: {total}\n"
            f"🟢 Accès actif: {active}\n"
            f"🔴 Expirés: {expired}\n\n"
            f"👤 Admins: {len(channel_info.get('admins', []))}",
            buttons=[[Button.inline("🔙 Retour", f"channel_{channel_id}".encode())]]
        )
    
    elif data.startswith("list_"):
        channel_id = data.replace("list_", "")
        channel_info = get_channel_info(channel_id)
        
        if not channel_info:
            return
        
        members = channel_info.get("members", {})
        current_time = int(datetime.now().timestamp())
        
        if not members:
            await event.edit(
                "📋 **Aucun membre**\n\n"
                "Ce canal n'a pas encore de membres.",
                buttons=[[Button.inline("🔙 Retour", f"channel_{channel_id}".encode())]]
            )
            return
        
        message = f"📋 **Membres - {channel_info.get('name')}**\n\n"
        
        for user_id_str, member in members.items():
            time_left = member.get("expires_at", 0) - current_time
            status = "🟢" if time_left > 0 else "🔴"
            time_str = format_time_remaining(time_left)
            
            message += (
                f"{status} **{member.get('prenom', '?')} {member.get('nom', '?')}**\n"
                f"   🆔 `{user_id_str}` | 🌍 {member.get('pays', '?')}\n"
                f"   ⏳ {time_str}\n\n"
            )
        
        await event.edit(
            message,
            buttons=[[Button.inline("🔙 Retour", f"channel_{channel_id}".encode())]]
        )
    
    elif data.startswith("settings_"):
        channel_id = data.replace("settings_", "")
        channel_info = get_channel_info(channel_id)
        
        if not is_super_admin(user_id) and not is_channel_admin(user_id, channel_id):
            await event.answer("❌ Accès refusé.", alert=True)
            return
        
        channel_steps[user_id] = {"step": 1, "action": "edit", "channel_id": channel_id, "data": {}}
        
        await event.edit(
            f"⚙️ **Paramètres - {channel_info.get('name')}**\n\n"
            f"ID actuel: `{channel_id}`\n"
            f"Nom: {channel_info.get('name')}\n"
            f"Lien: {channel_info.get('link')}\n\n"
            "**Étape 1/3:** Entrez le nouveau nom du canal:\n"
            "(ou envoyez `.` pour garder l'actuel)"
        )
    
    elif data.startswith("link_"):
        channel_id = data.replace("link_", "")
        channel_info = get_channel_info(channel_id)
        
        if not channel_info:
            return
        
        await event.edit(
            f"🔗 **Lien d'accès - {channel_info.get('name')}**\n\n"
            f"{channel_info.get('link', 'Lien non défini')}\n\n"
            "Partagez ce lien avec les utilisateurs pour qu'ils puissent "
            "rejoindre le canal après validation.",
            buttons=[[Button.inline("🔙 Retour", f"channel_{channel_id}".encode())]]
        )
    
    elif data.startswith("purge_"):
        channel_id = data.replace("purge_", "")
        
        if not is_super_admin(user_id) and not is_channel_admin(user_id, channel_id):
            await event.answer("❌ Accès refusé.", alert=True)
            return
        
        await event.edit(
            "⚠️ **Confirmer la purge?**\n\n"
            "Tous les membres seront retirés du canal.\n"
            "Cette action est irréversible!",
            buttons=[
                [Button.inline("✅ Confirmer", f"confirm_purge_{channel_id}".encode())],
                [Button.inline("❌ Annuler", f"channel_{channel_id}".encode())]
            ]
        )
    
    elif data.startswith("confirm_purge_"):
        channel_id = data.replace("confirm_purge_", "")
        channel_info = get_channel_info(channel_id)
        
        if not channel_info:
            return
        
        data_db = load_data()
        members_removed = 0
        
        for user_id_str in list(channel_info.get("members", {}).keys()):
            uid = int(user_id_str)
            
            if uid in data_db.get("global_admins", []):
                continue
            
            try:
                await bot(EditBanned(
                    int(channel_id),
                    uid,
                    ChatBannedRights(until_date=None, view_messages=True)
                ))
                
                try:
                    await bot.send_message(
                        uid,
                        f"⚠️ **Votre accès au canal '{channel_info.get('name')}' a été révoqué.**\n\n"
                        "Le canal a été purgé par un administrateur."
                    )
                except:
                    pass
                
                members_removed += 1
            except Exception as e:
                logger.error(f"Erreur purge {uid}: {e}")
        
        # Vider les membres
        data_db["channels"][channel_id]["members"] = {}
        save_data(data_db)
        
        await event.edit(
            f"✅ **Purge terminée!**\n\n"
            f"🗑️ {members_removed} membre(s) retiré(s)",
            buttons=[[Button.inline("🔙 Retour", f"channel_{channel_id}".encode())]]
        )
    
    elif data.startswith("addadmin_"):
        channel_id = data.replace("addadmin_", "")
        
        if not is_super_admin(user_id) and not is_channel_admin(user_id, channel_id):
            await event.answer("❌ Accès refusé.", alert=True)
            return
        
        channel_steps[user_id] = {"step": "add_admin", "channel_id": channel_id, "data": {}}
        
        await event.edit(
            "➕ **Ajouter un administrateur**\n\n"
            "Envoyez l'ID Telegram de l'utilisateur à ajouter comme admin:\n"
            "(L'utilisateur doit avoir démarré le bot avec /start)\n\n"
            "💡 L'utilisateur peut obtenir son ID avec @userinfobot"
        )
    
    elif data == "help":
        is_admin = is_super_admin(user_id) or get_user_channels(user_id)
        
        help_text = (
            "📖 **Aide du Bot Multi-Canaux**\n\n"
            
            "**👤 Utilisateur:**\n"
            "• `/start` - Menu principal\n"
            "• `/register <canal_id>` - S'inscrire à un canal\n\n"
        )
        
        if is_admin:
            help_text += (
                "**👑 Administrateur:**\n"
                "• `/validate <canal_id> <user_id> <heures>` - Valider un membre\n"
                "• `/remove <canal_id> <user_id>` - Retirer un membre\n"
                "• Utilisez les boutons pour plus d'options!\n\n"
            )
        
        help_text += (
            "**❓ Comment ça marche:**\n"
            "1. Un utilisateur s'inscrit avec `/register`\n"
            "2. Vous recevez une notification\n"
            "3. Vous validez avec `/validate`\n"
            "4. Le bot ajoute l'utilisateur au canal\n"
            "5. L'accès expire automatiquement"
        )
        
        await event.edit(help_text, buttons=[[Button.inline("🔙 Retour", b"main_menu")]])


# ═══════════════════════════════════════════════════════════════
# GESTION DES FORMULAIRES (Création/Édition de canal)
# ═══════════════════════════════════════════════════════════════

@bot.on(events.NewMessage)
async def handle_forms(event):
    """Gère les formulaires en cours"""
    user_id = event.sender_id
    text = event.message.text.strip()
    
    # Formulaire de création de canal
    if user_id in channel_steps:
        step_info = channel_steps[user_id]
        action = step_info.get("action")
        step = step_info.get("step")
        
        if action == "create":
            if step == 1:
                # ID du canal
                try:
                    channel_id = int(text)
                    if not str(channel_id).startswith("-100"):
                        await event.respond("❌ L'ID doit commencer par `-100`. Réessayez:")
                        return
                    
                    # Vérifier si le canal existe déjà
                    data = load_data()
                    if str(channel_id) in data.get("channels", {}):
                        await event.respond("❌ Ce canal est déjà enregistré. Réessayez:")
                        return
                    
                    channel_steps[user_id]["data"]["channel_id"] = channel_id
                    channel_steps[user_id]["step"] = 2
                    
                    await event.respond(
                        "✅ ID enregistré!\n\n"
                        "**Étape 2/4:** Entrez le nom du canal:\n"
                        "(Ex: `Canal VIP Premium`)"
                    )
                except ValueError:
                    await event.respond("❌ ID invalide. Entrez un nombre:")
            
            elif step == 2:
                channel_steps[user_id]["data"]["name"] = text
                channel_steps[user_id]["step"] = 3
                
                await event.respond(
                    "✅ Nom enregistré!\n\n"
                    "**Étape 3/4:** Entrez le lien d'invitation:\n"
                    "(Ex: `https://t.me/+u3Ha8i3mHG4yMWQ0`)"
                )
            
            elif step == 3:
                if not text.startswith("https://t.me/"):
                    await event.respond("❌ Le lien doit commencer par `https://t.me/`. Réessayez:")
                    return
                
                channel_steps[user_id]["data"]["link"] = text
                channel_steps[user_id]["step"] = 4
                
                await event.respond(
                    "✅ Lien enregistré!\n\n"
                    "**Étape 4/4:** Entrez l'ID du premier administrateur:\n"
                    "(Votre ID ou celui d'un autre admin)\n\n"
                    "💡 Obtenez votre ID avec @userinfobot"
                )
            
            elif step == 4:
                try:
                    admin_id = int(text)
                    
                    # Créer le canal
                    data = load_data()
                    channel_id = channel_steps[user_id]["data"]["channel_id"]
                    
                    data["channels"][str(channel_id)] = {
                        "name": channel_steps[user_id]["data"]["name"],
                        "link": channel_steps[user_id]["data"]["link"],
                        "admins": [admin_id],
                        "members": {},
                        "created_at": datetime.now().strftime("%d/%m/%Y à %H:%M"),
                        "updated_at": datetime.now().strftime("%d/%m/%Y à %H:%M")
                    }
                    save_data(data)
                    
                    del channel_steps[user_id]
                    
                    await event.respond(
                        "✅ **Canal créé avec succès!**\n\n"
                        f"🆔 ID: `{channel_id}`\n"
                        f"🏷️ Nom: {data['channels'][str(channel_id)]['name']}\n"
                        f"🔗 Lien: {data['channels'][str(channel_id)]['link']}\n"
                        f"👤 Admin: {admin_id}",
                        buttons=get_main_menu_keyboard(user_id)
                    )
                    
                except ValueError:
                    await event.respond("❌ ID invalide. Entrez un nombre:")
        
        elif action == "edit":
            channel_id = step_info.get("channel_id")
            data = load_data()
            
            if step == 1:
                # Nom
                if text != ".":
                    channel_steps[user_id]["data"]["name"] = text
                else:
                    channel_steps[user_id]["data"]["name"] = data["channels"][channel_id]["name"]
                
                channel_steps[user_id]["step"] = 2
                
                await event.respond(
                    "✅ Nom enregistré!\n\n"
                    "**Étape 2/3:** Entrez le nouveau lien:\n"
                    "(ou envoyez `.` pour garder l'actuel)"
                )
            
            elif step == 2:
                # Lien
                if text != ".":
                    if not text.startswith("https://t.me/"):
                        await event.respond("❌ Le lien doit commencer par `https://t.me/`. Réessayez:")
                        return
                    channel_steps[user_id]["data"]["link"] = text
                else:
                    channel_steps[user_id]["data"]["link"] = data["channels"][channel_id]["link"]
                
                channel_steps[user_id]["step"] = 3
                
                await event.respond(
                    "✅ Lien enregistré!\n\n"
                    "**Étape 3/3:** Entrez le nouvel ID du canal:\n"
                    "(ou envoyez `.` pour garder l'actuel)\n\n"
                    "⚠️ *Ne changez l'ID que si vous avez changé de canal Telegram*"
                )
            
            elif step == 3:
                # ID du canal (optionnel)
                if text != ".":
                    try:
                        new_channel_id = int(text)
                        if not str(new_channel_id).startswith("-100"):
                            await event.respond("❌ L'ID doit commencer par `-100`. Réessayez:")
                            return
                        
                        # Déplacer les données vers le nouvel ID
                        old_data = data["channels"].pop(channel_id)
                        old_data["name"] = channel_steps[user_id]["data"]["name"]
                        old_data["link"] = channel_steps[user_id]["data"]["link"]
                        old_data["updated_at"] = datetime.now().strftime("%d/%m/%Y à %H:%M")
                        data["channels"][str(new_channel_id)] = old_data
                        channel_id = str(new_channel_id)
                        
                    except ValueError:
                        await event.respond("❌ ID invalide. Réessayez:")
                        return
                else:
                    data["channels"][channel_id]["name"] = channel_steps[user_id]["data"]["name"]
                    data["channels"][channel_id]["link"] = channel_steps[user_id]["data"]["link"]
                    data["channels"][channel_id]["updated_at"] = datetime.now().strftime("%d/%m/%Y à %H:%M")
                
                save_data(data)
                del channel_steps[user_id]
                
                await event.respond(
                    "✅ **Paramètres mis à jour!**",
                    buttons=get_main_menu_keyboard(user_id)
                )
        
        elif step == "add_admin":
            channel_id = step_info.get("channel_id")
            
            try:
                new_admin_id = int(text)
                
                data = load_data()
                if new_admin_id in data["channels"][channel_id]["admins"]:
                    await event.respond("❌ Cet utilisateur est déjà admin.")
                    return
                
                data["channels"][channel_id]["admins"].append(new_admin_id)
                save_data(data)
                
                del channel_steps[user_id]
                
                await event.respond(
                    f"✅ **Administrateur ajouté!**\n\n"
                    f"🆔 ID: `{new_admin_id}`\n"
                    f"📢 Canal: {data['channels'][channel_id]['name']}",
                    buttons=get_channel_actions_keyboard(channel_id, user_id)
                )
                
            except ValueError:
                await event.respond("❌ ID invalide. Entrez un nombre:")


# ═══════════════════════════════════════════════════════════════
# COMMANDES TEXTE
# ═══════════════════════════════════════════════════════════════

@bot.on(events.NewMessage(pattern='/register'))
async def handle_register(event):
    """Inscription à un canal (par l'utilisateur)"""
    user_id = event.sender_id
    
    # Vérifier si l'utilisateur est déjà membre d'un canal
    data = load_data()
    user_channels = []
    
    for channel_id, channel_data in data.get("channels", {}).items():
        if str(user_id) in channel_data.get("members", {}):
            user_channels.append((channel_id, channel_data))
    
    if user_channels:
        message = "✅ **Vous êtes déjà membre de:**\n\n"
        for ch_id, ch_data in user_channels:
            member_data = ch_data["members"][str(user_id)]
            time_left = member_data.get("expires_at", 0) - int(datetime.now().timestamp())
            time_str = format_time_remaining(time_left)
            message += f"📢 {ch_data.get('name', 'Canal')} - ⏳ {time_str}\n"
        
        await event.respond(message)
        return
    
    # Démarrer l'inscription
    pending_users[user_id] = {"step": "select_channel", "data": {}}
    
    # Lister les canaux disponibles
    channels_list = ""
    for channel_id, channel_data in data.get("channels", {}).items():
        channels_list += f"• `{channel_id}` - {channel_data.get('name', 'Sans nom')}\n"
    
    if not channels_list:
        await event.respond("❌ Aucun canal disponible pour l'inscription.")
        return
    
    await event.respond(
        "📝 **Inscription à un canal**\n\n"
        "Canaux disponibles:\n" + channels_list + "\n"
        "Envoyez l'ID du canal auquel vous voulez vous inscrire:"
    )


@bot.on(events.NewMessage)
async def handle_user_registration(event):
    """Gère le formulaire d'inscription utilisateur"""
    user_id = event.sender_id
    text = event.message.text.strip()
    
    if user_id not in pending_users:
        return
    
    step = pending_users[user_id].get("step")
    
    if step == "select_channel":
        # Vérifier le canal
        try:
            channel_id = text
            data = load_data()
            
            if channel_id not in data.get("channels", {}):
                await event.respond("❌ Canal non trouvé. Vérifiez l'ID:")
                return
            
            # Vérifier si déjà membre
            if str(user_id) in data["channels"][channel_id].get("members", {}):
                await event.respond("✅ Vous êtes déjà membre de ce canal!")
                del pending_users[user_id]
                return
            
            pending_users[user_id]["data"]["channel_id"] = channel_id
            pending_users[user_id]["step"] = "nom"
            
            await event.respond(
                "👤 **Entrez votre Nom :**"
            )
            
        except Exception as e:
            await event.respond(f"❌ Erreur: {str(e)}")
    
    elif step == "nom":
        pending_users[user_id]["data"]["nom"] = text
        pending_users[user_id]["step"] = "prenom"
        await event.respond("👤 **Entrez votre Prénom :**")
    
    elif step == "prenom":
        pending_users[user_id]["data"]["prenom"] = text
        pending_users[user_id]["step"] = "pays"
        await event.respond("🌍 **Entrez votre Pays :**")
    
    elif step == "pays":
        pending_users[user_id]["data"]["pays"] = text
        
        # Récupérer les données
        channel_id = pending_users[user_id]["data"]["channel_id"]
        nom = pending_users[user_id]["data"]["nom"]
        prenom = pending_users[user_id]["data"]["prenom"]
        pays = text
        
        data = load_data()
        channel_info = data["channels"][channel_id]
        
        del pending_users[user_id]
        
        # Envoyer confirmation
        await event.respond(
            "✅ **Inscription terminée!**\n\n"
            f"👤 **{prenom} {nom}**\n"
            f"🌍 {pays}\n"
            f"📢 Canal: {channel_info.get('name', 'Inconnu')}\n\n"
            f"🔗 **Lien du canal:**\n{channel_info.get('link', 'Non défini')}\n\n"
            "⏳ *En attente de validation par un administrateur...*"
        )
        
        # Notifier les admins du canal
        for admin_id in channel_info.get("admins", []):
            try:
                await bot.send_message(
                    admin_id,
                    f"🆕 **Nouvelle inscription**\n\n"
                    f"📢 Canal: {channel_info.get('name')}\n"
                    f"👤 **Nom:** {nom}\n"
                    f"👤 **Prénom:** {prenom}\n"
                    f"🌍 **Pays:** {pays}\n"
                    f"🆔 **ID:** `{user_id}`\n\n"
                    f"⚠️ Définissez la durée ({MIN_DURATION_HOURS}h-{MAX_DURATION_HOURS}h):\n"
                    f"/validate {channel_id} {user_id} <heures>"
                )
            except Exception as e:
                logger.error(f"Erreur notification admin {admin_id}: {e}")


@bot.on(events.NewMessage(pattern=r'/validate\s+(-?\d+)\s+(\d+)\s+(\d+)'))
async def handle_validate(event):
    """Valide un membre: /validate <channel_id> <user_id> <heures>"""
    user_id = event.sender_id
    
    match = event.pattern_match
    channel_id = match.group(1)
    member_id = int(match.group(2))
    hours = int(match.group(3))
    
    # Vérifier les droits
    if not is_super_admin(user_id) and not is_channel_admin(user_id, channel_id):
        await event.respond("❌ Vous n'êtes pas administrateur de ce canal.")
        return
    
    # Vérifier la durée
    if hours < MIN_DURATION_HOURS or hours > MAX_DURATION_HOURS:
        await event.respond(f"❌ Durée invalide. Entre {MIN_DURATION_HOURS}h et {MAX_DURATION_HOURS}h.")
        return
    
    data = load_data()
    channel_info = data.get("channels", {}).get(channel_id)
    
    if not channel_info:
        await event.respond("❌ Canal non trouvé.")
        return
    
    # Chercher les infos du membre (dans les messages récents de l'admin)
    nom, prenom, pays = "Inconnu", "Inconnu", "Inconnu"
    async for message in bot.iter_messages(event.chat_id, limit=50):
        if message.text and f"🆔 **ID:** `{member_id}`" in message.text:
            lines = message.text.split('\n')
            for line in lines:
                if "Nom:" in line:
                    nom = line.split(":")[1].strip()
                elif "Prénom:" in line:
                    prenom = line.split(":")[1].strip()
                elif "Pays:" in line:
                    pays = line.split(":")[1].strip()
            break
    
    current_time = int(datetime.now().timestamp())
    duration_seconds = hours * 3600
    
    # Ajouter le membre
    data["channels"][channel_id]["members"][str(member_id)] = {
        "nom": nom,
        "prenom": prenom,
        "pays": pays,
        "join_time": current_time,
        "duration": duration_seconds,
        "expires_at": current_time + duration_seconds
    }
    save_data(data)
    
    # Ajouter au canal Telegram
    try:
        await bot(InviteToChannel(int(channel_id), [member_id]))
        
        # Notifier l'utilisateur
        await bot.send_message(
            member_id,
            f"🎉 **Félicitations!**\n\n"
            f"Votre accès à **{channel_info.get('name')}** a été validé!\n"
            f"⏳ Durée: **{hours} heure(s)**\n"
            f"📅 Expire le: {datetime.fromtimestamp(current_time + duration_seconds).strftime('%d/%m/%Y à %H:%M')}\n\n"
            f"🔗 **Rejoignez le canal:** {channel_info.get('link')}"
        )
        
        # Notifier le canal
        try:
            await bot.send_message(
                int(channel_id),
                f"👋 **Nouveau membre!**\n\n"
                f"👤 {prenom} {nom}\n"
                f"🌍 {pays}\n"
                f"⏳ Accès: {hours}h"
            )
        except:
            pass
        
        await event.respond(
            f"✅ **Membre validé!**\n\n"
            f"📢 {channel_info.get('name')}\n"
            f"👤 {prenom} {nom}\n"
            f"🆔 {member_id}\n"
            f"⏳ {hours}h"
        )
        
    except UserPrivacyRestrictError:
        await event.respond("❌ L'utilisateur doit d'abord démarrer le bot avec /start")
    except UserNotMutualContactError:
        await event.respond("❌ L'utilisateur doit d'abord contacter le bot")
    except Exception as e:
        await event.respond(f"❌ Erreur: {str(e)}")


@bot.on(events.NewMessage(pattern=r'/remove\s+(-?\d+)\s+(\d+)'))
async def handle_remove(event):
    """Retire un membre: /remove <channel_id> <user_id>"""
    user_id = event.sender_id
    
    match = event.pattern_match
    channel_id = match.group(1)
    member_id = int(match.group(2))
    
    if not is_super_admin(user_id) and not is_channel_admin(user_id, channel_id):
        await event.respond("❌ Accès refusé.")
        return
    
    data = load_data()
    channel_info = data.get("channels", {}).get(channel_id)
    
    if not channel_info:
        await event.respond("❌ Canal non trouvé.")
        return
    
    if str(member_id) not in channel_info.get("members", {}):
        await event.respond("❌ Membre non trouvé.")
        return
    
    member_data = channel_info["members"][str(member_id)]
    
    try:
        await bot(EditBanned(
            int(channel_id),
            member_id,
            ChatBannedRights(until_date=None, view_messages=True)
        ))
        
        del data["channels"][channel_id]["members"][str(member_id)]
        save_data(data)
        
        try:
            await bot.send_message(
                member_id,
                f"⚠️ **Votre accès à '{channel_info.get('name')}' a été révoqué.**"
            )
        except:
            pass
        
        await event.respond(
            f"✅ **Membre retiré!**\n\n"
            f"📢 {channel_info.get('name')}\n"
            f"👤 {member_data.get('prenom')} {member_data.get('nom')}"
        )
        
    except Exception as e:
        await event.respond(f"❌ Erreur: {str(e)}")


@bot.on(events.NewMessage(pattern='/help'))
async def handle_help_cmd(event):
    """Commande /help"""
    user_id = event.sender_id
    is_admin = is_super_admin(user_id) or get_user_channels(user_id)
    
    help_text = (
        "📖 **Aide du Bot Multi-Canaux**\n\n"
        "**👤 Utilisateur:**\n"
        "• `/start` - Menu principal avec boutons\n"
        "• `/register` - S'inscrire à un canal\n\n"
    )
    
    if is_admin:
        help_text += (
            "**👑 Administrateur:**\n"
            "• `/validate <canal_id> <user_id> <heures>` - Valider\n"
            "• `/remove <canal_id> <user_id>` - Retirer\n"
            "• Utilisez les boutons du menu pour plus d'options!\n\n"
        )
    
    help_text += "Utilisez `/start` pour accéder au menu principal."
    
    await event.respond(help_text)


# ═══════════════════════════════════════════════════════════════
# FONCTION PRINCIPALE
# ═══════════════════════════════════════════════════════════════

async def main():
    logger.info("🤖 Démarrage du bot multi-canaux...")
    
    await start_web_server()
    asyncio.create_task(check_expirations())
    
    await bot.start(bot_token=BOT_TOKEN)
    logger.info("✅ Bot multi-canaux démarré!")
    
    await bot.run_until_disconnected()


if __name__ == "__main__":
    asyncio.run(main())
