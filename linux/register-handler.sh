#!/usr/bin/env bash
# Register BetterTOTP as the handler for otpauth:// URIs
# Run this once after installing the btotp binary.
set -euo pipefail

BIN="${1:-btotp}"
DESKTOP_FILE="bettertotp.desktop"

if ! command -v xdg-mime &>/dev/null; then
    echo "ERROR: xdg-mime not found. Are you on Linux with xdg-utils installed?"
    exit 1
fi

# Install desktop file to user's applications directory
mkdir -p ~/.local/share/applications/
cp "$DESKTOP_FILE" ~/.local/share/applications/

# Update the Exec path in the desktop file to point to the actual binary
BIN_PATH=$(command -v "$BIN" || echo "$BIN")
sed -i "s|^Exec=.*|Exec=$BIN_PATH %u|" ~/.local/share/applications/bettertotp.desktop

# Register MIME type
xdg-mime default bettertotp.desktop x-scheme-handler/otpauth

echo "Registered $BIN_PATH as handler for otpauth:// URIs"
echo "Clicking an otpauth:// link will now open BetterTOTP."
