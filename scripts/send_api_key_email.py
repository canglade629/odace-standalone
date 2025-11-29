#!/usr/bin/env python3
"""
Script to generate API keys and create HTML email files for users.
This script prompts for an email address, creates an API key in Firestore,
and generates a French HTML email ready to be imported into Gmail.
"""
import asyncio
import sys
import os
import re
from pathlib import Path
from datetime import datetime

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from google.cloud import firestore
from app.core.api_key_manager import create_api_key


def validate_email(email: str) -> bool:
    """
    Validate email address format.
    
    Args:
        email: Email address to validate
        
    Returns:
        True if valid, False otherwise
    """
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def generate_html_email(email: str, api_key: str, created_at: str) -> str:
    """
    Generate French HTML email content with API key.
    
    Args:
        email: User's email address
        api_key: The generated API key
        created_at: Creation timestamp
        
    Returns:
        HTML email content
    """
    html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Votre clé API ODACE</title>
</head>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
    
    <div style="background-color: #f8f9fa; border-radius: 8px; padding: 30px; margin-bottom: 20px;">
        <h1 style="color: #2c3e50; margin-top: 0;">Bienvenue sur l'API ODACE</h1>
        
        <p>Bonjour,</p>
        
        <p>Votre clé API a été créée avec succès. Cette clé vous permettra d'accéder à l'ensemble de nos services API ODACE.</p>
        
        <div style="background-color: #fff; border-left: 4px solid #3498db; padding: 20px; margin: 25px 0; border-radius: 4px;">
            <h2 style="color: #2c3e50; margin-top: 0; font-size: 16px;">Votre clé API :</h2>
            <code style="background-color: #f8f9fa; padding: 12px; display: block; border-radius: 4px; font-size: 14px; word-wrap: break-word; font-family: 'Courier New', monospace; color: #e74c3c; font-weight: bold;">{api_key}</code>
            <p style="margin-bottom: 0; font-size: 12px; color: #7f8c8d; margin-top: 10px;">
                <strong>⚠️ Important :</strong> Conservez cette clé en lieu sûr. Elle ne sera plus affichée après cet email.
            </p>
        </div>
        
        <h2 style="color: #2c3e50; font-size: 18px;">Comment utiliser votre clé API</h2>
        
        <p>Pour accéder à l'API, incluez votre clé dans l'en-tête <code style="background-color: #f8f9fa; padding: 2px 6px; border-radius: 3px;">Authorization</code> de vos requêtes HTTP :</p>
        
        <div style="background-color: #2c3e50; color: #ecf0f1; padding: 15px; border-radius: 4px; margin: 15px 0; overflow-x: auto;">
            <pre style="margin: 0; font-family: 'Courier New', monospace; font-size: 13px;">curl -H "Authorization: Bearer {api_key}" \\
  https://odace-pipeline-588398598428.europe-west1.run.app/api/endpoint</pre>
        </div>
        
        <h3 style="color: #2c3e50; font-size: 16px;">Exemple avec Python :</h3>
        
        <div style="background-color: #2c3e50; color: #ecf0f1; padding: 15px; border-radius: 4px; margin: 15px 0; overflow-x: auto;">
            <pre style="margin: 0; font-family: 'Courier New', monospace; font-size: 13px;">import requests

headers = {{
    "Authorization": "Bearer {api_key}"
}}

response = requests.get(
    "https://odace-pipeline-588398598428.europe-west1.run.app/api/endpoint",
    headers=headers
)</pre>
        </div>
        
        <h2 style="color: #2c3e50; font-size: 18px;">Documentation</h2>
        
        <p>Pour plus d'informations sur l'utilisation de l'API, consultez notre documentation interactive :</p>
        
        <p style="margin: 15px 0;">
            📚 <a href="https://odace-pipeline-588398598428.europe-west1.run.app/docs" style="color: #3498db; text-decoration: none; font-weight: bold;">Documentation de l'API</a>
        </p>
        
        <h2 style="color: #2c3e50; font-size: 18px;">Informations importantes</h2>
        
        <div style="background-color: #fff3cd; border-left: 4px solid #ffc107; padding: 15px; margin: 20px 0; border-radius: 4px;">
            <p style="margin: 0;"><strong>Sécurité :</strong></p>
            <ul style="margin: 10px 0; padding-left: 20px;">
                <li>Ne partagez jamais votre clé API</li>
                <li>Ne la commitez pas dans votre système de contrôle de version</li>
                <li>Utilisez toujours HTTPS pour vos requêtes</li>
                <li>Contactez-nous immédiatement si votre clé est compromise</li>
            </ul>
        </div>
        
        <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #e0e0e0;">
            <p style="color: #7f8c8d; font-size: 14px; margin-bottom: 5px;">
                <strong>Détails de la clé :</strong>
            </p>
            <p style="color: #7f8c8d; font-size: 13px; margin: 5px 0;">
                Email : {email}<br>
                Créée le : {datetime.fromisoformat(created_at).strftime('%d/%m/%Y à %H:%M:%S UTC')}
            </p>
        </div>
        
        <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #e0e0e0;">
            <p style="color: #7f8c8d; font-size: 14px;">
                Si vous avez des questions ou besoin d'assistance, n'hésitez pas à nous contacter.
            </p>
            <p style="color: #7f8c8d; font-size: 14px; margin-top: 20px;">
                Cordialement,<br>
                <strong>L'équipe ODACE</strong>
            </p>
        </div>
    </div>
    
    <div style="text-align: center; color: #95a5a6; font-size: 12px; margin-top: 20px;">
        <p>Cet email a été généré automatiquement. Merci de ne pas y répondre.</p>
    </div>
    
</body>
</html>"""
    return html


async def main():
    """Main script entry point."""
    print("\n" + "="*80)
    print("🔑 Générateur de clé API ODACE")
    print("="*80 + "\n")
    
    # Prompt for email address
    while True:
        email = input("📧 Entrez l'adresse email de l'utilisateur : ").strip()
        
        if not email:
            print("❌ L'adresse email ne peut pas être vide.\n")
            continue
        
        if not validate_email(email):
            print("❌ Format d'email invalide. Veuillez réessayer.\n")
            continue
        
        # Confirm
        confirm = input(f"\n✓ Créer une clé API pour '{email}' ? (oui/non) : ").strip().lower()
        if confirm in ['oui', 'o', 'yes', 'y']:
            break
        elif confirm in ['non', 'n', 'no']:
            print("\n❌ Opération annulée.\n")
            sys.exit(0)
        else:
            print("❌ Réponse invalide. Veuillez entrer 'oui' ou 'non'.\n")
    
    print("\n⏳ Création de la clé API...")
    
    # Create API key in Firestore
    db = firestore.AsyncClient()
    try:
        result = await create_api_key(email, db)
        
        if result.get('replaced'):
            print("⚠️  Une clé API existante a été trouvée et remplacée.")
        print("✅ Clé API créée avec succès !\n")
        
        # Generate HTML email
        print("📝 Génération de l'email HTML...")
        html_content = generate_html_email(
            email=result['user_id'],
            api_key=result['api_key'],
            created_at=result['created_at']
        )
        
        # Create filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        safe_email = email.replace('@', '_').replace('.', '_')
        filename = f"{safe_email}_api_key_{timestamp}.html"
        
        # Get the directory path
        script_dir = Path(__file__).parent
        email_dir = script_dir / "email_templates"
        filepath = email_dir / filename
        
        # Save HTML file
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print("✅ Email HTML généré avec succès !\n")
        print("="*80)
        print("📋 RÉSUMÉ")
        print("="*80)
        print(f"Email :       {email}")
        print(f"Clé API :     {result['api_key']}")
        print(f"Fichier HTML: {filepath}")
        print("="*80)
        print("\n📬 ÉTAPES SUIVANTES :")
        print(f"  1. Ouvrez le fichier : {filepath}")
        print("  2. Copiez tout le contenu HTML")
        print("  3. Dans Gmail, créez un nouveau message")
        print("  4. Cliquez sur les trois points (⋮) > Afficher le HTML original")
        print("  5. Collez le contenu et envoyez à l'utilisateur")
        print("\n💡 SUGGESTION DE SUJET :")
        print("     Votre clé API ODACE - Accès autorisé")
        print("\n")
        
    except Exception as e:
        print(f"\n❌ Erreur : {str(e)}")
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())

