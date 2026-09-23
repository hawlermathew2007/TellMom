import json

from shared.services.security import (
    OUTBOUND_SEQUENCE_BASE,
    SessionState,
    decrypt_message,
    encrypt_message,
    seal_outbound,
)

KEY = bytes(range(32))
NONCE_BASE = bytes(range(12))


def _state() -> SessionState:
    return SessionState(session_id="s1", status="ok", aes_key=KEY, nonce_base=NONCE_BASE)


def test_outbound_never_reuses_an_inbound_nonce():
    state = _state()
    # The browser's requests count up from 1; a response must not share one.
    inbound = {
        encrypt_message(
            sequence=n, aes_key=KEY, nonce_base=NONCE_BASE, plaintext="x", session_id="s1"
        ).nonce
        for n in range(1, 50)
    }
    outbound = {seal_outbound(state, "y").nonce for _ in range(50)}
    assert inbound.isdisjoint(outbound)
    assert len(outbound) == 50


def test_outbound_sequence_is_json_safe_and_opens():
    state = _state()
    sealed = seal_outbound(state, json.dumps({"id": 7}))
    assert OUTBOUND_SEQUENCE_BASE < sealed.sequence < 2**53
    plain = decrypt_message(
        aes_key=KEY,
        nonce_base=NONCE_BASE,
        encrypted_message=sealed,
        aad=f"s1:{sealed.sequence}".encode(),
    )
    assert json.loads(plain) == {"id": 7}
