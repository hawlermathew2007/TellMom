# from backend.services.session_security import (
#     b64_to_int,
#     encrypt_message,
#     decrypt_message,
#     derive_dh_public_key,
#     derive_session_keys,
#     derive_shared_secret,
#     generate_dh_private_key,
#     int_to_b64,
#     xor_nonce,
# )
# 
# 
# def test_dh_hkdf_aes_gcm_roundtrip() -> None:
#     private_a = generate_dh_private_key()
#     private_b = generate_dh_private_key()
#     public_a = derive_dh_public_key(private_a)
#     public_b = derive_dh_public_key(private_b)
# 
#     secret_a = derive_shared_secret(private_a, public_b)
#     secret_b = derive_shared_secret(private_b, public_a)
#     assert secret_a == secret_b
# 
#     aes_key, nonce_base, _ = derive_session_keys(secret_a)
#     sequence = 1
#     nonce = xor_nonce(nonce_base, sequence)
#     plaintext = b"hello secure world"
#     aad = b"session:1"
# 
#     ciphertext, auth_tag = encrypt_message(aes_key, nonce, plaintext, aad)
#     recovered = decrypt_message(aes_key, nonce, ciphertext, auth_tag, aad)
#     assert recovered == plaintext
#     assert int_to_b64(public_a)
#     assert b64_to_int(int_to_b64(public_a)) == public_a
