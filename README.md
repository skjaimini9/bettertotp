# BetterTOTP

[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Android](https://img.shields.io/badge/Android-3DDC84?logo=android&logoColor=white)](android/)
[![Linux](https://img.shields.io/badge/Linux-FCC624?logo=linux&logoColor=black)](linux/)
[![API](https://img.shields.io/badge/API-FastAPI-009688?logo=fastapi&logoColor=white)](web/)

A TOTP-based time-varying code generator with alphanumeric and special character output. Uses HMAC-SHA512 (or SHA1/SHA256) to produce 12-character codes (configurable length) from a 75-character alphabet (`A-Z a-z 0-9 !@#$%&*-_+=?~`), with an encrypted vault for storing secrets. A native Android app is available in `android/`, and a standalone Linux binary in `linux/`.

---

## Features

- **Configurable TOTP** — Choose hash algorithm (SHA1, SHA256, SHA512), code length, and time step
- **Encrypted vault** — Store multiple named secrets in `~/.config/btotp/vault.json` encrypted with AES-256-GCM (PBKDF2-derived key from master password)
- **otpauth URI support** — Import accounts from standard `otpauth://totp/...` URIs (compatible with Bitwarden, Authy, Google Authenticator, etc.)
- **QR code display** — Render QR codes directly in the terminal for mobile enrollment
- **Clipboard copy** — Copy codes to clipboard (supports pyperclip, xclip, xsel, pbcopy)
- **Shell completions** — Generate tab-completion scripts for bash, zsh, and fish
- **Export/Import vault** — JSON-based backup and restore
- **User config** — Persistent defaults via `~/.config/btotp/config.json`
- **Android app** — Native Kotlin app with Master Password or Biometric vault modes, Material 3 UI
- **Linux binary** — Standalone executable (no Python needed), Tkinter GUI if available, CLI fallback, registers as `otpauth://` handler
- **Web API** — FastAPI microservice for TOTP enrollment and verification, stateless, ready to integrate into any website backend
- **PAM 2FA** — C-based PAM module (`pam_btotp.so`) for Linux SSH/sudo/system-login 2FA, reads secrets from `~/.btotp`

---

## Installation

```bash
pip install bettertotp

# Optional feature groups:
pip install bettertotp[clipboard]   # clipboard support (pyperclip)
pip install bettertotp[qr]          # QR code display
pip install bettertotp[completion]  # shell tab-completion
pip install bettertotp[all]         # all optional features
```

### From source

```bash
git clone https://github.com/skjaimini9/bettertotp.git
cd bettertotp
pip install .
```

### Android app

Build the native Android APK from the `android/` directory:

```bash
# 1. Generate a signing keystore (one-time)
keytool -genkey -v -keystore ~/.android/bettertotp-release.jks \
  -alias bettertotp -keyalg RSA -keysize 2048 -validity 10000

# 2. Install Android SDK and set ANDROID_HOME

# 3. Download the Gradle wrapper
cd android
gradle wrapper

# 4. Build the release APK
BTOTP_KEYSTORE_PATH=~/.android/bettertotp-release.jks \
BTOTP_STORE_PASSWORD=your-keystore-password \
BTOTP_KEY_ALIAS=bettertotp \
BTOTP_KEY_PASSWORD=your-key-password \
./gradlew assembleRelease

# 5. Locate the signed APK
ls app/build/outputs/apk/release/app-release.apk

# 6. GPG-sign the APK for distribution
gpg --detach-sign --armor app/build/outputs/apk/release/app-release.apk
```

The Android app is a native Kotlin + Jetpack Compose application with two vault modes:
- **Master Password** — PBKDF2 + AES-256-GCM (identical algorithm to the CLI version)
- **Biometric** — Android Keystore-backed, unlocks with fingerprint or device PIN

### Linux binary

Build the standalone executable from the `linux/` directory:

```bash
# 1. Generate a GPG signing key (one-time, if signing releases)
gpg --full-generate-key

# 2. Install dependencies
pip install pyinstaller cryptography

# 3. Build the binary and release archive
cd linux
chmod +x build.sh
./build.sh

# 4. Locate the outputs
ls dist/btotp                          # single-file binary
ls dist/btotp-linux-x86_64.tar.gz      # release archive
```

The binary works on any Linux distro with glibc ≥ 2.28 (Debian 10+, Ubuntu 18.04+, Fedora 30+, Arch). It adapts to your environment:

- **With a display** → Tkinter GUI window (unlock → live code list → add/copy/delete)
- **Without a display** → Falls back to the CLI (same as `btotp` from pip)
- **`btotp otpauth://totp/...`** → Imports the URI directly (GUI or CLI)
- **Register as URI handler** → `./register-handler.sh` enables one-click import from a browser

### Web backend API

A stateless FastAPI microservice for integrating BetterTOTP into any website backend.

```bash
# 1. Install dependencies
cd web
pip install -r requirements.txt

# 2. Start the server
uvicorn main:app --host 0.0.0.0 --port 8000

# 3. Enroll a new user
curl -X POST http://localhost:8000/api/enroll \
  -H "Content-Type: application/json" \
  -d '{"account": "user@example.com", "issuer": "MyApp"}'

# 4. Verify a TOTP code at login
curl -X POST http://localhost:8000/api/verify \
  -H "Content-Type: application/json" \
  -d '{"secret_hex": "<from step 3>", "code": "<user typed>"}'
```

**Integration flow:**
1. User enables 2FA → `POST /api/enroll` → store `secret_hex` in your DB → render QR from `uri`
2. User logs in → `POST /api/verify` with the stored `secret_hex` → if `valid: true`, allow access

The API is stateless — your backend owns the secret storage. See `web/README.md` for full documentation.

### Linux PAM module

A C-based PAM module for 2FA on SSH, sudo, and other PAM-aware services.

```bash
# 1. Build the module
cd linux/pam
make

# 2. Install (requires root)
sudo make install

# 3. Enroll a vault account for system login
btotp enroll my-account

# 4. Add to /etc/pam.d/sshd (or other service)
auth required pam_btotp.so nullok
```

The module reads the secret from `~/.btotp` (created by `btotp enroll`). Supports `nullok` (skip 2FA if no `~/.btotp` exists), custom secret path, time window, and debug logging. See `linux/pam/README.md` for full documentation.

---

## Quick Start

### 1. Create a vault

```bash
btotp init
```

You'll be prompted for a master password. This creates `~/.config/btotp/vault.json`.

### 2. Add an account

```bash
# Generate a random secret:
btotp add my-account --generate

# Or provide an existing hex secret:
btotp add my-account -s "a1b2c3d4..."

# Or import from an otpauth:// URI:
btotp import-uri "otpauth://totp/Example:user@example.com?secret=JBSWY3DPEHPK3PXP&issuer=Example"

# Or provide a base32 secret:
btotp add my-account --b32 "JBSWY3DPEHPK3PXP"
```

### 3. Get a code

```bash
btotp code -a my-account
```

### 4. List all accounts

```bash
btotp list
```

Output:
```
  my-account  3vMU-DiSZn0n  (12c / 45s)
  github      W078kA**ytRu  (12c / 45s)
```

---

## CLI Reference

### `btotp generate-secret`

Generate a new random secret key (64 bytes by default).

```
btotp generate-secret [-o FILE] [-f {hex,b32}] [--raw] [--qr]
```

| Flag | Description |
|---|---|
| `-o, --output` | Write secret to file instead of stdout |
| `-f, --format` | Output format: `hex` (default, chunked) or `b32` |
| `--raw` | Output raw hex (no spaces, lowercase) — safe for copy-paste |
| `--qr` | Display a QR code for the generated secret (useful for mobile enrollment) |

### `btotp code`

Generate a TOTP code from a secret or vault account.

```
btotp code [-s SECRET | -a ACCOUNT] [-w] [--copy] [--algo ALGO] [--length N] [--step N]
```

| Flag | Description |
|---|---|
| `-s, --secret` | Secret key as a hex string |
| `-a, --account` | Account name in the vault |
| `-w, --watch` | Watch mode — refresh periodically (press Ctrl+C to stop) |
| `--copy` | Copy the code to clipboard instead of stdout |
| `--algo, --algorithm` | Hash algorithm: `sha1`, `sha256`, `sha512` (default: `sha512`) |
| `--length` | Code length in characters (default: 12) |
| `--step` | Time step in seconds (default: 45) |

### `btotp verify`

Verify a TOTP code against a secret or vault account.

```
btotp verify (-s SECRET | -a ACCOUNT) -c CODE [-n WINDOW] [--algo ALGO] [--length N] [--step N]
```

| Flag | Description |
|---|---|
| `-s, --secret` | Secret key as a hex string |
| `-a, --account` | Account name in the vault |
| `-c, --code` | Code to verify |
| `-n, --window` | Time drift window (default: 1 step in each direction) |
| `--algo, --algorithm` | Hash algorithm |
| `--length` | Code length |
| `--step` | Time step |

Exits with status 0 if valid, 1 if invalid.

### `btotp init`

Create a new encrypted vault.

```
btotp init
```

Prompts for a master password (and confirmation). Creates `~/.config/btotp/vault.json`.

### `btotp add`

Add an account to the vault.

```
btotp add NAME [-s SECRET] [--b32 B32] [-u URI] [-g] [-i ISSUER] [--algo ALGO] [--digits N] [--period N]
```

| Argument | Description |
|---|---|
| `NAME` | Account name (required) |
| `-s, --secret` | Secret key as a hex string |
| `--b32` | Secret key as a base32 string |
| `-u, --uri` | Import from an `otpauth://` URI |
| `-g, --generate` | Generate a new random secret |
| `-i, --issuer` | Issuer name (e.g. "GitHub", "Google") |
| `--algo, --algorithm` | Hash algorithm (default: `sha512`) |
| `--digits` | Code length (default: 12) |
| `--period` | Time step in seconds (default: 45) |

### `btotp list`

List all accounts in the vault with their current TOTP codes.

```
btotp list
```

### `btotp show`

Show the current TOTP code for a specific account.

```
btotp show NAME [--copy]
```

| Flag | Description |
|---|---|
| `NAME` | Account name |
| `--copy` | Copy the code to clipboard |

### `btotp remove`

Remove an account from the vault.

```
btotp remove NAME
```

### `btotp rename`

Rename an account in the vault.

```
btotp rename OLD_NAME NEW_NAME
```

### `btotp import-uri`

Import an account from an `otpauth://totp/...` URI.

```
btotp import-uri URI [-n NAME]
```

| Argument | Description |
|---|---|
| `URI` | The full `otpauth://totp/...` URI |
| `-n, --name` | Account name (defaults to the label from the URI) |

### `btotp export`

Export the vault as plaintext JSON (secrets are visible — handle with care).

```
btotp export [-o FILE]
```

| Flag | Description |
|---|---|
| `-o, --output` | Write to file instead of stdout |

### `btotp import`

Import accounts from a JSON file or stdin.

```
btotp import [FILE]
```

| Argument | Description |
|---|---|
| `FILE` | JSON file to import (reads from stdin if omitted) |

### `btotp uri`

Generate an `otpauth://totp/...` URI for a vault account (for mobile enrollment).

```
btotp uri NAME [--qr]
```

| Flag | Description |
|---|---|
| `NAME` | Account name |
| `--qr` | Display the URI as a QR code in the terminal |

### `btotp completion`

Generate shell completion script.

```
btotp completion {bash,zsh,fish}
```

**Usage:**

```bash
# Bash
source <(btotp completion bash)

# Zsh
autoload -U bashcompinit && bashcompinit && source <(btotp completion zsh)

# Fish
btotp completion fish | source
```

Requires `argcomplete` (`pip install bettertotp[completion]`).

### `btotp config`

View or modify persistent configuration.

```
btotp config [--show] [--set KEY=VALUE]
```

| Flag | Description |
|---|---|
| `--show` | Display current configuration |
| `--set` | Set a configuration value |

**Available keys:**

| Key | Type | Default | Description |
|---|---|---|---|
| `time_step` | int | 45 | Default time step in seconds |
| `code_length` | int | 12 | Default code length in characters |
| `hash_algo` | string | `"sha512"` | Default hash algorithm |
| `clipboard` | bool | `false` | Always copy codes to clipboard |

Example:

```bash
btotp config --set time_step=30
btotp config --set code_length=8
btotp config --show
```

### `btotp enroll`

Enable 2FA for system login (SSH, sudo). Extracts the secret from a vault account to `~/.btotp` for the PAM module.

```
btotp enroll NAME
```

| Argument | Description |
|---|---|
| `NAME` | Account name in the vault to enroll |

### `btotp unenroll`

Disable 2FA for system login by removing `~/.btotp`.

```
btotp unenroll
```

### `btotp help`

Show help for any command.

```
btotp help [COMMAND]
```

Examples:

```bash
btotp help
btotp help code
btotp help list
```

---

## Python API

### `generate_code(key_bytes, t=None, algorithm="sha512", code_length=12, time_step=45)`

Generate a TOTP code.

```python
from btotp import generate_code

code = generate_code(b"your-secret-key")
code = generate_code(b"secret", algorithm="sha256", code_length=8, time_step=30)
```

### `verify_code(key_bytes, code, window=1, algorithm="sha512", code_length=12, time_step=45)`

Verify a TOTP code within a time window.

```python
from btotp import verify_code

valid = verify_code(b"secret", code)
valid = verify_code(b"secret", code, algorithm="sha256", code_length=8)
```

### `generate_code_at(key_bytes, timestamp, ...)`

Generate a code for a specific Unix timestamp.

```python
from btotp import generate_code_at

code = generate_code_at(b"secret", 1000000, time_step=30)
```

### `generate_secret(length=64)`

Generate a cryptographically random secret.

```python
from btotp import generate_secret

secret = generate_secret()      # 64 random bytes
secret = generate_secret(32)    # 32 random bytes
```

### `Vault`

Encrypted vault for storing multiple secrets.

```python
from btotp import Vault

vault = Vault()
vault.unlock("master-password")
vault.add("email", secret.hex(), issuer="Google")
code = vault.code("email")
accounts = vault.list_accounts()
vault.remove("email")
```

**Methods:**

| Method | Description |
|---|---|
| `exists()` | Check if vault file exists |
| `create(password)` | Create a new vault |
| `unlock(password)` | Unlock an existing vault |
| `add(name, secret, ...)` | Add an account |
| `remove(name)` | Remove an account |
| `rename(old, new)` | Rename an account |
| `get(name)` | Get account details |
| `list_accounts()` | List all accounts |
| `code(name)` | Generate current code for account |
| `export_json()` | Export vault as JSON string |
| `import_json(data)` | Import accounts from JSON string |

### `parse_otpauth(uri)`

Parse an `otpauth://totp/...` URI into its components.

```python
from btotp import parse_otpauth

result = parse_otpauth("otpauth://totp/Example:user@example.com?secret=JBSWY3DPEHPK3PXP")
# {
#   "secret": "...",     # hex-encoded secret
#   "issuer": "Example",
#   "account": "user@example.com",
#   "algorithm": "sha1",
#   "digits": 12,
#   "period": 45,
# }
```

### `generate_uri(account, secret_hex, issuer="", ...)`

Generate an `otpauth://totp/...` URI.

```python
from btotp import generate_uri

uri = generate_uri("myaccount", secret.hex(), issuer="MyApp",
                   algorithm="sha256", digits=8, period=30)
```

---

## Configuration

### Vault file

Encrypted vault at `~/.config/btotp/vault.json`. The file contains:

```json
{
  "version": 1,
  "salt": "<base64>",
  "nonce": "<base64>",
  "data": "<AES-256-GCM encrypted, base64-encoded JSON blob>"
}
```

- **Encryption**: AES-256-GCM with random 12-byte nonce
- **Key derivation**: PBKDF2-HMAC-SHA256, 600,000 iterations, random 16-byte salt
- **Plaintext format** (when decrypted):

```json
{
  "accounts": {
    "my-account": {
      "secret": "a1b2c3d4...",
      "issuer": "Example",
      "algorithm": "sha512",
      "digits": 12,
      "period": 45
    }
  }
}
```

### User config

Persistent defaults at `~/.config/btotp/config.json`:

```json
{
  "time_step": 30,
  "code_length": 8,
  "hash_algo": "sha256",
  "clipboard": true
}
```

---

## Security Considerations

- The vault master password is the single point of failure. Choose a strong password.
- `btotp export` outputs **plaintext JSON** including all secrets. Handle exports securely.
- The vault file itself is encrypted with AES-256-GCM, but the encryption strength depends on your master password.
- PBKDF2 iterations are set to 600,000 (OWASP 2023 recommendation for SHA-256).
- Secret keys default to 64 bytes (512 bits) of random data via `secrets.token_bytes()`.

---

## Differences from Standard TOTP (RFC 6238)

| Aspect | Standard TOTP | BetterTOTP |
|---|---|---|
| Output | 6–8 decimal digits | 12 alphanumeric+special characters |
| Alphabet | `0-9` (10 chars) | `A-Z a-z 0-9 !@#$%&*-_+=?~` (75 chars) |
| Default hash | SHA-1 | SHA-512 |
| Default time step | 30 seconds | 45 seconds |
| Code generation | Dynamic truncation + modulo 10^N | Byte encoding into 75-char alphabet |
| Secret size | 10–20 bytes (80–160 bits) recommended | 64 bytes (512 bits) default |

---

## Changelog

### v1.0.0

- **Android app** — Native Kotlin + Jetpack Compose APK in `android/`
- Dual vault modes: Master Password (PBKDF2 + AES-256-GCM) or Biometric (Android Keystore)
- TOTP core reimplemented in pure Kotlin (HMAC-SHA1/256/512, 75-char charset)
- Material 3 UI with dynamic color, navigation, and auto-refreshing codes
- **Linux binary** — PyInstaller-based standalone executable in `linux/`
- Tkinter GUI with unlock, live code list, add/copy/delete
- Automatic GUI/CLI fallback based on display availability
- `otpauth://` URI handler registration via xdg-mime
- **Web API** — FastAPI microservice for website backend integration in `web/`
- Stateless enrollment and verification endpoints (non-standard BetterTOTP algorithm)
- CORS configurable, ready for any web framework
- FOSS — MIT License. Author: Shri Kant

### v0.2.0

- Configurable hash algorithm (`sha1`, `sha256`, `sha512`)
- Configurable code length and time step
- Encrypted vault (`btotp init`, `add`, `list`, `show`, `remove`, `rename`)
- `otpauth://totp/...` URI import (`btotp import-uri`)
- URI generation with optional QR display (`btotp uri --qr`)
- Clipboard copy support (`btotp code --copy`, `btotp show --copy`)
- User configuration (`btotp config`)
- Vault export/import (`btotp export`, `btotp import`)
- Shell completion scripts (`btotp completion`)
- `btotp help` subcommand

### v0.1.0

- Initial release
- `btotp generate-secret`, `btotp code`, `btotp verify`
- HMAC-SHA512 with 12-char codes, 45-second time step
- Watch mode (`--watch`)

---

## License

MIT
