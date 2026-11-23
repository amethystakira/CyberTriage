# Build the CyberTriage macOS DMG

This project builds an unsigned local macOS installer containing the React app
and the FastAPI service. The installer is a drag-to-Applications DMG. On first
launch, CyberTriage creates an empty per-user SQLite database and prompts the
user to create the initial administrator account. No demo investigations,
evidence, findings, analysis runs, or timeline events are seeded in the
packaged app. Development runs continue to seed demo data. The database and
uploaded evidence live in `~/Library/Application Support/CyberTriage/`; the app
does not bundle or modify the development database in this checkout. The
application bundle remains read-only.

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

At first launch, use the in-app setup form to create the initial administrator
account, then create investigations and add evidence in the empty workspace.
Existing repository database files are not bundled or modified. Existing data
in a user's Application Support folder is preserved when the app is upgraded.
