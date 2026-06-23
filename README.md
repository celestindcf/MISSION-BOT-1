# 🖤 Mission Dispatch Bot

Bot Discord de dispatching de missions pour Black Ops / Jupiter Network.

## Fonctionnalités

- Assignation de missions à des agents
- Suivi des statuts (en attente, en cours, terminée, annulée)
- Gestion des rôles dynamique
- Override des permissions par utilisateur
- Interface entièrement configurable via commandes Discord

## Commandes principales

| Commande | Description |
|----------|-------------|
| `!assign @user mission` | Assigne une mission |
| `!missions` | Liste toutes les missions |
| `!status ID statut` | Change le statut |
| `!my_missions` | Voir ses missions |
| `!complete ID` | Terminer une mission |
| `!config_show` | Voir la configuration |
| `!role_rename key nom` | Renommer un rôle |
| `!role_link key @role` | Associer un rôle Discord |
| `!user_override @user roles perms` | Override utilisateur |

## Installation

1. Cloner le repo
2. Créer un fichier `config.json` à partir de `config.json.example`
3. Installer les dépendances : `pip install -r requirements.txt`
4. Lancer : `python main.py`

## Déploiement sur Render

1. Connecter le repo
2. Build command : `pip install -r requirements.txt`
3. Start command : `python main.py`
4. Ajouter `DISCORD_TOKEN` en variable d'environnement

## Licence

Private - Black Ops / Jupiter Network
