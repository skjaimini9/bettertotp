import re
import urllib.parse

from .core import DEFAULT_HASH_ALGO, DEFAULT_CODE_LENGTH, DEFAULT_TIME_STEP

_ALGO_MAP = {"SHA1": "sha1", "SHA256": "sha256", "SHA512": "sha512"}
_ALGO_REVERSE = {v: k for k, v in _ALGO_MAP.items()}


def parse_otpauth(uri: str) -> dict:
    if not uri.startswith("otpauth://totp/"):
        raise ValueError("Only otpauth://totp/ URIs are supported")

    parsed = urllib.parse.urlparse(uri)
    # path is /ISSUER:ACCOUNT or /ACCOUNT (no /totp/ prefix)
    path = urllib.parse.unquote(parsed.path.lstrip("/"))
    query = urllib.parse.parse_qs(parsed.query, keep_blank_values=True)

    match = re.match(r"^(.*?):(.+)$", path) if ":" in path else None
    if match:
        issuer = match.group(1)
        account = match.group(2)
    else:
        issuer = ""
        account = path

    secret = query.get("secret", [""])[0].upper()
    if not secret:
        raise ValueError("No secret found in URI")

    algo_raw = query.get("algorithm", ["SHA1"])[0].upper()
    algorithm = _ALGO_MAP.get(algo_raw, DEFAULT_HASH_ALGO)

    digits_str = query.get("digits", [str(DEFAULT_CODE_LENGTH)])[0]
    try:
        digits = int(digits_str)
    except ValueError:
        digits = DEFAULT_CODE_LENGTH

    period_str = query.get("period", [str(DEFAULT_TIME_STEP)])[0]
    try:
        period = int(period_str)
    except ValueError:
        period = DEFAULT_TIME_STEP

    issuer_param = query.get("issuer", [""])[0]
    if issuer_param and not issuer:
        issuer = issuer_param

    return {
        "secret": _b32_to_hex(secret),
        "issuer": issuer,
        "account": account,
        "algorithm": algorithm,
        "digits": digits,
        "period": period,
    }


def _b32_to_hex(b32: str) -> str:
    import base64
    padding = 8 - (len(b32) % 8)
    if padding != 8:
        b32 += "=" * padding
    raw = base64.b32decode(b32)
    return raw.hex()


def _hex_to_b32(hex_str: str) -> str:
    import base64
    raw = bytes.fromhex(hex_str)
    return base64.b32encode(raw).decode("ascii").rstrip("=")


def generate_uri(account: str, secret_hex: str, issuer: str = "",
                 algorithm: str = DEFAULT_HASH_ALGO,
                 digits: int = DEFAULT_CODE_LENGTH,
                 period: int = DEFAULT_TIME_STEP) -> str:
    b32_secret = _hex_to_b32(secret_hex)
    algo_label = _ALGO_REVERSE.get(algorithm, "SHA512")
    label = f"{issuer}:{account}" if issuer else account
    params = {"secret": b32_secret, "algorithm": algo_label, "digits": str(digits), "period": str(period)}
    if issuer:
        params["issuer"] = issuer
    qs = urllib.parse.urlencode(params)
    return f"otpauth://totp/{urllib.parse.quote(label, safe='')}?{qs}"
