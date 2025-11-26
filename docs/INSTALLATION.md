# Installation Guide

This guide walks you through installing the Emby Media integration for Home Assistant.

## Prerequisites

Before installing, ensure you have:

- **Home Assistant** version 2025.11.3 or later
- **Emby Server** version 4.9.1.90 or later running and accessible
- **Network access** from Home Assistant to your Emby server
- An **Emby API key** (we'll create one during setup)

## Installation Methods

### Method 1: HACS (Recommended)

[HACS](https://hacs.xyz/) (Home Assistant Community Store) is the easiest way to install and keep the integration updated.

#### Step 1: Install HACS (if not already installed)

If you don't have HACS installed, follow the [official HACS installation guide](https://hacs.xyz/docs/setup/download).

#### Step 2: Add Custom Repository

1. Open Home Assistant
2. Navigate to **HACS** in the sidebar
3. Click the three dots menu (⋮) in the top right
4. Select **Custom repositories**
5. Enter the repository URL:
   ```
   https://github.com/troykelly/homeassistant-emby
   ```
6. Select **Integration** as the category
7. Click **Add**

#### Step 3: Install the Integration

1. In HACS, click **+ Explore & Download Repositories**
2. Search for **"Emby Media"**
3. Click on the integration
4. Click **Download**
5. Select the latest version
6. Click **Download** again

#### Step 4: Restart Home Assistant

1. Go to **Settings** → **System** → **Restart**
2. Click **Restart** and wait for Home Assistant to come back online

### Method 2: Manual Installation

If you prefer not to use HACS, you can install manually.

#### Step 1: Download the Integration

1. Go to the [Releases page](https://github.com/troykelly/homeassistant-emby/releases)
2. Download the latest `embymedia.zip` file
3. Extract the contents

#### Step 2: Copy Files

1. Locate your Home Assistant configuration directory
   - Usually `/config` in Docker or `/home/homeassistant/.homeassistant/`
2. Create a `custom_components` folder if it doesn't exist
3. Copy the `embymedia` folder into `custom_components`

Your directory structure should look like:

```
config/
├── configuration.yaml
├── secrets.yaml
├── custom_components/
│   └── embymedia/
│       ├── __init__.py
│       ├── manifest.json
│       ├── api.py
│       ├── config_flow.py
│       ├── coordinator.py
│       ├── media_player.py
│       └── ... (other files)
```

#### Step 3: Restart Home Assistant

1. Go to **Settings** → **System** → **Restart**
2. Click **Restart**

## Verifying Installation

After restarting, verify the integration is available:

1. Go to **Settings** → **Devices & Services**
2. Click **+ Add Integration**
3. Search for **"Emby Media"**

If you see "Emby Media" in the list, the installation was successful! Continue to [Configuration](CONFIGURATION.md).

## Troubleshooting Installation

### Integration Not Showing Up

If "Emby Media" doesn't appear in the integration list:

1. **Check the logs**:
   - Go to **Settings** → **System** → **Logs**
   - Look for errors related to `embymedia` or `custom_components`

2. **Verify file placement**:
   ```
   custom_components/embymedia/__init__.py  # This file must exist
   custom_components/embymedia/manifest.json  # This file must exist
   ```

3. **Check file permissions**:
   - All files should be readable by Home Assistant
   - On Linux: `chmod -R 755 custom_components/embymedia`

4. **Clear browser cache**:
   - Hard refresh your browser (Ctrl+Shift+R or Cmd+Shift+R)
   - Try a different browser or incognito mode

5. **Restart again**:
   - Sometimes a second restart is needed

### Version Compatibility

| Home Assistant Version | Emby Media Version | Emby Server Version |
|----------------------|-------------------|---------------------|
| 2025.11.3+ | 0.1.0+ | 4.9.1.90+ |

If you're running an older version of Home Assistant, you may need to upgrade before using this integration.

### Getting Help

If you're still having issues:

1. Check the [GitHub Issues](https://github.com/troykelly/homeassistant-emby/issues) for known problems
2. Search the [Home Assistant Community Forums](https://community.home-assistant.io/)
3. [Open a new issue](https://github.com/troykelly/homeassistant-emby/issues/new) with:
   - Your Home Assistant version
   - Your Emby Server version
   - Installation method used
   - Relevant log entries

## Next Steps

Once installed, proceed to:

1. **[Configuration](CONFIGURATION.md)** - Set up the integration
2. **[Automations](AUTOMATIONS.md)** - Create automations with your Emby media players
