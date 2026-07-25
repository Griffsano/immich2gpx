# 🔑 Immich API Key Setup

*immich2gpx* requires a **read-only API key** to query your server.

## ✨ Create an Immich API Key

1. Log in to the Immich web interface  
2. On the top right, click on your profile image and open `Account Settings`
3. Select the menu `API Keys` (alternatively, visit https://your-immich-server.example.com/user-settings?isOpen=api-keys)
4. Click on `+ New API Key`
5. Select **only** the following permissions:
   - `asset.read`
   - `album.read`
   - `face.read`
   - `person.read`
6. Click on `Create`
7. Copy and securely store the key

## 📝 Use in Configuration

Add your API key under the `immich/api_key` configuration:

```yaml
immich:
  url: https://your-immich-server.example.com
  api_key: YOUR_API_KEY
```

Refer to the [Configuration Schema](config_schema.md#immich-server-settings) for details.

## 🛡️ Security Notes

- Only set the recommended permissions as defined above. This prevents privileged write access to the Immich database, which is not required for *immich2gpx*.
- Treat API keys like passwords
- Do **not** commit keys to version control
- Revoke compromised keys immediately
