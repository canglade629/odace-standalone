#!/usr/bin/env python3
"""CLI tool for managing API keys."""
import asyncio
import sys
import os
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from google.cloud import firestore
from app.core.api_key_manager import (
    create_api_key,
    revoke_api_key,
    delete_api_key,
    list_api_keys
)


def print_usage():
    """Print usage information."""
    print("""
API Key Management CLI

Usage:
    python scripts/manage_api_keys.py create <user_id>
    python scripts/manage_api_keys.py revoke <api_key>
    python scripts/manage_api_keys.py delete <api_key>
    python scripts/manage_api_keys.py list

Commands:
    create <user_id>  - Generate a new API key for the specified user
    revoke <api_key>  - Revoke an API key (soft delete, sets active=False)
    delete <api_key>  - Permanently delete an API key
    list              - List all API keys (without plaintext)

Examples:
    python scripts/manage_api_keys.py create user@example.com
    python scripts/manage_api_keys.py revoke sk_live_abc123...
    python scripts/manage_api_keys.py list
""")


async def cmd_create(user_id: str):
    """Create a new API key."""
    db = firestore.AsyncClient()
    try:
        result = await create_api_key(user_id, db)
        
        if result.get('replaced'):
            print("\n⚠️  Existing API key for this user was found and replaced.")
        
        print("\n✅ API Key Created Successfully!")
        print("=" * 80)
        print(f"User ID:    {result['user_id']}")
        print(f"API Key:    {result['api_key']}")
        print(f"Created At: {result['created_at']}")
        print("=" * 80)
        print("\n⚠️  IMPORTANT: Save this API key securely. It will not be shown again!\n")
    finally:
        db.close()  # Not awaitable in AsyncClient


async def cmd_revoke(api_key: str):
    """Revoke an API key."""
    db = firestore.AsyncClient()
    try:
        success = await revoke_api_key(api_key, db)
        if success:
            print(f"\n✅ API key revoked successfully")
        else:
            print(f"\n❌ API key not found")
            sys.exit(1)
    finally:
        db.close()  # Not awaitable in AsyncClient


async def cmd_delete(api_key: str):
    """Delete an API key permanently."""
    db = firestore.AsyncClient()
    try:
        # Confirm deletion
        confirm = input(f"⚠️  Are you sure you want to permanently delete this API key? (yes/no): ")
        if confirm.lower() != "yes":
            print("Deletion cancelled.")
            return
        
        success = await delete_api_key(api_key, db)
        if success:
            print(f"\n✅ API key deleted successfully")
        else:
            print(f"\n❌ API key not found")
            sys.exit(1)
    finally:
        db.close()  # Not awaitable in AsyncClient


async def cmd_list():
    """List all API keys."""
    db = firestore.AsyncClient()
    try:
        keys = await list_api_keys(db)
        
        if not keys:
            print("\nNo API keys found.")
            return
        
        print(f"\n📋 API Keys ({len(keys)} total)")
        print("=" * 120)
        print(f"{'User ID':<30} {'Active':<8} {'Created At':<25} {'Last Used At':<25} {'Hash (first 16)':<20}")
        print("=" * 120)
        
        for key in keys:
            user_id = key.get('user_id', 'N/A')
            active = '✓' if key.get('active', False) else '✗'
            created_at = key.get('created_at')
            last_used_at = key.get('last_used_at')
            hash_preview = key.get('hash', '')[:16]
            
            created_str = created_at.strftime('%Y-%m-%d %H:%M:%S') if created_at else 'N/A'
            last_used_str = last_used_at.strftime('%Y-%m-%d %H:%M:%S') if last_used_at else 'Never'
            
            print(f"{user_id:<30} {active:<8} {created_str:<25} {last_used_str:<25} {hash_preview:<20}")
        
        print("=" * 120)
        print()
    finally:
        db.close()  # Not awaitable in AsyncClient


async def main():
    """Main CLI entry point."""
    if len(sys.argv) < 2:
        print_usage()
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    try:
        if command == "create":
            if len(sys.argv) != 3:
                print("❌ Error: create command requires user_id argument")
                print_usage()
                sys.exit(1)
            user_id = sys.argv[2]
            await cmd_create(user_id)
        
        elif command == "revoke":
            if len(sys.argv) != 3:
                print("❌ Error: revoke command requires api_key argument")
                print_usage()
                sys.exit(1)
            api_key = sys.argv[2]
            await cmd_revoke(api_key)
        
        elif command == "delete":
            if len(sys.argv) != 3:
                print("❌ Error: delete command requires api_key argument")
                print_usage()
                sys.exit(1)
            api_key = sys.argv[2]
            await cmd_delete(api_key)
        
        elif command == "list":
            await cmd_list()
        
        else:
            print(f"❌ Error: Unknown command '{command}'")
            print_usage()
            sys.exit(1)
    
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

