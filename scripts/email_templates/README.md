# Email Templates pour Clés API

Ce dossier contient les emails HTML générés automatiquement pour l'envoi de clés API aux utilisateurs.

## Fichiers

- Les fichiers sont nommés selon le format : `{email}_api_key_{timestamp}.html`
- Exemple : `user_example_com_api_key_20250129_143052.html`
- `SAMPLE_email_exemple.html` : Un exemple de template pour prévisualisation

## Utilisation

### 1. Générer un email avec clé API

```bash
cd /Users/christophe.anglade/Documents/odace_backend
python3 scripts/send_api_key_email.py
```

Le script vous demandera :
- L'adresse email de l'utilisateur
- Confirmation avant de créer la clé

### 2. Envoyer l'email via Gmail

1. Ouvrez le fichier HTML généré dans un éditeur de texte
2. Copiez tout le contenu (Cmd+A puis Cmd+C)
3. Dans Gmail, créez un nouveau message
4. Cliquez sur les trois points (⋮) en bas à droite
5. Sélectionnez "Mode HTML d'origine" ou "Show original HTML"
6. Collez le contenu HTML
7. Ajoutez le sujet : **Votre clé API ODACE - Accès autorisé**
8. Envoyez à l'utilisateur

## Structure de l'email

Chaque email contient :
- ✅ Message de bienvenue en français
- ✅ Clé API en évidence
- ✅ Instructions d'utilisation avec exemples (curl, Python)
- ✅ Consignes de sécurité
- ✅ Liens vers la documentation
- ✅ Détails de création (email, date/heure)

## Sécurité

⚠️ **Important** : 
- Ne commitez jamais les fichiers HTML contenant de vraies clés API
- Supprimez les fichiers après envoi des emails
- Les clés API ne peuvent être récupérées qu'une seule fois à la création

## Nettoyage

Pour supprimer les anciens emails :

```bash
# Supprimer tous les emails sauf le sample
find scripts/email_templates -name "*.html" -not -name "SAMPLE*" -delete

# Ou supprimer un fichier spécifique
rm scripts/email_templates/user_example_com_api_key_*.html
```

