# Installation Guide

Get Emby Media for Home Assistant up and running in minutes.

## Prerequisites

| Requirement | Minimum Version |
|-------------|----------------|
| **Home Assistant** | 2025.11.3+ |
| **Emby Server** | 4.9.1.90+ |
| **Network** | HA must reach Emby server |

## Installation

### Option 1: HACS (Recommended)

[HACS](https://hacs.xyz/) keeps your integration updated automatically.

#### If you don't have HACS installed

Follow the [official HACS installation guide](https://hacs.xyz/docs/setup/download) first.

#### Install Emby Media

1. Open **HACS** in Home Assistant
2. Click the ⋮ menu → **Custom repositories**
3. Add repository:
   ```
   https://github.com/troykelly/homeassistant-emby
   ```
4. Select **Integration** as category → **Add**
5. Search for **"Emby Media"** → **Download**
6. Select latest version → **Download**
7. **Restart Home Assistant**

### Option 2: Manual Installation

1. Download `embymedia.zip` from the [Releases page](https://github.com/troykelly/homeassistant-emby/releases)
2. Extract the `embymedia` folder
3. Copy to your `config/custom_components/` directory
4. **Restart Home Assistant**

<details>
<summary>📁 Expected folder structure</summary>

```
config/
├── configuration.yaml
├── secrets.yaml
└── custom_components/
    └── embymedia/
        ├── __init__.py
        ├── manifest.json
        ├── api.py
        ├── config_flow.py
        └── ... (other files)
```

</details>

## Verify Installation

After restarting:

1. Go to **Settings** → **Devices & Services**
2. Click **+ Add Integration**
3. Search for **"Emby Media"**

If you see it in the list, installation succeeded! Continue to [Configuration](CONFIGURATION.md).

---

## Troubleshooting Installation

### Integration Not Showing Up

**Check the logs:**
- **Settings** → **System** → **Logs**
- Look for errors mentioning `embymedia` or `custom_components`

**Verify files exist:**
```
custom_components/embymedia/__init__.py
custom_components/embymedia/manifest.json
```

**Check file permissions (Linux):**
```bash
chmod -R 755 custom_components/embymedia
```

**Clear browser cache:**
- Hard refresh: `Ctrl+Shift+R` (Windows/Linux) or `Cmd+Shift+R` (Mac)
- Try incognito/private mode

**Restart again:**
- Sometimes a second restart is needed

### Version Compatibility

| Home Assistant | Emby Media | Emby Server |
|---------------|------------|-------------|
| 2025.11.3+ | 0.1.0+ | 4.9.1.90+ |

Older Home Assistant versions may not be supported.

---

## Getting Help

1. Check [existing issues](https://github.com/troykelly/homeassistant-emby/issues)
2. Search [Home Assistant Community Forums](https://community.home-assistant.io/)
3. [Open a new issue](https://github.com/troykelly/homeassistant-emby/issues/new?template=bug_report.md) with:
   - Your Home Assistant version
   - Your Emby Server version
   - Installation method used
   - Relevant log entries

---

## Next Steps

- **[Configuration](CONFIGURATION.md)** — Connect to your Emby server
- **[Automations](AUTOMATIONS.md)** — Create powerful automations
- **[Services](SERVICES.md)** — Explore available service calls
