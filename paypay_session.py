from PayPaython_mobile import PayPay
from config import PAYPAY_PHONE, PAYPAY_PASSWORD
from database.db import get_tokens, save_tokens

class PayPaySession:
    def __init__(self):
        self.tokens = get_tokens()
        self.paypay = None
        self.login()

    def login(self):
        login_successful = False

        try:
            if "access_token" in self.tokens:
                print("[INFO] Trying access_token login")
                self.paypay = PayPay(access_token=self.tokens["access_token"])
                self.paypay.get_balance()
                login_successful = True
        except Exception as e:
            print(f"[WARN] access_token invalid: {e}")

        if not login_successful:
            try:
                if "refresh_token" in self.tokens:
                    print("[INFO] Trying refresh_token login")
                    self.paypay = PayPay(PAYPAY_PHONE, PAYPAY_PASSWORD)
                    self.paypay.token_refresh(self.tokens["refresh_token"])
                    save_tokens(
                        self.paypay.access_token,
                        self.paypay.refresh_token,
                        self.paypay.device_uuid
                    )
                    login_successful = True
            except Exception as e:
                print(f"[WARN] refresh_token failed: {e}")

        if not login_successful:
            try:
                if "device_uuid" in self.tokens:
                    print("[INFO] Trying device_uuid login")
                    self.paypay = PayPay(PAYPAY_PHONE, PAYPAY_PASSWORD, self.tokens["device_uuid"])
                    login_successful = True
            except Exception as e:
                print(f"[WARN] device_uuid failed: {e}")

        if not login_successful:
            try:
                print("[INFO] All methods failed. Please enter login URL or ID manually.")
                self.paypay = PayPay(PAYPAY_PHONE, PAYPAY_PASSWORD)
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

    def send_money(self, amount, receiver_id):
        return self.paypay.send_money(amount=amount, receiver_id=receiver_id)

paypay_session = PayPaySession()
