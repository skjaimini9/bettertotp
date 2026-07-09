# BetterTOTP — Web Backend API

A stateless FastAPI microservice for TOTP enrollment and verification.

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET`  | `/api/health` | Health check |
| `POST` | `/api/enroll` | Generate a secret + `otpauth://` URI for a new user |
| `POST` | `/api/verify` | Verify a TOTP code submitted during login |
| `POST` | `/api/generate-code` | Get the current code for a secret (sync/preview) |

## Quick start

```bash
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```

## Integration example

### 1. User enables 2FA

```
POST /api/enroll
{"account": "alice@example.com", "issuer": "MyApp"}

→ 201
{
  "secret_hex": "a1b2c3d4e5f6...",
  "secret_b32": "JBSWY3DPEHPK3PXP...",
  "uri": "otpauth://totp/MyApp:alice@example.com?secret=JBSWY...&algorithm=SHA512&digits=12&period=45"
}
```

Store `secret_hex` in your user database. Render the `uri` as a QR code on the enrollment page.

### 2. User logs in with TOTP

```
POST /api/verify
{"secret_hex": "<stored secret>", "code": "3vMU-DiSZn0n"}

→ 200
{"valid": true}
```

If `valid: true`, allow the login. Default time window is ±1 step (45 seconds).

### 3. Manual verification with `curl`

```bash
SECRET="your-hex-secret"

# Get current code
curl -s http://localhost:8000/api/generate-code \
  -H "Content-Type: application/json" \
  -d "{\"secret_hex\": \"$SECRET\"}"

# Verify a code
curl -s http://localhost:8000/api/verify \
  -H "Content-Type: application/json" \
  -d "{\"secret_hex\": \"$SECRET\", \"code\": \"3vMU-DiSZn0n\"}"
```

## Configuration

| Env variable | Default | Description |
|---|---|---|
| `CORS_ORIGINS` | `*` | Comma-separated allowed origins (e.g. `https://myapp.com,https://admin.myapp.com`) |

## Algorithm (non-standard)

| Parameter | Value |
|-----------|-------|
| Hash | SHA-512 |
| Alphabet | `A-Z a-z 0-9 !@#$%&*-_+=?~` (75 chars) |
| Code length | 12 characters |
| Time step | 45 seconds |
| Default window | ±1 step (45s each direction) |

## Deploy

```bash
# Production with gunicorn
pip install gunicorn
gunicorn -k uvicorn.workers.UvicornWorker main:app --bind 0.0.0.0:8000 --workers 4
```
