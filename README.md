# 🤖 Bot Telegram - Version Render (Sans Telethon)

Version du bot optimisée pour le déploiement sur Render et autres plateformes cloud.

---

## ⚠️ Problème résolu

| Problème | Solution |
|----------|----------|
| Telethon nécessite une session interactive | ✅ Utilise `python-telegram-bot` |
| Fichier `.session` à créer manuellement | ✅ Pas besoin de fichier session |
| Erreur "Could not find the input entity" | ✅ API plus simple et stable |

---

## 📦 Différences avec la version Telethon

| Aspect | Telethon | python-telegram-bot |
|--------|----------|---------------------|
| Session | Fichier `.session` requis | Token suffisant |
| Authentification | API_ID + API_HASH | BOT_TOKEN uniquement |
| Complexité | Plus complexe | Plus simple |
| Déploiement cloud | Difficile | Facile ✅ |

---

## 🚀 Configuration Render

### 1. Variables d'environnement (Obligatoires)

Dans Render Dashboard → Your Service → Environment:

```
BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrSTUvwxyz
CHANNEL_ID=-1001234567890
CHANNEL_LINK=https://t.me/+VotreLienIci
CHANNEL_NAME=Mon Canal VIP
ADMINS=1190237801,1190237802
PORT=10000
```

### 2. Build & Start Commands

```bash
# Build Command:
pip install -r requirements.txt

# Start Command:
python main.py
```

---

## 📋 Prérequis

### 1. Créer le bot

1. Allez sur [@BotFather](https://t.me/BotFather)
2. Envoyez `/newbot`
3. Suivez les instructions
4. **Copiez le TOKEN** (ex: `123456789:ABCdef...`)

### 2. Créer le canal

1. Créez un canal privé sur Telegram
2. Ajoutez votre bot comme **administrateur**
3. Donnez-lui ces permissions:
   - ✅ Ajouter des membres
   - ✅ Bannir des utilisateurs
   - ✅ Supprimer des messages
   - ✅ Gérer le groupe

### 3. Obtenir l'ID du canal

1. Ajoutez [@RawDataBot](https://t.me/RawDataBot) à votre canal
2. Le bot enverra l'ID (format: `-1001234567890`)
3. Retirez @RawDataBot

### 4. Obtenir votre ID

1. Envoyez `/start` à [@userinfobot](https://t.me/userinfobot)
2. Notez votre ID

---

## 🎮 Commandes

### Utilisateur

| Commande | Description |
|----------|-------------|
| `/start` | Démarrer l'inscription |

### Administrateur

| Commande | Description |
|----------|-------------|
| `/list` | Liste des membres |
| `/remove <id>` | Retirer un membre |
| `/purge` | Vider le canal |
| `/info` | Infos du canal |
| `/help` | Aide |

---

## 🔄 Flux d'utilisation

```
Utilisateur          Admin              Bot
    |                  |                 |
    |──/start─────────▶|                 |
    |◄──Formulaire─────|                 |
    |──Nom/Prénom/Pays▶|                 |
    |                  |◄──Notification──|
    |                  │──[Bouton: Valider 24h]──▶|
    |◄──Lien d'accès──────────────────────────────|
    |                  |                 |
    │──Rejoint canal──▶│                 │
    │                  │                 │
    │                  │                 │◄──Expiration auto
    │◄──"Accès expiré"────────────────────────────│
```

---

## 📁 Structure

```
telegram-bot-render/
├── config.py        # Configuration (variables d'env)
├── main.py          # Code principal
├── requirements.txt # Dépendances
├── members.json     # Base de données
└── README.md        # Documentation
```

---

## 🐛 Dépannage

| Erreur | Solution |
|--------|----------|
| "Bot not found" | Vérifiez BOT_TOKEN |
| "Chat not found" | Vérifiez CHANNEL_ID (doit commencer par -100) |
| "Not enough rights" | Ajoutez le bot comme admin du canal |
| "User not found" | L'utilisateur doit d'abord démarrer le bot |

---

## 📝 Notes importantes

1. **Le bot doit être admin du canal** pour ajouter/retirer des membres
2. **Les utilisateurs doivent démarrer le bot** avant de pouvoir être ajoutés
3. **Les liens d'invitation** sont générés automatiquement (usage unique)
4. **Les expirations** sont vérifiées toutes les 60 secondes

---

## ✅ Déploiement rapide sur Render

```bash
# 1. Créer un repo GitHub avec ces fichiers
# 2. Connecter Render au repo
# 3. Configurer les variables d'environnement
# 4. Deploy!
```

---

**Le bot est maintenant prêt pour Render!** 🎉
