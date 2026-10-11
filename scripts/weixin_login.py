#!/usr/bin/env python
"""Standalone Weixin (WeChat) QR login for Hermes — fetch QR, render PNG, poll until confirmed, save creds to .env.

Reuses the shipped adapter (gateway.platforms.weixin.qr_login) and the canonical
hermes_cli.config.save_env_value so the result matches `hermes gateway setup`.

Run with the Hermes venv python (has aiohttp + cryptography). qrcode+PIL optional
(PNG only; the terminal ASCII render still works without them).
"""
from __future__ import annotations

import asyncio
import json
import os
import sys

# --- resolve paths (edit if your install lives elsewhere) ---
HERMES_HOME = os.environ.get("HERMES_HOME") or os.path.expanduser("~/.hermes")
# Find the source workspace so `gateway.platforms.weixin` imports.
_candidates = [
    os.environ.get("HERMES_WORKSPACE"),
    os.path.join(HERMES_HOME, "hermes-agent"),
]
WORKSPACE = next((c for c in _candidates if c), None)
if WORKSPACE and os.path.isdir(WORKSPACE):
    sys.path.insert(0, WORKSPACE)

SCRATCH = os.environ.get("TMPDIR") or os.path.join(HERMES_HOME, "cache", "scratch")
QR_URL_FILE = os.path.join(SCRATCH, "weixin_qr_url.txt")
QR_PNG_FILE = os.path.join(SCRATCH, "weixin_qr.png")
RESULT_FILE = os.path.join(SCRATCH, "weixin_result.json")
STATE_FILE = os.path.join(SCRATCH, "weixin_state.txt")

from gateway.platforms import weixin as wx  # noqa: E402


def _render_qr_png(url: str) -> bool:
    try:
        import qrcode
        qr = qrcode.QRCode(version=None, error_correction=qrcode.constants.ERROR_CORRECT_M,
                           box_size=10, border=4)
        qr.add_data(url)
        qr.make(fit=True)
        qr.make_image(fill_color="black", back_color="white").save(QR_PNG_FILE)
        return True
    except Exception as exc:  # noqa: BLE001
        print(f"[qr] PNG render failed: {exc}", flush=True)
        return False


_orig_print_qr = wx._print_qr


def _patched_print_qr(qrcode_value: str, qrcode_url: str, *, report_render_error: bool) -> None:
    if qrcode_url:
        try:
            with open(QR_URL_FILE, "w", encoding="utf-8") as f:
                f.write(qrcode_url)
            _render_qr_png(qrcode_url)
            with open(STATE_FILE, "w", encoding="utf-8") as f:
                f.write("qr_ready")
            print(f"[qr] URL captured ({len(qrcode_url)} chars), PNG written", flush=True)
        except Exception as exc:  # noqa: BLE001
            print(f"[qr] capture failed: {exc}", flush=True)
    _orig_print_qr(qrcode_value, qrcode_url, report_render_error=report_render_error)


wx._print_qr = _patched_print_qr


def _save_env(key: str, value: str) -> None:
    try:
        from hermes_cli.config import save_env_value
        save_env_value(key, value)
    except Exception as exc:  # noqa: BLE001
        print(f"[env] save_env_value({key}) failed: {exc}", flush=True)


async def main() -> None:
    print("[login] starting Weixin QR login...", flush=True)
    creds = await wx.qr_login(HERMES_HOME, bot_type="3", timeout_seconds=480)
    with open(RESULT_FILE, "w", encoding="utf-8") as f:
        json.dump(creds, f)
    print(f"[login] RESULT: {json.dumps(creds)}", flush=True)

    if not creds:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            f.write("failed")
        return

    # Match the wizard: persist credentials + recommended defaults to .env.
    _save_env("WEIXIN_ACCOUNT_ID", creds.get("account_id", ""))
    _save_env("WEIXIN_TOKEN", creds.get("token", ""))
    if creds.get("base_url"):
        _save_env("WEIXIN_BASE_URL", creds.get("base_url", ""))
    _save_env("WEIXIN_CDN_BASE_URL", "https://novac2c.cdn.weixin.qq.com/c2c")
    _save_env("WEIXIN_DM_POLICY", "pairing")
    _save_env("WEIXIN_ALLOW_ALL_USERS", "false")
    _save_env("WEIXIN_ALLOWED_USERS", "")
    _save_env("WEIXIN_GROUP_POLICY", "disabled")
    _save_env("WEIXIN_GROUP_ALLOWED_USERS", "")
    if creds.get("user_id"):
        _save_env("WEIXIN_HOME_CHANNEL", creds.get("user_id", ""))

    with open(STATE_FILE, "w", encoding="utf-8") as f:
        f.write("confirmed")
    print("[login] credentials saved to .env", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
