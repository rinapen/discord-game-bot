"""
システムユーティリティ
Provably Fair実装のための暗号化関数を提供します
"""
import secrets
import hashlib
import hmac


def generate_server_seed() -> str:
    """
    サーバーシードを生成
    
    Returns:
        str: 32バイトのランダムな16進数文字列
    """
    return secrets.token_hex(32)


def hash_server_seed(seed: str) -> str:
    """
    サーバーシードをSHA256でハッシュ化
    
    Args:
        seed: ハッシュ化するシード
    
    Returns:
        str: SHA256ハッシュ値（16進数）
    """
    return hashlib.sha256(seed.encode()).hexdigest()


def get_hmac_sha256(server_seed: str, client_seed: str, nonce: int) -> str:
    """
    HMAC-SHA256を計算
    
    Args:
        server_seed: サーバーシード
        client_seed: クライアントシード
        nonce: ナンス値
    
    Returns:
        str: HMAC-SHA256ハッシュ値（16進数）
    """
    msg = f"{client_seed}:{nonce}".encode()
    return hmac.new(server_seed.encode(), msg, hashlib.sha256).hexdigest()