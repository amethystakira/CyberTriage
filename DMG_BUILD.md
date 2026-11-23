# Build the CyberTriage macOS DMG

This project builds an unsigned local macOS installer containing the React app
and the FastAPI service. The installer is a drag-to-Applications DMG. On first
launch, CyberTriage creates a per-user SQLite database, seeds the demo dataset,
and prompts you to create the initial administrator account. The demo includes
5 investigations, 8 harmless text evidence files, 10 findings, 5 analysis runs,
and related timeline events. The database and uploaded evidence live in
`~/Library/Application Support/CyberTriage/`; the app does not bundle or modify
the development database in this checkout. The application bundle remains
read-only.

## Build on an Apple Silicon Mac

Install Node.js 22+ and Python 3.13,
then run from the repository root:

```sh
npm install
python3.13 -m venv .venv-dmg
source .venv-dmg/bin/activate
python -m pip install -r backend/requirements.txt pyinstaller
npm run build:mac
```

The DMG is written to `dist/CyberTriage-1.0.0-arm64.dmg`. Run `npm run
build:mac` on an Intel Mac to produce the native Intel build. The app is not
code-signed or notarized by this local build; macOS may require the user to
approve opening it. Distribution outside a development/demo context should be
signed and notarized with the project's Developer ID credentials.

The DMG is a self-contained demo installation. At first launch, use the in-app
setup form to create the initial administrator account; the sample cases and
evidence are available after setup. Existing repository database files are not
bundled or modified.
