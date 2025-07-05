import secrets
import hashlib
import hmac

def generate_server_seed():
    return secrets.token_hex(32)

def hash_server_seed(seed: str):
    return hashlib.sha256(seed.encode()).hexdigest()

def get_hmac_sha256(server_seed: str, client_seed: str, nonce: int) -> str:
    msg = f"{client_seed}:{nonce}".encode()
    return hmac.new(server_seed.encode(), msg, hashlib.sha256).hexdigest()