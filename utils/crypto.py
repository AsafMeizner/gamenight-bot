# utils/crypto.py
import base64
import hashlib
import secrets
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305

_SALT_LEN  = 16
_NONCE_LEN = 12
_KEY_LEN   = 32
_SCRYPT_N = 2**14
_SCRYPT_R = 8
_SCRYPT_P = 1
_MAGIC = b"SC1"

def _b64u_encode(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).decode("ascii")

def _b64u_decode(s: str) -> bytes:
    return base64.urlsafe_b64decode(s.encode("ascii"))

def _kdf_scrypt(passphrase: str, salt: bytes) -> bytes:
    return hashlib.scrypt(
        password=passphrase.encode("utf-8"),
        salt=salt,
        n=_SCRYPT_N, r=_SCRYPT_R, p=_SCRYPT_P,
        dklen=_KEY_LEN
    )

def encrypt_strong(plaintext: str, passphrase: str) -> str:
    if not isinstance(plaintext, str) or not isinstance(passphrase, str):
        raise TypeError("plaintext and passphrase must be str")
    salt  = secrets.token_bytes(_SALT_LEN)
    key   = _kdf_scrypt(passphrase, salt)
    nonce = secrets.token_bytes(_NONCE_LEN)
    aead  = ChaCha20Poly1305(key)
    pt = plaintext.encode("utf-8")
    ct = aead.encrypt(nonce, pt, _MAGIC)  # ciphertext||tag
    blob = _MAGIC + salt + nonce + ct
    return _b64u_encode(blob)

def decrypt_strong(cipher_b64: str, passphrase: str) -> str:
    blob = _b64u_decode(cipher_b64)
    if len(blob) < len(_MAGIC) + _SALT_LEN + _NONCE_LEN + 16:
        raise ValueError("ciphertext too short or malformed")
    if blob[:len(_MAGIC)] != _MAGIC:
        raise ValueError("unknown format / bad header")
    idx = len(_MAGIC)
    salt  = blob[idx: idx+_SALT_LEN];  idx += _SALT_LEN
    nonce = blob[idx: idx+_NONCE_LEN]; idx += _NONCE_LEN
    ct    = blob[idx:]
    key  = _kdf_scrypt(passphrase, salt)
    aead = ChaCha20Poly1305(key)
    try:
        pt = aead.decrypt(nonce, ct, _MAGIC)
    except Exception as e:
        raise ValueError("decryption failed (bad key or tampered data)") from e
    return pt.decode("utf-8")
