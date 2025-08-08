#!/usr/bin/env bash
set -euo pipefail

# ------------ Pretty printing ------------
info()  { printf "\033[1;34m[i]\033[0m %s\n" "$*"; }
ok()    { printf "\033[1;32m[✓]\033[0m %s\n" "$*"; }
warn()  { printf "\033[1;33m[!]\033[0m %s\n" "$*"; }
err()   { printf "\033[1;31m[x]\033[0m %s\n" "$*" >&2; }

info "QR Local Decoder — macOS Quick Action setup"

# ------------ Paths / Platform ------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$SCRIPT_DIR"
info "Project dir: $PROJECT_DIR"

if [[ "$(uname -s)" != "Darwin" ]]; then
  err "This installer targets macOS (Automator Services)."
  exit 1
fi

# ------------ Python / venv ------------
if command -v python3 >/dev/null 2>&1; then
  PYTHON="python3"
elif command -v python >/dev/null 2>&1; then
  PYTHON="python"
else
  err "python3/python not found. Please install Python 3."
  exit 1
fi
info "Using Python: $PYTHON ($(command -v "$PYTHON"))"

VENV_DIR="$PROJECT_DIR/venv"
if [[ ! -d "$VENV_DIR" ]]; then
  info "Creating venv..."
  "$PYTHON" -m venv "$VENV_DIR"
else
  info "venv already exists — skipping creation."
fi

# shellcheck disable=SC1090
source "$VENV_DIR/bin/activate"

info "Installing requirements..."
if [[ -f "$PROJECT_DIR/requirements.txt" ]]; then
  pip install -r "$PROJECT_DIR/requirements.txt"
else
  warn "requirements.txt not found — skipping deps install."
fi

# ------------ Decoder script ------------
DECODER_SCRIPT="$PROJECT_DIR/qr_local_decoder.py"
if [[ ! -f "$DECODER_SCRIPT" ]]; then
  err "Decoder script not found: $DECODER_SCRIPT"
  exit 1
fi
info "Decoder script: $DECODER_SCRIPT"

# ------------ Prepare workflow ------------
SRC_WORKFLOW_DIR="$PROJECT_DIR/decode-qr-img-quick-action.workflow"
DEST_WORKFLOW_NAME="Decode QR img.workflow"
DEST_WORKFLOW_DIR="$PROJECT_DIR/$DEST_WORKFLOW_NAME"

if [[ ! -d "$SRC_WORKFLOW_DIR" ]]; then
  err "Source workflow not found: $SRC_WORKFLOW_DIR"
  exit 1
fi

info "Preparing workflow from template..."
rm -rf "$DEST_WORKFLOW_DIR"
cp -R "$SRC_WORKFLOW_DIR" "$DEST_WORKFLOW_DIR"

DOC="$DEST_WORKFLOW_DIR/Contents/document.wflow"
if [[ ! -f "$DOC" ]]; then
  err "document.wflow not found at $DOC"
  exit 1
fi

# ------------ Build COMMAND_STRING with PROJECT_DIR var ------------
read -r -d '' NEW_COMMAND <<EOF
#!/bin/zsh
set -e

# === CONFIG ===
PROJECT_DIR="${PROJECT_DIR}"

# === LOGIC ===
source "\$PROJECT_DIR/venv/bin/activate"

python "\$PROJECT_DIR/$(basename "$DECODER_SCRIPT")" "\$@" --copy
STATUS=\$?

if [ \$STATUS -eq 0 ]; then
  /usr/bin/osascript -e 'display notification "QR decoded. Link copied to clipboard." with title "QR Decoder"'
elif [ \$STATUS -eq 4 ]; then
  /usr/bin/osascript -e 'display notification "No QR found in the image." with title "QR Decoder"'
else
  /usr/bin/osascript -e "display notification \"Error. Exit code \$STATUS\" with title \"QR Decoder\""
fi

sleep 0.2
EOF

# Put the command text into a temp file for plistlib patch
TMP_CMD_FILE="$(mktemp)"
printf "%s" "$NEW_COMMAND" > "$TMP_CMD_FILE"

info "Patching COMMAND_STRING (+ enforcing /bin/zsh & 'as arguments')..."
"$PYTHON" - "$DOC" "$TMP_CMD_FILE" <<'PY'
import plistlib, sys, pathlib
doc = pathlib.Path(sys.argv[1])
cmd_file = pathlib.Path(sys.argv[2])
cmd = cmd_file.read_text()

with doc.open('rb') as f:
    pl = plistlib.load(f)

# Assume first action is "Run Shell Script"
action = pl['actions'][0]['action']
params = action['ActionParameters']

params['COMMAND_STRING'] = cmd
params['shell'] = '/bin/zsh'
# 1 = "as arguments", 0 = stdin
params['inputMethod'] = 1

with doc.open('wb') as f:
    plistlib.dump(pl, f)
PY
rm -f "$TMP_CMD_FILE"
ok "Workflow updated."

# ------------ Install (move) to Services ------------
SERVICES_DIR="$HOME/Library/Services"
INSTALL_TARGET="$SERVICES_DIR/$DEST_WORKFLOW_NAME"

info "Installing Quick Action to: $INSTALL_TARGET"
mkdir -p "$SERVICES_DIR"
rm -rf "$INSTALL_TARGET"
mv "$DEST_WORKFLOW_DIR" "$INSTALL_TARGET"
ok "Installed."

# ------------ Finish ------------
/usr/bin/osascript -e 'display notification "QR Quick Action installed" with title "QR Local Decoder"'
ok "Done. Finder → Right-click image → Quick Actions → \"Decode QR img\"."
