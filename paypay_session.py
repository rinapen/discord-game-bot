"""
PayPayセッション管理モジュール
本番環境とテスト環境を自動的に切り替えます
"""
from typing import Any, Optional
import random
import string

from config import IS_TEST_MODE, IS_PRODUCTION_MODE, PAYPAY_PHONE_NUMBER, PAYPAY_PIN

# 本番環境の場合のみPayPayライブラリをインポート
if IS_PRODUCTION_MODE:
    from PayPaython_mobile import PayPay
    from database.db import get_tokens, save_tokens


# ========================================
# テスト用モッククラス
# ========================================
class MockDepositInfo:
    """テスト用の入金情報モック"""
    def __init__(self, amount: float, sender_id: str = "test_sender_id"):
        self.amount = amount
        self.order_id = f"TEST-{''.join(random.choices(string.ascii_uppercase + string.digits, k=12))}"
        self.sender_name = "テストユーザー"
        self.sender_icon = "https://via.placeholder.com/150"
        self.sender_external_id = sender_id
        self.status = "PENDING"


class MockPayPay:
    """テスト用のPayPayモッククラス"""
    
    def __init__(self, *args, **kwargs):
        print("🧪 [TEST MODE] MockPayPayを使用しています（実際のPayPay接続なし）")
        self.access_token = "mock_access_token"
        self.refresh_token = "mock_refresh_token"
        self.device_uuid = "mock_device_uuid"
    
    def get_balance(self):
        """残高取得のモック"""
        return {"balance": 100000}
    
    def login(self, url: str):
        """ログインのモック"""
        print(f"🧪 [TEST MODE] Mock login with URL: {url}")
        return True
    
    def token_refresh(self, refresh_token: str):
        """トークンリフレッシュのモック"""
        print(f"🧪 [TEST MODE] Mock token refresh")
        return True
    
    def link_check(self, paypay_link: str) -> MockDepositInfo:
        """リンクチェックのモック"""
        # テストモード: 固定金額またはランダム金額を返す
        amount = random.uniform(100, 2000)
        # リンクからユーザーIDを推測（テスト用）
        sender_id = f"test_sender_{hash(paypay_link) % 10000}"
        print(f"🧪 [TEST MODE] Mock link check: {paypay_link} -> {amount}円")
        return MockDepositInfo(amount, sender_id)
    
    def link_receive(self, paypay_link: str):
        """リンク受信のモック"""
        print(f"🧪 [TEST MODE] Mock link receive: {paypay_link}")
        return True
    
    def send_money(self, amount: int, receiver_id: str):
        """送金のモック"""
        print(f"🧪 [TEST MODE] Mock send money: {amount}円 to {receiver_id}")
        return True
    
    def alive(self):
        """生存確認のモック"""
        return True


# ========================================
# PayPayセッションクラス
# ========================================
class PayPaySession:
    """PayPayセッション管理（テスト/本番自動切替）"""
    
    def __init__(self):
        self.is_test_mode = IS_TEST_MODE
        self.paypay = None
        
        if IS_TEST_MODE:
            print("=" * 60)
            print("🧪 テストモードで起動しています")
            print("   PayPayは使用されません（モックデータを使用）")
            print("=" * 60)
            self.paypay = MockPayPay()
        else:
            print("=" * 60)
            print("🚀 本番モードで起動しています")
            print("   実際のPayPayに接続します")
            print("=" * 60)
            self.tokens = get_tokens()
        self.login()

    def login(self):
        """PayPayにログイン（本番モードのみ）"""
        if IS_TEST_MODE:
            return  # テストモードでは何もしない
        
        login_successful = False

        # access_tokenで試行
        try:
            if "access_token" in self.tokens:
                print("[INFO] Trying access_token login")
                self.paypay = PayPay(access_token=self.tokens["access_token"])
                self.paypay.get_balance()
                login_successful = True
        except Exception as e:
            print(f"[WARN] access_token invalid: {e}")

        # refresh_tokenで試行
        if not login_successful:
            try:
                if "refresh_token" in self.tokens:
                    print("[INFO] Trying refresh_token login")
                    self.paypay.token_refresh(self.tokens["refresh_token"])
                    save_tokens(
                        self.paypay.access_token,
                        self.paypay.refresh_token,
                        self.paypay.device_uuid
                    )
                    self.paypay = PayPay(access_token=self.tokens["access_token"])
                    login_successful = True
            except Exception as e:
                print(f"[WARN] refresh_token failed: {e}")

        # device_uuidで試行
        if not login_successful:
            try:
                if "device_uuid" in self.tokens:
                    print("[INFO] Trying device_uuid login")
                    self.paypay = PayPay(PAYPAY_PHONE_NUMBER, PAYPAY_PIN, self.tokens["device_uuid"])
                    login_successful = True
            except Exception as e:
                print(f"[WARN] device_uuid failed: {e}")

        # 手動ログイン
        if not login_successful:
            try:
                print("[INFO] All methods failed. Please enter login URL or ID manually.")
                self.paypay = PayPay(PAYPAY_PHONE_NUMBER, PAYPAY_PIN)
                url = input("PayPay URL (or ID): ")
                self.paypay.login(url)
                save_tokens(
                    self.paypay.access_token,
                    self.paypay.refresh_token,
                    self.paypay.device_uuid
                )
                print("[INFO] Manual login successful.")
            except Exception as e:
                print(f"[ERROR] Manual login failed: {e}")
                raise e

    def send_money(self, amount: int, receiver_id: str):
        """送金処理"""
        return self.paypay.send_money(amount=amount, receiver_id=receiver_id)


# シングルトンインスタンス
paypay_session = PayPaySession()
