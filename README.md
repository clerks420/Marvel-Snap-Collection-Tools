# Marvel Snap Save Extractor

A lightweight desktop tool that analyzes your **Marvel Snap save files** and helps you understand:

- Which cards have the most boosters
- Which cards still need mastery progress
- Which cards are already maxed (and can be deprioritized)
- Variant counts per card
- Album completion progress

The app includes a simple graphical interface and works **offline** using your local Snap save data.

---

## ✨ Features

- Auto-loads Marvel Snap save files on Windows
- Multiple sorting options:
  - Boosters (highest → lowest)
  - Mastery (highest → lowest)
  - Mastery + Boosters (combined priority)
  - Versions that push **maxed mastery (30)** cards to the bottom
- Variant count per card
- Album completion tracking
- Clean, sortable table preview
- Export any report to CSV
- No Snap login, no API keys, no internet required

---

## 🖥️ Option 1: Using the Executable (Recommended)

If you downloaded the **prebuilt executable**, you do **not** need Python.

### Steps

1. Download the latest `.exe` from the **Releases** page.
2. Double-click the executable to launch it.
3. The app will attempt to auto-load your Snap save files from:

%USERPROFILE%\AppData\LocalLow\Second Dinner\SNAP\Standalone\States\nvprod\

4. If the files are found, you’re ready to go immediately.
5. If not, click **Browse…** and manually select:
- `CollectionState.json`
- `CharacterMasteryState.json`

6. Choose a report type, click **Generate Preview**, then **Export CSV** if desired.

That’s it — no setup required.

---

## 🐍 Option 2: Running from Source (Python)

This option is for users who want to modify the code or run it directly.

### Requirements

- Python **3.10+**
- pip

### Install Python

Download Python from:
https://www.python.org/downloads/

During installation:
- ✅ Check **“Add Python to PATH”**
- Complete the install

### Install Dependencies

From the project folder, run:

pip install pandas

Run the App

python snap_extractor_gui.py

The same GUI will launch.

📂 Where the Data Comes From

Marvel Snap stores local save state files on Windows at:

%USERPROFILE%\AppData\LocalLow\Second Dinner\SNAP\Standalone\States\nvprod\

This tool reads:

CollectionState.json (boosters, variants, albums)

CharacterMasteryState.json (mastery levels and XP)

No files are modified — the tool is read-only.

📊 Available Reports
Card Reports

Boosters (DESC) then Mastery

Boosters (DESC), Max Mastery (30) at Bottom

Mastery (DESC) then Boosters

Mastery + Boosters

Mastery + Boosters, Max Mastery (30) at Bottom

Other Reports

Variants per Card (most → least)

Albums by Completion (most complete → least)

🧠 How Sorting Works (Example)

If two cards have the same mastery level:

The one with more boosters is ranked higher.

If a card is already mastery 30:

It can be pushed to the bottom using the special sorting options, even if it has lots of boosters.

This helps prioritize where your boosters actually matter.

⚠️ Notes & Limitations

Artist names and variant artist breakdowns are not yet included

Variant IDs are shown (e.g. Venom_21) — future versions may add friendly names

Currently Windows-focused (auto-load path is Windows-specific)

❤️ Community & Contributions

This project is made for the Marvel Snap community.

If you’d like to:

Add artist metadata

Improve the UI

Add Mac/Linux support

Add new reports

Feel free to open a PR or issue.

📜 Disclaimer

This project is not affiliated with Second Dinner or Marvel Snap.
All game assets, names, and data belong to their respective owners.

---

## Source Code

The Python source code is located in the `src/` directory.

Most users should download the standalone executable from the Releases page.


