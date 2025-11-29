# API Key Authentication System

This document describes how to use the multi-user API key authentication system.

## Overview

The API key system allows you to:
- Generate secure API keys for different users
- Validate API keys on each request
- Revoke or delete API keys
- Track usage (last_used_at timestamp)

## Security Features

- **Secure Generation**: Keys use 256 bits of entropy via Python's `secrets` module
- **Hashed Storage**: Keys are hashed with SHA-256 before storage in Firestore
- **Bearer Token Auth**: Industry-standard `Authorization: Bearer` header
- **Soft Delete**: Keys can be revoked (active=false) for audit trail
- **Admin Protection**: Key management endpoints protected by separate admin secret

## Configuration

### Environment Variables

Update your `.env` file:

```bash
# Remove the old API_KEY
# API_KEY=odace-api-key-2024  # DELETE THIS

# Add the new ADMIN_SECRET
ADMIN_SECRET=your-secure-admin-secret-here
```

The `ADMIN_SECRET` protects the admin endpoints for creating/managing API keys.

## Managing API Keys

### Method 1: CLI Tool (Recommended for Manual Management)

#### Create a new API key

```bash
python scripts/manage_api_keys.py create user@example.com
```

Output:
```
✅ API Key Created Successfully!
================================================================================
User ID:    user@example.com
API Key:    odace_example_api_key_1234567890abcdefgh
Created At: 2025-01-10T10:30:00.000000
================================================================================

⚠️  IMPORTANT: Save this API key securely. It will not be shown again!
```

#### List all API keys

```bash
python scripts/manage_api_keys.py list
```

#### Revoke an API key (soft delete)

```bash
python scripts/manage_api_keys.py revoke odace_example_api_key_1234567890abcdefgh
```

#### Permanently delete an API key

```bash
python scripts/manage_api_keys.py delete odace_example_api_key_1234567890abcdefgh
```

### Method 2: Admin API Endpoints

All admin endpoints require the `ADMIN_SECRET` in the Authorization header.

#### Create a new API key

```bash
POST /admin/api-keys
Authorization: Bearer your-admin-secret-here
Content-Type: application/json

{
  "user_id": "user@example.com"
}
```

Response:
```json
{
  "api_key": "odace_example_api_key_1234567890abcdefgh",
  "user_id": "user@example.com",
  "created_at": "2025-01-10T10:30:00.000000",
  "message": "API key created successfully. Save this key - it will not be shown again."
}
```

#### List all API keys

```bash
GET /admin/api-keys
Authorization: Bearer your-admin-secret-here
```

#### Revoke an API key

```bash
DELETE /admin/api-keys/revoke
Authorization: Bearer your-admin-secret-here
Content-Type: application/json

{
  "api_key": "odace_example_api_key_1234567890abcdefgh"
}
```

#### Permanently delete an API key

```bash
DELETE /admin/api-keys/delete
Authorization: Bearer your-admin-secret-here
Content-Type: application/json

{
  "api_key": "odace_example_api_key_1234567890abcdefgh"
}
```

## Using API Keys

### For API Consumers

Users must include their API key in the `Authorization` header with the `Bearer` scheme:

```bash
GET /api/endpoint
Authorization: Bearer odace_example_api_key_1234567890abcdefgh
```

Example with curl:

```bash
curl -H "Authorization: Bearer odace_example_api_key_1234567890abcdefgh" \
  https://your-api.com/api/endpoint
```

Example with Python requests:

```python
import requests

headers = {
    "Authorization": "Bearer odace_example_api_key_1234567890abcdefgh"
}

response = requests.get("https://your-api.com/api/endpoint", headers=headers)
```

### Authentication Errors

- **401 Unauthorized**: API key is missing from the request
- **403 Forbidden**: API key is invalid or has been revoked

## Firestore Schema

API keys are stored in the `api_keys` collection:

```
Collection: api_keys
Document ID: <sha256_hash_of_api_key>
Fields:
  - user_id: string         # User email or identifier
  - created_at: timestamp   # When the key was created
  - last_used_at: timestamp # Last time the key was used (auto-updated)
  - active: boolean         # Whether the key is active (false = revoked)
```

## Migration from Old System

The old single `API_KEY` system has been completely replaced. You need to:

1. **Update your `.env` file**:
   - Remove `API_KEY`
   - Add `ADMIN_SECRET`

2. **Generate API keys** for your users:
   ```bash
   python scripts/manage_api_keys.py create user1@example.com
   python scripts/manage_api_keys.py create user2@example.com
   ```

3. **Update client code** to use `Authorization: Bearer` header instead of `X-API-Key`

4. **Distribute API keys** to your users securely

## Testing

Run the test suite to verify the system is working:

```bash
python scripts/test_api_key_system.py
```

This will test:
- API key generation
- Validation
- Last used timestamp updates
- Revocation
- Deletion
- Invalid key rejection

## Best Practices

1. **Keep API keys secret**: Never commit them to version control
2. **Use HTTPS**: Always use HTTPS in production to protect keys in transit
3. **Rotate keys regularly**: Delete old keys and generate new ones periodically
4. **Monitor usage**: Check `last_used_at` timestamps to identify unused keys
5. **Revoke before delete**: Use revocation first to ensure no active usage before permanent deletion
6. **Secure admin secret**: Protect your `ADMIN_SECRET` as it controls all key management

## Troubleshooting

### "API key is missing"
- Ensure you're sending the `Authorization: Bearer <key>` header
- Check for typos in the header name

### "Invalid or inactive API key"
- Verify the key hasn't been revoked
- Check that you're using the complete key including the `odace_` prefix
- Ensure the key exists in Firestore

### Firestore connection issues
- Verify GCP credentials are configured
- Check that the service account has Firestore permissions
- Ensure the Firestore API is enabled in your GCP project

## Support

For issues or questions, please refer to the main README.md or contact your system administrator.

