# 🤖 Bot Telegram Multi-Canaux

Bot Telegram qui gère **plusieurs canaux privés indépendamment**, chacun avec ses propres administrateurs et membres.

---

## 🎯 Différences avec la version simple

| Fonctionnalité | Version Simple | Version Multi-Canaux |
|---------------|----------------|---------------------|
| Canaux gérés | 1 seul | Illimités |
| Admins | 2 fixes | Configurables par canal |
| Base de données | `members.json` | `channels_data.json` |
| Interface | Commandes texte | Boutons + Commandes |
| Super Admin | Non | Oui (accès total) |

---

## 📁 Structure du projet

```
telegram-bot-multi/
├── config.py           # Configuration globale
├── main.py             # Code principal (multi-canaux)
├── channels_data.json  # Base de données multi-canaux
├── requirements.txt    # Dépendances
├── .gitignore         # Fichiers ignorés
└── README.md          # Documentation
```

---

## 🚀 Démarrage rapide

### 1. Configuration

Éditez `config.py` :

```python
# Identifiants Telegram (my.telegram.org)
API_ID = 29177661
API_HASH = "votre_api_hash"
BOT_TOKEN = "votre_token_bot"

# Super Admin (vous)
SUPER_ADMIN_ID = 1190237801  # Votre ID Telegram
```

### 2. Installation

```bash
pip install -r requirements.txt
python main.py
```

### 3. Premier canal

1. Envoyez `/start` au bot
2. Cliquez sur **"➕ Créer un Canal"** (super admin uniquement)
3. Suivez les 4 étapes :
   - ID du canal Telegram
   - Nom du canal
   - Lien d'invitation
   - ID du premier admin

---

## 🎮 Commandes

### Utilisateur

| Commande | Description |
|----------|-------------|
| `/start` | Menu principal avec boutons |
| `/register` | S'inscrire à un canal |

### Administrateur

| Commande | Syntaxe | Description |
|----------|---------|-------------|
| `/validate` | `/validate <canal_id> <user_id> <heures>` | Valider un membre |
| `/remove` | `/remove <canal_id> <user_id>` | Retirer un membre |

---

## 📊 Structure de la base de données

```json
{
    "channels": {
        "-1001234567890": {
            "name": "Canal VIP Premium",
            "link": "https://t.me/+xxx",
            "admins": [1190237801, 1190237802],
            "members": {
                "987654321": {
                    "nom": "Dupont",
                    "prenom": "Jean",
                    "pays": "France",
                    "join_time": 1706880000,
                    "duration": 86400,
                    "expires_at": 1706966400
                }
            },
            "created_at": "02/02/2026 à 14:30",
            "updated_at": "02/02/2026 à 14:30"
        }
    },
    "global_admins": [1190237801]
}
```

---

## 🔐 Rôles et permissions

### Super Admin
- ✅ Créer des canaux
- ✅ Gérer tous les canaux
- ✅ Ajouter des admins globaux
- ✅ Toutes les commandes

### Admin de canal
- ✅ Gérer son canal
- ✅ Valider/retirer des membres
- ✅ Voir les statistiques
- ❌ Créer des canaux
- ❌ Gérer d'autres canaux

### Utilisateur
- ✅ S'inscrire à un canal
- ✅ Recevoir le lien après validation
- ❌ Aucune commande admin

---

## 🔄 Flux d'utilisation

### Pour le Super Admin

```
/start → "➕ Créer un Canal" → Remplir les 4 étapes
                              → Canal créé!
                              
/start → "📋 Mes Canaux" → Sélectionner un canal
                         → Gérer (stats, membres, purge...)
```

### Pour un Admin de canal

```
/start → "📋 Mes Canaux" → Son canal
                         → Gérer les membres

Quand inscription: Reçoit notification
→ /validate <canal_id> <user_id> <heures>
```

### Pour un Utilisateur

```
/register → Choisir un canal
          → Remplir Nom/Prénom/Pays
          → Attendre validation
          → Reçoit lien d'accès
```

---

## 🛠️ Déploiement sur Render

```yaml
# render.yaml
services:
  - type: web
    name: telegram-bot-multi
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: python main.py
    envVars:
      - key: API_ID
        value: 29177661
      - key: API_HASH
        value: votre_api_hash
      - key: BOT_TOKEN
        value: votre_token
      - key: SUPER_ADMIN_ID
        value: 1190237801
      - key: PORT
        value: 10000
```

---

## 📱 Captures d'écran (exemple)

### Menu Principal
```
🤖 Bot Multi-Canaux - Gestionnaire d'Accès

Bienvenue! Ce bot vous permet de gérer l'accès temporaire 
à plusieurs canaux privés.

👤 Votre ID: `1190237801`

[📋 Mes Canaux] [➕ Créer un Canal]
[❓ Aide]
```

### Détail d'un canal
```
📢 Canal VIP Premium

🆔 ID: `-1001234567890`
👥 Membres: 15
👤 Admins: 2
🔗 Lien: https://t.me/+xxx

🕐 Créé le: 02/02/2026 à 14:30

[📊 Statistiques] [👥 Liste des membres]
[⚙️ Paramètres]   [🔗 Obtenir le lien]
[➕ Ajouter admin] [🗑️ Purge]
[🔙 Retour]
```

---

## 🐛 Dépannage

| Problème | Solution |
|----------|----------|
| "Accès refusé" | Vérifiez que vous êtes admin du canal |
| "Canal non trouvé" | Vérifiez l'ID (doit commencer par -100) |
| L'utilisateur ne reçoit pas le lien | Il doit avoir démarré le bot avec `/start` |
| Le bot n'ajoute pas au canal | Vérifiez que le bot est admin du canal Telegram |

---

## 📝 Changelog

### v2.0 - Multi-Canaux
- ✅ Gestion de plusieurs canaux indépendants
- ✅ Interface avec boutons
- ✅ Super admin + admins par canal
- ✅ Commandes `/validate` et `/remove` avec canal_id
- ✅ Statistiques par canal

---

**Besoin d'aide ?** Ouvrez une issue sur GitHub.
