# SOCIAL MEDIA AUTO CONTENT SYSTEM - BETA VERSIONS

## TIGA VERSI TANPA NUELINK + CONFIGURATION SYSTEM

---

# BETA 1: PYTHON UI (Tkinter Desktop App)

## File: `beta1_python_ui.py`

Post to social media (placeholder + open folder)	✅
---

# BETA 2: WEBAPP UI (Flask)

## File: `beta2_webapp.py`

Social media post (placeholder)	⚠️ (perlu browser automation)|
---

## File: `templates/beta2_dashboard.html`

---

# BETA 3: WINDOWS CMD/POWERSHELL UI

## File: `beta3_windows_cli.ps1`

---

## FILE CONFIGURATION UNTUK ON/OFF FITUR

## File: `config.json` (Default)

---

## CARA MENJALANKAN

### Beta 1 (Python UI)

```bash
# Install dependencies
pip install tkinter pillow requests

# Run
python beta1_python_ui.py
```

### Beta 2 (Web App)

```bash
# Install dependencies
pip install flask flask-cors

# Run
python beta2_webapp.py

# Open browser at http://localhost:5000
```

### Beta 3 (Windows PowerShell)

```powershell
# Interactive mode
.\beta3_windows_cli.ps1 interactive

# Generate single video
.\beta3_windows_cli.ps1 generate -Template zodiac_dark -Zodiac leo -Text1 "Leo Energy" -Text2 "Shine Bright"

# Batch generate
.\beta3_windows_cli.ps1 batch

# Diagnostics
.\beta3_windows_cli.ps1 diagnostics
```

---

## RINGKASAN KETIGA VERSI

| Fitur | Beta 1 (Python UI) | Beta 2 (Web App) | Beta 3 (CLI) |
|-------|-------------------|------------------|--------------|
| Interface | Tkinter Desktop | Web Browser | PowerShell/CMD |
| Config UI | Yes | Yes | Menu-based |
| On/Off Feature Toggles | Yes | Yes | Via config file |
| Video Generation | Yes | Yes | Yes |
| Batch Processing | Yes | Yes | Yes |
| Queue System | Yes | Yes | Yes |
| Social Media Post | Planned | Basic | Manual |
| Schedule | Yes | Basic | Via Task Scheduler |
| Cross-platform | Yes | Yes | Windows only |
| No External APIs | Yes | Yes | Yes |
| Config File | config.json | config.json | config.json |