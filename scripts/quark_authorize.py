"""Create a temporary Quark QR code and wait for the account authorization."""

import json
import time
from pathlib import Path

import qrcode
from quark_client.auth.api_login import APILogin


PROJECT_ROOT = Path(__file__).resolve().parent.parent
STATE_FILE = PROJECT_ROOT / "quark_auth_state.json"
QR_FILE = PROJECT_ROOT / "quark_authorize_qr.png"
COOKIES_FILE = PROJECT_ROOT / "quark_mount_cookies.json"


def save_state(status, **extra):
    payload = {"status": status, "updated_at": int(time.time()), **extra}
    STATE_FILE.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def main():
    try:
        manager = APILogin(timeout=300)
        token, url = manager.get_qr_code()
        qrcode.make(url).save(QR_FILE)
        save_state("waiting")

        if not manager.wait_for_login(token):
            save_state("expired")
            return

        cookies = [
            {
                "name": cookie.name,
                "value": cookie.value,
                "domain": cookie.domain,
                "path": cookie.path or "/",
                "expires": cookie.expires or 0,
            }
            for cookie in manager.client.cookies.jar
            if cookie.domain and "quark.cn" in cookie.domain
        ]
        COOKIES_FILE.write_text(
            json.dumps({"cookies": cookies, "timestamp": int(time.time())}, ensure_ascii=False),
            encoding="utf-8",
        )
        save_state("authorized")
    except Exception as error:
        save_state("error", message=str(error))


if __name__ == "__main__":
    main()
