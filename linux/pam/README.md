# BetterTOTP — PAM Module for Linux 2FA

A PAM module that adds two-factor authentication to Linux system login (SSH, sudo, display managers) using BetterTOTP's non-standard TOTP algorithm.

## Algorithm

| Parameter | Value |
|-----------|-------|
| Hash | HMAC-SHA512 |
| Charset | `A-Z a-z 0-9 !@#$%&*-_+=?~` (75 chars) |
| Code length | 12 characters |
| Time step | 45 seconds |
| Secret size | 64 bytes (512 bits) |

## Installation

### 1. Build the PAM module

```bash
cd linux/pam
make
```

### 2. Install the module

```bash
sudo make install
```

This copies `pam_btotp.so` to `/lib/security/` (or the appropriate directory for your system).

### 3. Set up your vault

```bash
btotp init
btotp add my-account -g
```

### 4. Enroll for system 2FA

```bash
btotp enroll my-account
```

This extracts the secret from your vault and writes it to `~/.btotp` (plaintext, 0600 permissions).

### 5. Configure PAM

Add to `/etc/pam.d/sshd`:

```
# Standard password auth
auth    required    pam_unix.so     nullok_secure

# BetterTOTP 2FA
auth    required    pam_btotp.so    nullok

# Account checks
account required    pam_unix.so
```

### 6. Test

```bash
pamtester sshd $(whoami) authenticate
```

## Usage

### Enroll an account

```bash
btotp enroll my-account
```

### Unenroll (disable 2FA)

```bash
btotp unenroll
```

### Get a code for login

```bash
btotp show my-account
# → ZijRG1F1BzpS
```

## Module Arguments

| Argument | Default | Description |
|----------|---------|-------------|
| `nullok` | off | Allow users without `~/.btotp` to skip 2FA |
| `debug` | off | Log debug messages to syslog |
| `secret=/path` | `~/.btotp` | Custom secret file location |
| `window=N` | 1 | Time drift window (±N steps) |
| `time_step=N` | 45 | Time step in seconds |
| `code_length=N` | 12 | Code length in characters |

### Examples

```bash
# Allow users without 2FA to skip
auth required pam_btotp.so nullok

# Strict mode (all users must have 2FA)
auth required pam_btotp.so

# Custom window for time drift
auth required pam_btotp.so window=2

# Debug logging
auth required pam_btotp.so nullok debug
```

## Security

### Secret file permissions

The `~/.btotp` file must have:
- Permissions: `0600` (owner read/write only)
- Owner: Must match the authenticating user
- Not a symlink

The PAM module validates these permissions before reading the file.

### Privilege management

The module drops to the user's privileges when reading `~/.btotp`, then restores root privileges. This prevents root from reading arbitrary user files.

### Brute-force protection

The TOTP code is 12 characters from a 75-character alphabet, giving ~74.7 bits of entropy. With a 45-second time window, brute-force is infeasible.

For additional protection, consider combining with `pam_faillock.so`:

```
auth required pam_faillock.so preauth deny=5 unlock_time=900
auth required pam_btotp.so nullok
auth [default=die] pam_faillock.so authfail deny=5 unlock_time=900
```

## Troubleshooting

### "No secret file for user"

Run `btotp enroll <account-name>` to create `~/.btotp`.

### "Secret file has invalid permissions"

Fix permissions:
```bash
chmod 0600 ~/.btotp
chown $(whoami) ~/.btotp
```

### "Verification failed"

1. Check the code is fresh (codes change every 45 seconds)
2. Verify the secret is correct: `btotp show my-account`
3. Check system clock: `date`
4. Enable debug: add `debug` to module arguments and check syslog

### Module not found

Ensure `pam_btotp.so` is in the correct directory:
```bash
# Debian/Ubuntu
ls /lib/x86_64-linux-gnu/security/pam_btotp.so

# RHEL/CentOS
ls /lib64/security/pam_btotp.so

# Arch
ls /lib/security/pam_btotp.so
```

## File Locations

| File | Purpose |
|------|---------|
| `~/.config/btotp/vault.json` | Encrypted vault (master password required) |
| `~/.btotp` | Plaintext secret for PAM (0600 permissions) |
| `/lib/security/pam_btotp.so` | PAM module |
| `/etc/pam.d/sshd` | PAM configuration for SSH |

## Comparison with google-authenticator

| Aspect | google-authenticator | pam_btotp |
|--------|---------------------|-----------|
| Hash | SHA-1 | SHA-512 |
| Charset | 0-9 (10 chars) | 75 chars |
| Code length | 6 digits | 12 characters |
| Time step | 30 seconds | 45 seconds |
| Secret size | 20 bytes | 64 bytes |
| Storage | `~/.google_authenticator` | `~/.btotp` |
| Vault integration | No | Yes (via `btotp enroll`) |

## License

MIT License - Copyright (c) 2024 Shri Kant
