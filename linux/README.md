# BetterTOTP — Linux Binary

Single-file executable for Linux (x86_64). No Python or pip required.

## Usage

```bash
./btotp                          # GUI if display available, else CLI
./btotp code -a my-account       # CLI mode (explicit)
./btotp otpauth://totp/...       # Import otpauth URI
```

## Installation

```bash
cp btotp ~/.local/bin/
```

## Verification

```bash
gpg --verify btotp.asc btotp
```

## Register as otpauth:// handler

```bash
chmod +x register-handler.sh
./register-handler.sh
```

Then clicking an `otpauth://` link in your browser imports the account.

## Build from source

See `build.sh` — requires Python 3.10+ and pip.
