# Troubleshooting Guide

This guide helps you resolve common issues with the Emby Media integration.

## Table of Contents

- [Connection Issues](#connection-issues)
- [Authentication Issues](#authentication-issues)
- [Entity Issues](#entity-issues)
- [Playback Issues](#playback-issues)
- [WebSocket Issues](#websocket-issues)
- [Media Browsing Issues](#media-browsing-issues)
- [Performance Issues](#performance-issues)
- [Getting Diagnostics](#getting-diagnostics)
- [Reporting Issues](#reporting-issues)

---

## Connection Issues

### "Connection Failed" During Setup

**Symptoms:**
- Error message "Cannot connect to Emby server"
- Timeout during configuration

**Solutions:**

1. **Verify Emby is running:**
   - Open `http://your-server:8096` in a browser
   - You should see the Emby web interface

2. **Check the host and port:**
   - Use IP address instead of hostname (e.g., `192.168.1.100` instead of `emby.local`)
   - Default ports: `8096` (HTTP), `8920` (HTTPS)

3. **Check firewall:**
   - Ensure your firewall allows connections on the Emby port
   - On Linux: `sudo ufw allow 8096`

4. **Check network connectivity:**
   - From the HA host, run: `curl http://your-emby-server:8096/System/Info/Public`
   - You should get a JSON response

5. **For Docker users:**
   - Ensure HA container can reach Emby container
   - Use the Docker network IP or container name if on the same network

### "SSL Certificate Verification Failed"

**Symptoms:**
- Error during HTTPS connection
- Works in browser but not in HA

**Solutions:**

1. **For self-signed certificates:**
   - Disable "Verify SSL" in the integration configuration
   - This is safe for local connections

2. **For Let's Encrypt or other CA certificates:**
   - Ensure the certificate is valid (not expired)
   - Verify the hostname matches the certificate

3. **Check certificate chain:**
   - Some systems need the full certificate chain
   - Install CA certificates: `sudo apt install ca-certificates`

---

## Authentication Issues

### "Invalid API Key"

**Symptoms:**
- Authentication error during setup
- Previously working integration stops working

**Solutions:**

1. **Generate a new API key:**
   - Emby Dashboard → Settings → Advanced → API Keys
   - Create a new key and try again

2. **Check for whitespace:**
   - Ensure no leading/trailing spaces when pasting the key
   - Copy the key directly from Emby, don't retype it

3. **Verify key hasn't been revoked:**
   - Check the API Keys page in Emby
   - Look for your key in the list

4. **Check key permissions:**
   - API keys should have full access by default
   - Try creating a key with admin user

### "Access Denied" or "Unauthorized"

**Symptoms:**
- Setup succeeds but some features don't work
- Library browsing shows empty

**Solutions:**

1. **Check user permissions:**
   - If you selected a user during setup, that user's permissions apply
   - Ensure the user has access to the libraries you want to browse

2. **Verify library access:**
   - Emby Dashboard → Users → [Your User] → Library Access
   - Enable access to all required libraries

---

## Entity Issues

### No Entities Appearing

**Symptoms:**
- Integration shows as configured but no entities
- No media player entities visible

**Solutions:**

1. **Open Emby on a client device:**
   - Media players only appear when clients are connected
   - Open Emby on your TV, phone, or another device

2. **Check if device supports remote control:**
   - Not all Emby clients support remote control
   - Web browsers and official apps generally work

3. **Verify device isn't ignored:**
   - Check integration options for "Ignored Devices"
   - Remove the device from the ignored list if present

4. **Wait for the first poll:**
   - It can take up to the scan interval (default 10 seconds) for entities to appear

5. **Check Home Assistant logs:**
   - Look for errors related to `embymedia`
   - Go to Settings → System → Logs

### Entities Show as "Unavailable"

**Symptoms:**
- Media player shows unavailable
- Entity appears but can't be controlled

**Solutions:**

1. **Client disconnected:**
   - The Emby client may have closed
   - Reopen Emby on the device

2. **Session timeout:**
   - Long-idle sessions may be closed by Emby
   - Interact with Emby on the device to restore the session

3. **Server restart:**
   - After Emby server restart, clients need to reconnect
   - Wait a few minutes for sessions to re-establish

4. **Check coordinator status:**
   - The integration may have lost connection
   - Reload the integration: Settings → Devices & Services → Emby Media → ⋮ → Reload

### Entity Names Are Strange

**Symptoms:**
- Entity names don't match device names
- Multiple entities for same device

**Solutions:**

1. **Device names come from Emby:**
   - The entity name is based on the device name in Emby
   - Rename the device in the Emby client settings

2. **Duplicate entities:**
   - May occur if device ID changes
   - Delete old entities from Entity Registry

---

## Playback Issues

### Playback Commands Don't Work

**Symptoms:**
- Play/Pause/Stop don't respond
- Volume changes don't apply

**Solutions:**

1. **Check client capabilities:**
   - Not all clients support all commands
   - Check `supported_features` attribute of the entity

2. **Verify active session:**
   - Commands only work on active sessions
   - Ensure Emby is open on the device

3. **Check API command:**
   - Some commands may not be supported by certain Emby versions
   - Try using the Emby web interface to verify functionality

### Seeking Doesn't Work

**Symptoms:**
- Seek bar moves but position doesn't change
- Position resets after seeking

**Solutions:**

1. **Client limitation:**
   - Some clients don't support remote seeking
   - Try a different client (web browser usually works)

2. **File format issue:**
   - Some file formats don't support seeking well
   - This is typically a client/transcoding issue

### Media Position Not Updating

**Symptoms:**
- Position stays at 0
- Position doesn't update during playback

**Solutions:**

1. **Enable WebSocket:**
   - Position updates more frequently with WebSocket
   - Enable in integration options

2. **Reduce scan interval:**
   - Set to 5 seconds for more frequent updates
   - Note: increases server load

---

## WebSocket Issues

### WebSocket Won't Connect

**Symptoms:**
- Log shows WebSocket connection failures
- Real-time updates not working

**Solutions:**

1. **Check WebSocket URL:**
   - WebSocket uses `ws://` or `wss://` protocol
   - Ensure Emby's WebSocket is enabled

2. **Proxy interference:**
   - Reverse proxies may block WebSocket
   - Configure proxy to allow WebSocket connections
   - For nginx: add `proxy_http_version 1.1;` and `proxy_set_header Upgrade $http_upgrade;`

3. **Firewall issues:**
   - WebSocket uses the same port as HTTP
   - Ensure port is fully open (not just HTTP filtered)

### Frequent Disconnections

**Symptoms:**
- WebSocket connects but drops frequently
- States jump between values

**Solutions:**

1. **Network stability:**
   - Check for network issues between HA and Emby
   - Try wired connection instead of WiFi

2. **Server resources:**
   - Emby server may be overloaded
   - Check Emby server CPU/memory usage

3. **Disable WebSocket:**
   - If unstable, disable WebSocket in options
   - Polling will be used instead (slightly slower updates)

4. **Check reconnection:**
   - Integration automatically reconnects with exponential backoff
   - Check logs for reconnection attempts

---

## Media Browsing Issues

### Library Shows Empty

**Symptoms:**
- Browse Media shows no libraries
- Some libraries missing

**Solutions:**

1. **Check API key permissions:**
   - API key should have access to all libraries
   - Try recreating the key

2. **Verify library visibility:**
   - Emby Dashboard → Libraries
   - Ensure libraries are not hidden

3. **User restrictions:**
   - If using user selection, check user's library access
   - Emby Dashboard → Users → [User] → Library Access

4. **Cache issue:**
   - Browse results are cached
   - Wait a few minutes for cache to refresh

### Media Won't Play from Browse

**Symptoms:**
- Can browse but "Play" does nothing
- Error when trying to play

**Solutions:**

1. **Check client capabilities:**
   - The selected client may not support the media type
   - Try a different client

2. **Transcoding required:**
   - Some files need transcoding
   - Enable transcoding in Emby settings

3. **Direct play issues:**
   - Disable "Direct Play" in integration options
   - This forces transcoding which may help compatibility

---

## Performance Issues

### High CPU/Memory Usage

**Symptoms:**
- Home Assistant using excessive resources
- Slow dashboard

**Solutions:**

1. **Increase scan interval:**
   - Default 10 seconds may be too frequent
   - Try 30 or 60 seconds

2. **Enable WebSocket:**
   - WebSocket reduces polling load
   - More efficient for real-time updates

3. **Check entity count:**
   - Many Emby sessions = many entities
   - Use "Ignored Devices" to filter unnecessary devices

### Slow Media Browsing

**Symptoms:**
- Browse Media takes long to load
- Timeouts when browsing large libraries

**Solutions:**

1. **Browse cache:**
   - Results are cached to improve performance
   - First load will be slower

2. **Large libraries:**
   - Use category filters (A-Z, Genre, Year)
   - Avoid browsing root of very large libraries

3. **Network speed:**
   - Slow network between HA and Emby affects browsing
   - Check network connectivity

---

## Getting Diagnostics

When reporting issues, include diagnostic information:

### Download Diagnostics

1. Go to **Settings** → **Devices & Services**
2. Find **Emby Media**
3. Click the three dots (⋮)
4. Click **Download Diagnostics**

This generates a JSON file containing:
- Integration configuration (API keys are redacted)
- Server information
- Connection status
- Active sessions
- Cache statistics

### Check Logs

1. Go to **Settings** → **System** → **Logs**
2. Filter for `embymedia` entries
3. Look for ERROR or WARNING messages

### Enable Debug Logging

Add to `configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.embymedia: debug
```

Restart Home Assistant and reproduce the issue.

---

## Reporting Issues

When opening a GitHub issue, please include:

1. **Home Assistant version**
2. **Emby Server version**
3. **Integration version**
4. **Diagnostics file** (download as described above)
5. **Relevant log entries** (with debug logging if possible)
6. **Steps to reproduce** the issue
7. **Expected vs actual behavior**

Open issues at: https://github.com/troykelly/homeassistant-emby/issues

---

## Common Error Messages

| Error | Cause | Solution |
|-------|-------|----------|
| `Cannot connect to host` | Network/firewall issue | Check connectivity, firewall rules |
| `401 Unauthorized` | Invalid API key | Regenerate API key |
| `403 Forbidden` | Permission denied | Check user permissions |
| `Connection reset` | Server closed connection | Check server status |
| `Session not found` | Client disconnected | Reopen Emby on device |
| `WebSocket closed` | Connection dropped | Check network stability |

---

## Still Having Issues?

If this guide didn't solve your problem:

1. Search [existing issues](https://github.com/troykelly/homeassistant-emby/issues)
2. Check [Home Assistant Community](https://community.home-assistant.io/)
3. [Open a new issue](https://github.com/troykelly/homeassistant-emby/issues/new) with full details
