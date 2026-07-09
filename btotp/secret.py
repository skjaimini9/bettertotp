import base64
import secrets


SECRET_BYTE_LENGTH = 64


def generate_secret(length=SECRET_BYTE_LENGTH):
    return secrets.token_bytes(length)


def secret_to_b32(secret_bytes):
    return base64.b32encode(secret_bytes).decode("ascii")


def b32_to_secret(b32_string):
    return base64.b32decode(b32_string)


def secret_to_hex(secret_bytes):
    return secret_bytes.hex()


def hex_to_secret(hex_string):
    return bytes.fromhex(hex_string)


def format_secret_for_display(secret_bytes, chunk=4):
    h = secret_to_hex(secret_bytes).upper()
    return " ".join(h[i:i + chunk] for i in range(0, len(h), chunk))
