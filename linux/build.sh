#!/usr/bin/env bash
set -euo pipefail

NAME="btotp"
SPEC="btotp.spec"
DIST="dist"
ARCHIVE_NAME="btotp-linux-x86_64"

echo "=== BetterTOTP Linux Binary Builder ==="
echo ""

# --- Step 1: Check dependencies ---
echo "[1/6] Checking dependencies..."
PYTHON=$(command -v python3 || command -v python)
PIP="$PYTHON -m pip"
$PIP install --quiet pyinstaller cryptography 2>/dev/null || {
    echo "ERROR: pip install failed. Ensure python3 and pip are installed."
    exit 1
}

# --- Step 2: Build with PyInstaller ---
echo "[2/6] Building with PyInstaller..."
pyinstaller --clean "$SPEC"

# --- Step 3: Strip debug symbols ---
echo "[3/6] Stripping debug symbols..."
if command -v strip &>/dev/null; then
    strip "$DIST/$NAME"
    echo "  Stripped $DIST/$NAME"
else
    echo "  strip not found, skipping"
fi

# --- Step 4: GPG sign ---
echo "[4/6] Signing with GPG..."
if command -v gpg &>/dev/null; then
    gpg --detach-sign --armor "$DIST/$NAME"
    echo "  Created $DIST/$NAME.asc"
else
    echo "  gpg not found, skipping signature"
fi

# --- Step 5: Stage release archive ---
echo "[5/6] Staging release archive..."
RELEASE_DIR="$DIST/release"
mkdir -p "$RELEASE_DIR"
cp "$DIST/$NAME" "$RELEASE_DIR/"
if [ -f "$DIST/$NAME.asc" ]; then
    cp "$DIST/$NAME.asc" "$RELEASE_DIR/"
fi
cp assets/bettertotp.desktop "$RELEASE_DIR/"
cp register-handler.sh "$RELEASE_DIR/"
cp README.md "$RELEASE_DIR/"

# --- Step 6: Create .tar.gz ---
echo "[6/6] Creating .tar.gz archive..."
cd "$DIST"
tar czf "${ARCHIVE_NAME}.tar.gz" -C release .
cd ..
mv "$DIST/${ARCHIVE_NAME}.tar.gz" "$DIST/"

echo ""
echo "=== Build Complete ==="
echo "  Binary:     $DIST/$NAME ($(du -h "$DIST/$NAME" | cut -f1))"
echo "  Signature:  $DIST/$NAME.asc"
echo "  Archive:    $DIST/$ARCHIVE_NAME.tar.gz"
echo ""
echo "To run:  ./$DIST/$NAME"
echo "Install: cp $DIST/$NAME ~/.local/bin/"
