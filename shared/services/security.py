import base64
import hashlib
import hmac
import secrets
from dataclasses import dataclass
from shared.schemas.tunnel import EncryptedMessage

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

# This is a safe 2048-bit MODP group from RFC 3526 (group 14)
DH_P = int(
    """
    FFFFFFFF FFFFFFFF C90FDAA2 2168C234 C4C6628B 80DC1CD1
    29024E08 8A67CC74 020BBEA6 3B139B22 514A0879 8E3404DD
    EF9519B3 CD3A431B 302B0A6D F25F1437 4FE1356D 6D51C245
    E485B576 625E7EC6 F44C42E9 A637ED6B 0BFF5CB6 F406B7ED
    EE386BFB 5A899FA5 AE9F2411 7C4B1FE6 49286651 ECE65381
    FFFFFFFF FFFFFFFF
    """.replace("\n", "").replace(" ", ""),
    16,
)
DH_G = 2


@dataclass
class SessionState:
    session_id: str
    status: str
    sequence: int = 1
    aes_key: bytes | None = None
    nonce_base: bytes | None = None
    server_private: int | None = None
    server_public: int | None = None


def int_to_b64(value: int) -> str:
    raw = value.to_bytes((value.bit_length() + 7) // 8 or 1, "big")
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def b64_to_int(value: str) -> int:
    padded = value + "=" * (-len(value) % 4)
    raw = base64.urlsafe_b64decode(padded.encode("ascii"))
    return int.from_bytes(raw, "big")


def generate_dh_private_key() -> int:
    return secrets.randbelow(DH_P - 2) + 2


def derive_dh_public_key(private_key: int) -> int:
    return pow(DH_G, private_key, DH_P)


def derive_shared_secret(private_key: int, peer_public: int) -> bytes:
    shared = pow(peer_public, private_key, DH_P)
    secret_bytes = shared.to_bytes((shared.bit_length() + 7) // 8 or 1, "big")
    return hashlib.sha256(secret_bytes).digest()


def hkdf_extract(salt: bytes, ikm: bytes) -> bytes:
    return hmac.new(salt, ikm, hashlib.sha256).digest()


def hkdf_expand(prk: bytes, info: bytes, length: int) -> bytes:
    result = b""
    previous = b""
    counter = 1
    while len(result) < length:
        previous = hmac.new(
            prk, previous + info + bytes([counter]), hashlib.sha256
        ).digest()
        result += previous
        counter += 1
    return result[:length]


def derive_session_keys(shared_secret: bytes) -> tuple[bytes, bytes, bytes]:
    prk = hkdf_extract(b"", shared_secret)
    aes_key = hkdf_expand(prk, b"aes-gcm", 32)
    nonce_base = hkdf_expand(prk, b"nonce", 12)
    future_keys = hkdf_expand(prk, b"future", 32)
    return aes_key, nonce_base, future_keys


def xor_nonce(nonce_base: bytes, sequence: int) -> bytes:
    sequence_bytes = sequence.to_bytes(len(nonce_base), "big")
    return bytes(a ^ b for a, b in zip(nonce_base, sequence_bytes))


def encrypt_message(
    *,
    sequence: int,
    aes_key: bytes,
    nonce_base: bytes,
    plaintext: str,
    session_id: str,
) -> EncryptedMessage:
    nonce = xor_nonce(nonce_base, sequence)
    aad = f"{session_id}:{sequence}".encode("utf-8")

    aesgcm = AESGCM(aes_key)
    encrypted = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), aad)

    body = encrypted[:-16]
    tag = encrypted[-16:]

    return EncryptedMessage(
        sequence=sequence,
        nonce=base64.urlsafe_b64encode(nonce).rstrip(b"=").decode("ascii"),
        ciphertext=base64.urlsafe_b64encode(body).rstrip(b"=").decode("ascii"),
        auth_tag=base64.urlsafe_b64encode(tag).rstrip(b"=").decode("ascii"),
    )


def decrypt_message(
    *,
    aes_key: bytes,
    nonce_base: bytes,
    encrypted_message: EncryptedMessage,
    aad: bytes,
) -> bytes:
    nonce = xor_nonce(nonce_base, encrypted_message.sequence)

    ciphertext = base64.urlsafe_b64decode(
        encrypted_message.ciphertext + "=" * (-len(encrypted_message.ciphertext) % 4)
    )
    tag = base64.urlsafe_b64decode(
        encrypted_message.auth_tag + "=" * (-len(encrypted_message.auth_tag) % 4)
    )
    aesgcm = AESGCM(aes_key)

    return aesgcm.decrypt(nonce, ciphertext + tag, aad)
