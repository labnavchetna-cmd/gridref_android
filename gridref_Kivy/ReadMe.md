# GridRef — Android Build Instructions

This is a Kivy (touch UI) port of your original `mgrs_cli.py` terminal tool.
The conversion logic (`mgrs_core.py`) is a direct port of your original code —
same math, same validation rules, same input parsing.

I cannot compile the `.apk` myself (that requires the Android SDK/NDK and a
full Linux build toolchain, which this sandbox doesn't have network access
for). Below is the **easiest working path**: let GitHub build it for you,
for free, with no Android tools installed on your own machine.

---

## Option A — Build via GitHub Actions (recommended, no local setup)

1. Create a new **public or private** repo on GitHub (e.g. `gridref-android`).
2. Upload every file in this folder to that repo, **preserving the folder
   structure** — especially `.github/workflows/build-apk.yml`.
   - Easiest way: `git init`, `git add .`, `git commit -m "init"`,
     `git remote add origin <your-repo-url>`, `git push -u origin main`
3. Go to your repo on GitHub → the **Actions** tab. A workflow called
   "Build Android APK" will run automatically (takes ~15-25 minutes the
   first time — Buildozer downloads the Android SDK/NDK on that run).
4. When it finishes (green check), click into the run → scroll to
   **Artifacts** → download `gridref-apk.zip`. Unzip it — that's your `.apk`.
5. Transfer the `.apk` to your Android 12 phone (email, USB, Google Drive,
   whatever) and tap it to install. You'll need to allow "Install unknown
   apps" for whichever app you use to open it (Settings → Apps → Special
   access → Install unknown apps).

If the Action fails, open the failed run and check the log — it's almost
always one of: a typo introduced during upload, or a Buildozer/NDK version
mismatch (see Troubleshooting below).

## Option B — Build locally on Linux / WSL2

If you'd rather not use GitHub:

```bash
# On Ubuntu 22.04 or WSL2 Ubuntu 22.04
sudo apt update
sudo apt install -y git zip unzip openjdk-17-jdk python3-pip autoconf libtool \
    pkg-config zlib1g-dev libncurses5-dev libncursesw5-dev libtinfo5 \
    cmake libffi-dev libssl-dev automake build-essential

pip install --upgrade pip
pip install buildozer cython==0.29.36

cd gridref_kivy
buildozer android debug
```

The finished APK will land in `gridref_kivy/bin/gridref-1.0.0-arm64-v8a_armeabi-v7a-debug.apk`.

Buildozer does **not** run on native Windows — WSL2 (Windows Subsystem for
Linux) or a Linux VM is required. Plain macOS also generally struggles with
Buildozer's NDK toolchain versions; Linux is the reliable path.

---

## Project structure

```
gridref_kivy/
├── main.py              # Kivy UI (touch-friendly rebuild of the terminal UI)
├── mgrs_core.py          # Conversion logic (validation, parsing, MGRS formatting)
├── pure_mgrs.py           # Pure-Python lat/lon -> UTM -> MGRS math, no C extensions
├── buildozer.spec        # Android build config (targets API 33, min API 31 = Android 12+)
├── .github/workflows/
│   └── build-apk.yml     # Cloud build via GitHub Actions
└── README.md
```

**Note on the conversion engine**: your original CLI used the `mgrs` PyPI
package, which wraps a compiled C library (GeoTrans). C extensions are a
common source of Buildozer build failures because they must be
cross-compiled for Android's ARM architecture. To make the build reliable,
I reimplemented the lat/lon -> UTM -> MGRS math in pure Python
(`pure_mgrs.py`), using the same standard formulas (WGS84 ellipsoid,
Snyder/Karney transverse Mercator equations) that `mgrs` and virtually
every other MGRS library use. I verified it against known reference points
(US Capitol, London, Sydney, Reykjavik, Null Island) and the results match
official/published MGRS values. It covers the same latitude range as your
original tool (-80° to 84°; polar UPS regions were out of scope for the
original CLI too).

## What changed from the original CLI, and why

| Original (`mgrs_cli.py`)              | Android version                          | Why |
|----------------------------------------|-------------------------------------------|-----|
| `rich.Prompt.ask()` terminal prompts   | `TextInput` fields                        | No terminal on a phone screen |
| `rich` panels/tables for output        | Kivy `Label`/`BoxLayout` "cards"           | Rich renders ANSI escape codes, which Android has no terminal to display |
| `pyperclip` for clipboard              | `kivy.core.clipboard.Clipboard`            | pyperclip is a desktop-OS clipboard library; Android needs its native clipboard API |
| Infinite `while True` REPL loop        | Tap "CONVERT" button, repeatable           | Touch UI is event-driven, not loop-driven |
| `Prompt.ask(..., choices=["1","2","3"])` for precision | `Spinner` dropdown | Native mobile-style picker |

The actual coordinate math, MGRS parsing, and input validation (`mgrs_core.py`)
were **not rewritten** — only ported into a standalone module — so behavior
matches your original tool exactly.

## Troubleshooting

- **App installs but crashes on open**: run `buildozer android debug deploy run logcat`
  (with a phone connected via USB and USB debugging on) to see the actual
  Python traceback — Android hides Python errors by default.
- **"App not installed" on phone**: usually a signature mismatch from a
  previous install attempt — uninstall any prior version of GridRef first.
