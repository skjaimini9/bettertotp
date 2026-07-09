CHARSET = (
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    "abcdefghijklmnopqrstuvwxyz"
    "0123456789"
    "!@#$%&*-_+=?~"
)

CHARSET_SIZE = len(CHARSET)

def encode_to_chars(hash_bytes, length=12):
    indices = []
    for i in range(length):
        low = hash_bytes[i % len(hash_bytes)]
        high = hash_bytes[(i + 1) % len(hash_bytes)]
        idx = (low + high * 256) % CHARSET_SIZE
        indices.append(idx)
    return "".join(CHARSET[idx] for idx in indices)
