from shared.services.security import (
    b64_to_int,
    encrypt_message,
    decrypt_message,
    derive_dh_public_key,
    derive_session_keys,
    derive_shared_secret,
    generate_dh_private_key,
    int_to_b64,
)


def test_dh_hkdf_aes_gcm_roundtrip() -> None:
    private_a = generate_dh_private_key()
    private_b = generate_dh_private_key()
    public_a = derive_dh_public_key(private_a)
    public_b = derive_dh_public_key(private_b)

    secret_a = derive_shared_secret(private_a, public_b)
    secret_b = derive_shared_secret(private_b, public_a)
    assert secret_a == secret_b

    aes_key, nonce_base, _ = derive_session_keys(secret_a)

    sequence = 1
    session_id = "id_1"
    plaintext = "hello world"
    aad = f"{session_id}:{sequence}".encode()

    ciphertext = encrypt_message(
        sequence=sequence,
        aes_key=aes_key,
        nonce_base=nonce_base,
        plaintext=plaintext,
        session_id=session_id,
    )

    recovered = decrypt_message(
        aes_key=aes_key,
        nonce_base=nonce_base,
        encrypted_message=ciphertext,
        aad=aad,
    )

    assert recovered.decode() == plaintext
    assert int_to_b64(public_a)
    assert b64_to_int(int_to_b64(public_a)) == public_a
