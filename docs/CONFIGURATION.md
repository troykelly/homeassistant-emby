# Configuration Reference

This document covers all configuration options for the Emby Media integration.

## Initial Setup

### Creating an API Key in Emby

Before configuring the integration, you need an API key from your Emby server:

1. Open your Emby server dashboard in a web browser
   - Usually at `http://your-server-ip:8096`
2. Click the **Settings** (gear) icon
3. Navigate to **Advanced** → **API Keys**
4. Click **+ New API Key**
5. Enter a name (e.g., "Home Assistant")
6. Click **OK**
7. **Copy the generated key** - you'll need it for configuration

> **Note**: Store your API key securely. Anyone with this key can control your Emby server.

## UI Configuration (Recommended)

The easiest way to configure the integration is through the Home Assistant UI.

### Step 1: Add the Integration

1. Go to **Settings** → **Devices & Services**
2. Click **+ Add Integration**
3. Search for **"Emby Media"**
4. Click to add it

### Step 2: Enter Connection Details

| Field | Required | Description |
|-------|----------|-------------|
| **Host** | Yes | Your Emby server hostname or IP address |
| **Port** | Yes | Server port (default: 8096 for HTTP, 8920 for HTTPS) |
| **Use SSL** | No | Enable for HTTPS connections |
| **API Key** | Yes | The API key you created in Emby |
| **Verify SSL** | No | Validate SSL certificate (disable for self-signed) |

### Connection Examples

**Local HTTP server:**
```
Host: 192.168.1.100
Port: 8096
Use SSL: No
```

**Local HTTPS with self-signed certificate:**
```
Host: emby.local
Port: 8920
Use SSL: Yes
Verify SSL: No
```

**Remote server with valid SSL:**
```
Host: emby.example.com
Port: 443
Use SSL: Yes
Verify SSL: Yes
```

## YAML Configuration

You can also configure the integration via `configuration.yaml`. This is useful for:
- Storing sensitive values in `secrets.yaml`
- Version controlling your configuration
- Setting up multiple servers

### Basic Configuration

```yaml
embymedia:
  host: emby.local
  api_key: !secret emby_api_key
```

### Full Configuration

```yaml
embymedia:
  # Required
  host: emby.local
  api_key: !secret emby_api_key

  # Connection settings
  port: 8096              # Default: 8096
  ssl: false              # Default: false
  verify_ssl: true        # Default: true

  # Polling and updates
  scan_interval: 10       # Seconds between polls (5-300)
  enable_websocket: true  # Real-time updates

  # Device filtering
  ignored_devices: "Web Player, Guest Tablet"  # Comma-separated
  ignore_web_players: false  # Hide browser sessions

  # Transcoding options
  direct_play: true           # Try direct play first
  video_container: mp4        # mp4, mkv, or webm
  max_video_bitrate: 10000    # kbps (optional)
  max_audio_bitrate: 320      # kbps (optional)
```

### Using secrets.yaml

For security, store your API key in `secrets.yaml`:

**secrets.yaml:**
```yaml
emby_api_key: your-api-key-here
```

**configuration.yaml:**
```yaml
embymedia:
  host: emby.local
  api_key: !secret emby_api_key
```

## Configuration Options Reference

### Connection Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `host` | string | *required* | Emby server hostname or IP address |
| `port` | integer | 8096 | Server port number |
| `ssl` | boolean | false | Use HTTPS instead of HTTP |
| `api_key` | string | *required* | Emby API key for authentication |
| `verify_ssl` | boolean | true | Validate SSL certificate |

### Update Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `scan_interval` | integer | 10 | Seconds between polling updates (5-300) |
| `enable_websocket` | boolean | true | Use WebSocket for real-time updates |

**About Scan Interval:**
- Lower values = more responsive, but more server load
- When WebSocket is enabled, polling is reduced to 60 seconds
- Minimum: 5 seconds, Maximum: 300 seconds (5 minutes)

**About WebSocket:**
- Provides near-instant state updates
- Automatically reconnects if disconnected
- Falls back to polling if WebSocket fails
- Recommended: Keep enabled for best experience

### Device Filtering Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `ignored_devices` | string | "" | Comma-separated list of device names to ignore |
| `ignore_web_players` | boolean | false | Hide all web browser sessions |

**Examples:**
```yaml
# Ignore specific devices
ignored_devices: "Guest iPad, Kids Tablet, Web Player"

# Hide all web browser sessions
ignore_web_players: true
```

### Transcoding Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `direct_play` | boolean | true | Attempt direct play before transcoding |
| `video_container` | string | "mp4" | Preferred container format |
| `max_video_bitrate` | integer | *none* | Maximum video bitrate in kbps |
| `max_audio_bitrate` | integer | *none* | Maximum audio bitrate in kbps |

**Video Container Options:**
- `mp4` - Most compatible, works with most players
- `mkv` - Better quality, less compatible
- `webm` - Web-optimized, limited support

**Bitrate Guidelines:**
| Quality | Video Bitrate | Audio Bitrate |
|---------|--------------|---------------|
| 1080p High | 10000-15000 | 320 |
| 1080p Medium | 6000-8000 | 256 |
| 720p | 4000-5000 | 192 |
| Mobile | 2000-3000 | 128 |

## Modifying Options After Setup

You can change configuration options at any time:

1. Go to **Settings** → **Devices & Services**
2. Find **Emby Media** and click **Configure**
3. Modify the options
4. Click **Submit**

Changes take effect immediately (no restart required).

## Multiple Emby Servers

To connect multiple Emby servers, add the integration multiple times:

1. Go to **Settings** → **Devices & Services**
2. Click **+ Add Integration**
3. Search for **"Emby Media"**
4. Enter the second server's details

Each server will have its own set of entities.

## Advanced: User Selection

If your Emby server has multiple users, you can optionally select a specific user:

1. During setup, after entering connection details
2. You'll be prompted to select a user (optional)
3. This affects which libraries are visible and enforces user restrictions

If no user is selected, the integration uses the API key's default permissions.

## Troubleshooting Configuration

### "Connection Failed"

1. Verify Emby server is running: `http://your-server:8096`
2. Check firewall rules allow the connection
3. Try using IP address instead of hostname
4. For HTTPS, try disabling SSL verification temporarily

### "Invalid API Key"

1. Generate a new API key in Emby Dashboard
2. Ensure no extra spaces when pasting
3. Verify the key hasn't been revoked

### "No Devices Found"

1. Open Emby on at least one client device
2. Check that remote control is enabled on the client
3. Verify the device isn't in the ignored list

### Configuration Not Saving

1. Check Home Assistant logs for errors
2. Ensure configuration.yaml syntax is valid
3. Restart Home Assistant after YAML changes

## Next Steps

- **[Automations](AUTOMATIONS.md)** - Create automations with your Emby media players
- **[Services](SERVICES.md)** - Learn about available service calls
- **[Troubleshooting](TROUBLESHOOTING.md)** - Detailed troubleshooting guide
