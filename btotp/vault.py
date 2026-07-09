import json
import os
import base64
import getpass

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from .core import generate_code, DEFAULT_HASH_ALGO, DEFAULT_CODE_LENGTH, DEFAULT_TIME_STEP

VAULT_DIR = os.path.join(os.path.expanduser("~"), ".config", "btotp")
VAULT_PATH = os.path.join(VAULT_DIR, "vault.json")
KDF_ITERATIONS = 600_000
AES_KEY_LENGTH = 32


def _derive_key(password: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=AES_KEY_LENGTH, salt=salt, iterations=KDF_ITERATIONS)
    return kdf.derive(password.encode("utf-8"))


def _encrypt(plaintext: str, password: str) -> dict:
    salt = os.urandom(16)
    nonce = os.urandom(12)
    key = _derive_key(password, salt)
    aesgcm = AESGCM(key)
    ct = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
    return {
        "version": 1,
        "salt": base64.b64encode(salt).decode("ascii"),
        "nonce": base64.b64encode(nonce).decode("ascii"),
        "data": base64.b64encode(ct).decode("ascii"),
    }


def _decrypt(payload: dict, password: str) -> str:
    salt = base64.b64decode(payload["salt"])
    nonce = base64.b64decode(payload["nonce"])
    ct = base64.b64decode(payload["data"])
    key = _derive_key(password, salt)
    aesgcm = AESGCM(key)
    pt = aesgcm.decrypt(nonce, ct, None)
    return pt.decode("utf-8")


class Vault:
    def __init__(self, path: str = VAULT_PATH):
        self.path = path
        self._password: str | None = None
        self._accounts: dict = {}

    def exists(self) -> bool:
        return os.path.exists(self.path)

    def _load(self):
        with open(self.path) as f:
            payload = json.load(f)
        raw = _decrypt(payload, self._password)
        self._accounts = json.loads(raw)["accounts"]

    def _save(self):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        raw = json.dumps({"accounts": self._accounts})
        payload = _encrypt(raw, self._password)
        with open(self.path, "w") as f:
            json.dump(payload, f)

    def unlock(self, password: str | None = None):
        if password is None:
            password = getpass.getpass("Master password: ")
        self._password = password
        if self.exists():
            self._load()

    def create(self, password: str | None = None):
        if password is None:
            password = getpass.getpass("New master password: ")
            confirm = getpass.getpass("Confirm master password: ")
            if password != confirm:
                raise ValueError("Passwords do not match")
        self._password = password
        self._accounts = {}
        self._save()

    def add(self, name: str, secret: str, issuer: str = "", algorithm: str = DEFAULT_HASH_ALGO,
            digits: int = DEFAULT_CODE_LENGTH, period: int = DEFAULT_TIME_STEP):
        if name in self._accounts:
            raise KeyError(f"Account '{name}' already exists")
        self._accounts[name] = {
            "secret": secret,
            "issuer": issuer,
            "algorithm": algorithm,
            "digits": digits,
            "period": period,
        }
        self._save()

    def remove(self, name: str):
        if name not in self._accounts:
            raise KeyError(f"Account '{name}' not found")
        del self._accounts[name]
        self._save()

    def rename(self, old_name: str, new_name: str):
        if old_name not in self._accounts:
            raise KeyError(f"Account '{old_name}' not found")
        if new_name in self._accounts:
            raise KeyError(f"Account '{new_name}' already exists")
        self._accounts[new_name] = self._accounts.pop(old_name)
        self._save()

    def get(self, name: str) -> dict:
        if name not in self._accounts:
            raise KeyError(f"Account '{name}' not found")
        return dict(self._accounts[name])

    def list_accounts(self) -> list[dict]:
        return [
            {"name": name, **acc}
            for name, acc in self._accounts.items()
        ]

    def code(self, name: str) -> str:
        acc = self.get(name)
        secret = bytes.fromhex(acc["secret"])
        return generate_code(
            secret,
            algorithm=acc.get("algorithm", DEFAULT_HASH_ALGO),
            code_length=acc.get("digits", DEFAULT_CODE_LENGTH),
            time_step=acc.get("period", DEFAULT_TIME_STEP),
        )

    def export_json(self) -> str:
        return json.dumps({"accounts": self._accounts}, indent=2)

    def import_json(self, data: str):
        parsed = json.loads(data)
        for name, acc in parsed.get("accounts", {}).items():
            if name in self._accounts:
                raise KeyError(f"Account '{name}' already exists in vault")
            self._accounts[name] = acc
        self._save()
