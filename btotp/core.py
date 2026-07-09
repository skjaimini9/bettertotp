import hashlib
import hmac
import struct
import time

from .charset import encode_to_chars

DEFAULT_TIME_STEP = 45
DEFAULT_CODE_LENGTH = 12
DEFAULT_HASH_ALGO = "sha512"

_ALGO_MAP = {
    "sha1": hashlib.sha1,
    "sha256": hashlib.sha256,
    "sha512": hashlib.sha512,
}


def _time_counter(t=None, time_step=DEFAULT_TIME_STEP):
    if t is None:
        t = time.time()
    return int((t) / time_step)


def _hmac(key_bytes, counter, algorithm=DEFAULT_HASH_ALGO):
    hash_func = _ALGO_MAP[algorithm]
    msg = struct.pack(">Q", counter)
    return hmac.new(key_bytes, msg, hash_func).digest()


def hotp(key_bytes, counter, algorithm=DEFAULT_HASH_ALGO, code_length=DEFAULT_CODE_LENGTH):
    hash_bytes = _hmac(key_bytes, counter, algorithm)
    return encode_to_chars(hash_bytes, code_length)


def totp(key_bytes, t=None, algorithm=DEFAULT_HASH_ALGO, code_length=DEFAULT_CODE_LENGTH, time_step=DEFAULT_TIME_STEP):
    counter = _time_counter(t, time_step)
    return hotp(key_bytes, counter, algorithm, code_length)


def generate_code(key_bytes, t=None, algorithm=DEFAULT_HASH_ALGO, code_length=DEFAULT_CODE_LENGTH, time_step=DEFAULT_TIME_STEP):
    if isinstance(key_bytes, str):
        key_bytes = key_bytes.encode("utf-8")
    key_bytes = bytes(key_bytes)
    return totp(key_bytes, t, algorithm, code_length, time_step)


def generate_code_at(key_bytes, timestamp, algorithm=DEFAULT_HASH_ALGO, code_length=DEFAULT_CODE_LENGTH, time_step=DEFAULT_TIME_STEP):
    return totp(key_bytes, timestamp, algorithm, code_length, time_step)


def verify_code(key_bytes, code, window=1, algorithm=DEFAULT_HASH_ALGO, code_length=DEFAULT_CODE_LENGTH, time_step=DEFAULT_TIME_STEP):
    if isinstance(key_bytes, str):
        key_bytes = key_bytes.encode("utf-8")
    key_bytes = bytes(key_bytes)
    current_counter = _time_counter(time_step=time_step)
    for offset in range(-window, window + 1):
        candidate = hotp(key_bytes, current_counter + offset, algorithm, code_length)
        if candidate == code:
            return True
    return False
