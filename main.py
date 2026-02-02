"""
Bot Telegram - Gestionnaire d'Accès Temporaire (Version Render)
Utilise python-telegram-bot + aiohttp pour le keep-alive
"""

import asyncio
import json
import logging
from datetime import datetime
from aiohttp import web
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, ConversationHandler,
    CallbackQueryHandler, ContextTypes, filters
)

from config import (
    BOT_TOKEN, CHANNEL_ID, CHANNEL_LINK, CHANNEL_NAME, ADMINS, PORT,
    MIN_DURATION_HOURS, MAX_DURATION_HOURS, DATA_FILE, CHECK_INTERVAL
)

# Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# États pour la conversation
NOM, PRENOM, PAYS = range(3)

# ═══════════════════════════════════════════════════════════════
# FONCTIONS DE DONNÉES
# ═══════════════════════════════════════════════════════════════

def load_data():
    """Charge les données JSON"""
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        data = {
            "channel_id": CHANNEL_ID,
            "link": CHANNEL_LINK,
            "link_name": CHANNEL_NAME,
            "link_updated": datetime.now().strftime("%d/%m/%Y à %H:%M"),
            "members": {},
            "pending_validations": {}  # En attente de validation
        }
        save_data(data)
        return data
    except Exception as e:
        logger.error(f"Erreur load_data: {e}")
        return {"members": {}, "pending_validations": {}}


def save_data(data):
    """Sauvegarde les données JSON"""
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def is_admin(user_id):
    """Vérifie si l'utilisateur est admin"""
    return user_id in ADMINS


def format_time_remaining(seconds):
    """Formate le temps restant"""
    if seconds <= 0:
        return "Expiré"
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    if hours >= 24:
        days = hours // 24
        remaining = hours % 24
        return f"{days}j {remaining}h" if remaining else f"{days}j"
    elif hours > 0:
        return f"{hours}h {minutes}m" if minutes else f"{hours}h"
    return f"{minutes}m"


# ═══════════════════════════════════════════════════════════════
# SERVEUR WEB KEEP-ALIVE
# ═══════════════════════════════════════════════════════════════

async def web_handler(request):
    """Handler pour le serveur web"""
    data = load_data()
    members_count = len(data.get("members", {}))
    return web.Response(
        text=f"🤖 Bot Telegram - {CHANNEL_NAME} - {members_count} membre(s) - En ligne!",
        content_type="text/html"
    )


async def start_web_server():
    """Démarre le serveur web"""
    app = web.Application()
    app.router.add_get('/', web_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', PORT)
    await site.start()
    logger.info(f"🌐 Serveur web démarré sur le port {PORT}")


# ═══════════════════════════════════════════════════════════════
# COMMANDES UTILISATEUR
# ═══════════════════════════════════════════════════════════════

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Commande /start"""
    user_id = update.effective_user.id
    
    # Vérifier si déjà membre
    data = load_data()
    if str(user_id) in data.get("members", {}):
        member = data["members"][str(user_id)]
        time_left = member.get("expires_at", 0) - int(datetime.now().timestamp())
        time_str = format_time_remaining(time_left)
        
        keyboard = [[InlineKeyboardButton("🔗 Rejoindre le canal", url=data["link"])]]
        await update.message.reply_text(
            f"✅ **Vous êtes membre!**\n\n"
            f"⏳ Temps restant: {time_str}\n\n"
            f"🔗 **Lien:** {data['link']}",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
        return
    
    # Vérifier si en attente de validation
    if str(user_id) in data.get("pending_validations", {}):
        await update.message.reply_text(
            "⏳ **Inscription en cours...**\n\n"
            "Votre demande est en attente de validation par un administrateur."
        )
        return
    
    # Démarrer l'inscription
    await update.message.reply_text(
        "👋 **Bienvenue!**\n\n"
        "Pour accéder au canal privé, complétez ce formulaire.\n\n"
        "👤 **Entrez votre Nom :**"
    )
    return NOM


async def get_nom(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Récupère le nom"""
    context.user_data["nom"] = update.message.text.strip()
    await update.message.reply_text("👤 **Entrez votre Prénom :**")
    return PRENOM


async def get_prenom(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Récupère le prénom"""
    context.user_data["prenom"] = update.message.text.strip()
    await update.message.reply_text("🌍 **Entrez votre Pays :**")
    return PAYS


async def get_pays(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Récupère le pays et finalise l'inscription"""
    user_id = update.effective_user.id
    context.user_data["pays"] = update.message.text.strip()
    
    nom = context.user_data["nom"]
    prenom = context.user_data["prenom"]
    pays = context.user_data["pays"]
    
    # Sauvegarder dans pending_validations
    data = load_data()
    data["pending_validations"][str(user_id)] = {
        "nom": nom,
        "prenom": prenom,
        "pays": pays,
        "registered_at": datetime.now().strftime("%d/%m/%Y à %H:%M")
    }
    save_data(data)
    
    # Confirmer à l'utilisateur
    await update.message.reply_text(
        "✅ **Inscription terminée!**\n\n"
        f"👤 **{prenom} {nom}**\n"
        f"🌍 {pays}\n\n"
        "⏳ *En attente de validation par un administrateur...*\n\n"
        "Vous recevrez un message dès que votre accès sera validé."
    )
    
    # Notifier les admins
    for admin_id in ADMINS:
        try:
            keyboard = [
                [InlineKeyboardButton(
                    "✅ Valider 24h", 
                    callback_data=f"validate_{user_id}_24"
                )],
                [InlineKeyboardButton(
                    "✅ Valider 48h", 
                    callback_data=f"validate_{user_id}_48"
                )],
                [InlineKeyboardButton(
                    "✅ Valider 7j (168h)", 
                    callback_data=f"validate_{user_id}_168"
                )],
                [InlineKeyboardButton(
                    "❌ Refuser", 
                    callback_data=f"reject_{user_id}"
                )]
            ]
            await context.bot.send_message(
                admin_id,
                f"🆕 **Nouvelle inscription**\n\n"
                f"👤 **Nom:** {nom}\n"
                f"👤 **Prénom:** {prenom}\n"
                f"🌍 **Pays:** {pays}\n"
                f"🆔 **ID:** `{user_id}`\n\n"
                f"⚠️ Cliquez pour valider:",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Erreur notification admin {admin_id}: {e}")
    
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Annule la conversation"""
    await update.message.reply_text("❌ Inscription annulée.")
    return ConversationHandler.END


# ═══════════════════════════════════════════════════════════════
# CALLBACKS (Boutons)
# ═══════════════════════════════════════════════════════════════

async def validate_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gère la validation via bouton"""
    query = update.callback_query
    await query.answer()
    
    if not is_admin(update.effective_user.id):
        await query.edit_message_text("❌ Accès refusé.")
        return
    
    data_parts = query.data.split("_")
    action = data_parts[0]
    user_id = int(data_parts[1])
    
    if action == "reject":
        # Refuser l'inscription
        data = load_data()
        if str(user_id) in data.get("pending_validations", {}):
            del data["pending_validations"][str(user_id)]
            save_data(data)
        
        await query.edit_message_text("❌ Inscription refusée.")
        
        # Notifier l'utilisateur
        try:
            await context.bot.send_message(
                user_id,
                "❌ **Votre inscription a été refusée.**\n\n"
                "Contactez un administrateur pour plus d'informations."
            )
        except:
            pass
        return
    
    # Validation
    hours = int(data_parts[2])
    
    data = load_data()
    
    # Vérifier si l'utilisateur est en attente
    if str(user_id) not in data.get("pending_validations", {}):
        await query.edit_message_text("❌ Cet utilisateur n'est plus en attente.")
        return
    
    pending = data["pending_validations"][str(user_id)]
    
    # Calculer les dates
    current_time = int(datetime.now().timestamp())
    duration_seconds = hours * 3600
    expires_at = current_time + duration_seconds
    
    # Ajouter aux membres
    data["members"][str(user_id)] = {
        "nom": pending["nom"],
        "prenom": pending["prenom"],
        "pays": pending["pays"],
        "join_time": current_time,
        "duration": duration_seconds,
        "expires_at": expires_at
    }
    
    # Supprimer des pending
    del data["pending_validations"][str(user_id)]
    save_data(data)
    
    # Générer le lien d'invitation
    try:
        # Créer un lien d'invitation unique
        invite_link = await context.bot.create_chat_invite_link(
            CHANNEL_ID,
            member_limit=1,  # Lien à usage unique
            expire_date=expires_at
        )
        link_to_send = invite_link.invite_link
    except Exception as e:
        logger.warning(f"Impossible de créer lien unique: {e}")
        link_to_send = data["link"]  # Utiliser le lien par défaut
    
    # Notifier l'utilisateur
    try:
        keyboard = [[InlineKeyboardButton("🔗 Rejoindre le canal", url=link_to_send)]]
        await context.bot.send_message(
            user_id,
            f"🎉 **Félicitations!**\n\n"
            f"Votre accès a été validé!\n\n"
            f"📢 **Canal:** {CHANNEL_NAME}\n"
            f"⏳ **Durée:** {hours} heure(s)\n"
            f"📅 **Expire le:** {datetime.fromtimestamp(expires_at).strftime('%d/%m/%Y à %H:%M')}\n\n"
            f"⚠️ *Ce lien est unique et expire avec votre accès.*",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Erreur notification user: {e}")
    
    # Notifier le canal
    try:
        await context.bot.send_message(
            CHANNEL_ID,
            f"👋 **Nouveau membre!**\n\n"
            f"👤 {pending['prenom']} {pending['nom']}\n"
            f"🌍 {pending['pays']}\n"
            f"⏳ Accès: {hours}h"
        )
    except:
        pass
    
    # Mettre à jour le message admin
    await query.edit_message_text(
        f"✅ **Membre validé!**\n\n"
        f"👤 {pending['prenom']} {pending['nom']}\n"
        f"🆔 {user_id}\n"
        f"⏳ {hours}h\n"
        f"📅 {datetime.fromtimestamp(expires_at).strftime('%d/%m/%Y à %H:%M')}"
    )


# ═══════════════════════════════════════════════════════════════
# COMMANDES ADMIN
# ═══════════════════════════════════════════════════════════════

async def list_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Liste tous les membres"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Accès refusé.")
        return
    
    data = load_data()
    members = data.get("members", {})
    current_time = int(datetime.now().timestamp())
    
    if not members:
        await update.message.reply_text("📋 Aucun membre.")
        return
    
    message = f"📋 **Membres - {CHANNEL_NAME}**\n\n"
    
    for user_id_str, member in members.items():
        time_left = member.get("expires_at", 0) - current_time
        status = "🟢" if time_left > 0 else "🔴"
        time_str = format_time_remaining(time_left)
        
        message += (
            f"{status} **{member.get('prenom', '?')} {member.get('nom', '?')}**\n"
            f"   🆔 `{user_id_str}` | 🌍 {member.get('pays', '?')}\n"
            f"   ⏳ {time_str}\n\n"
        )
    
    await update.message.reply_text(message, parse_mode="Markdown")


async def remove_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Retire un membre: /remove <user_id>"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Accès refusé.")
        return
    
    if not context.args:
        await update.message.reply_text("❌ Usage: `/remove <user_id>`")
        return
    
    try:
        user_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ ID invalide.")
        return
    
    data = load_data()
    
    if str(user_id) not in data.get("members", {}):
        await update.message.reply_text("❌ Membre non trouvé.")
        return
    
    member = data["members"][str(user_id)]
    
    # Bannir du canal
    try:
        await context.bot.ban_chat_member(CHANNEL_ID, user_id)
        await context.bot.unban_chat_member(CHANNEL_ID, user_id)  # Débannir pour permettre revenir
    except Exception as e:
        logger.warning(f"Impossible de bannir: {e}")
    
    # Supprimer de la base
    del data["members"][str(user_id)]
    save_data(data)
    
    # Notifier
    try:
        await context.bot.send_message(
            user_id,
            f"⚠️ **Votre accès à '{CHANNEL_NAME}' a été révoqué.**"
        )
    except:
        pass
    
    await update.message.reply_text(
        f"✅ **Membre retiré!**\n\n"
        f"👤 {member.get('prenom')} {member.get('nom')}"
    )


async def purge_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Purge tous les membres"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Accès refusé.")
        return
    
    data = load_data()
    members = list(data.get("members", {}).keys())
    removed = 0
    
    for user_id_str in members:
        user_id = int(user_id_str)
        
        # Ne pas supprimer les admins
        if user_id in ADMINS:
            continue
        
        try:
            await context.bot.ban_chat_member(CHANNEL_ID, user_id)
            await context.bot.unban_chat_member(CHANNEL_ID, user_id)
            
            try:
                await context.bot.send_message(
                    user_id,
                    f"⚠️ **Le canal '{CHANNEL_NAME}' a été purgé.**"
                )
            except:
                pass
            
            removed += 1
        except Exception as e:
            logger.error(f"Erreur purge {user_id}: {e}")
    
    data["members"] = {}
    save_data(data)
    
    await update.message.reply_text(f"✅ **Purge terminée!**\n\n🗑️ {removed} membre(s) retiré(s)")


async def info_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Affiche les infos du canal"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Accès refusé.")
        return
    
    data = load_data()
    members_count = len(data.get("members", {}))
    pending_count = len(data.get("pending_validations", {}))
    
    await update.message.reply_text(
        f"📋 **Informations**\n\n"
        f"🏷️ **Nom:** {CHANNEL_NAME}\n"
        f"🆔 **ID:** `{CHANNEL_ID}`\n"
        f"🔗 **Lien:** {data.get('link', CHANNEL_LINK)}\n"
        f"👥 **Membres:** {members_count}\n"
        f"⏳ **En attente:** {pending_count}\n"
        f"🕐 **Mis à jour:** {data.get('link_updated', 'Inconnu')}"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Affiche l'aide"""
    user_id = update.effective_user.id
    
    if is_admin(user_id):
        text = (
            "📖 **Commandes Admin**\n\n"
            "**Utilisateur:**\n"
            "• `/start` - S'inscrire\n\n"
            "**Admin:**\n"
            "• `/list` - Liste des membres\n"
            "• `/remove <id>` - Retirer un membre\n"
            "• `/purge` - Vider le canal\n"
            "• `/info` - Infos du canal\n\n"
            "Les validations se font via les boutons dans les notifications."
        )
    else:
        text = (
            "📖 **Aide**\n\n"
            "• `/start` - S'inscrire au canal\n\n"
            "Remplissez le formulaire et attendez la validation d'un admin."
        )
    
    await update.message.reply_text(text)


# ═══════════════════════════════════════════════════════════════
# TÂCHE DE VÉRIFICATION DES EXPIRATIONS
# ═══════════════════════════════════════════════════════════════

async def check_expirations_task(application: Application):
    """Vérifie les expirations en arrière-plan"""
    while True:
        try:
            data = load_data()
            current_time = int(datetime.now().timestamp())
            to_remove = []
            
            for user_id_str, member in data.get("members", {}).items():
                if member.get("expires_at", 0) <= current_time:
                    user_id = int(user_id_str)
                    to_remove.append((user_id, user_id_str))
            
            for user_id, user_id_str in to_remove:
                try:
                    # Bannir du canal
                    await application.bot.ban_chat_member(CHANNEL_ID, user_id)
                    await application.bot.unban_chat_member(CHANNEL_ID, user_id)
                    
                    # Supprimer de la base
                    del data["members"][user_id_str]
                    
                    # Notifier
                    try:
                        await application.bot.send_message(
                            user_id,
                            f"⏰ **Votre accès à '{CHANNEL_NAME}' a expiré.**\n\n"
                            "Contactez un admin pour renouveler."
                        )
                    except:
                        pass
                    
                    logger.info(f"Membre {user_id} expiré et retiré")
                    
                except Exception as e:
                    logger.error(f"Erreur expiration {user_id}: {e}")
            
            if to_remove:
                save_data(data)
                
        except Exception as e:
            logger.error(f"Erreur check_expirations: {e}")
        
        await asyncio.sleep(CHECK_INTERVAL)


# ═══════════════════════════════════════════════════════════════
# FONCTION PRINCIPALE
# ═══════════════════════════════════════════════════════════════

async def main():
    """Fonction principale"""
    logger.info("🤖 Démarrage du bot...")
    
    # Créer l'application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Conversation pour l'inscription
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start_command)],
        states={
            NOM: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_nom)],
            PRENOM: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_prenom)],
            PAYS: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_pays)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    
    # Ajouter les handlers
    application.add_handler(conv_handler)
    application.add_handler(CallbackQueryHandler(validate_callback, pattern="^(validate|reject)_"))
    application.add_handler(CommandHandler("list", list_command))
    application.add_handler(CommandHandler("remove", remove_command))
    application.add_handler(CommandHandler("purge", purge_command))
    application.add_handler(CommandHandler("info", info_command))
    application.add_handler(CommandHandler("help", help_command))
    
    # Démarrer le serveur web
    await start_web_server()
    
    # Démarrer la tâche de vérification
    asyncio.create_task(check_expirations_task(application))
    
    # Démarrer le bot
    await application.initialize()
    await application.start()
    logger.info("✅ Bot démarré avec succès!")
    
    # Garder le bot en vie
    await application.updater.start_polling(drop_pending_updates=True)
    
    # Boucle infinie
    while True:
        await asyncio.sleep(3600)


if __name__ == "__main__":
    asyncio.run(main())
