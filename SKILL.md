---
name: hermes-weixin
description: "Use when connecting Hermes to personal WeChat (Weixin)."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [windows, linux, macos]
metadata:
  hermes:
    tags: [weixin, wechat, messaging, gateway, ilink, qr-login]
---

# Hermes ↔ WeChat (Weixin) integration

Connect Hermes to a **personal WeChat account** over Tencent's iLink Bot API
(adapter: `gateway/platforms/weixin.py`). Messages flow via long-polling — no
public endpoint or webhook needed. Distinct from WeCom (企业微信), which is a
separate adapter with working group support.

## Hard limitation (say this up front)

QR login connects an **iLink bot identity** (`<hex>@im.bot`), NOT a scriptable
personal WeChat account:

- **DMs work reliably**; **ordinary WeChat groups do not** — the bot identity
  usually cannot be invited into groups, and iLink does not deliver group
  events (incl. `@`-mentions) for most bot accounts. This is Tencent-side, not
  configurable.
- Each QR scan creates a **fresh bot** (new `account_id` + `token`), bound to
  the account that scanned. To add more users, put their `user_id` in the
  allowlist — they must message the bot first so you can read their id from the
  gateway log.
- `8ca0cf6d09d8@im.bot`-style ids are internal and NOT searchable in WeChat.
  Users reach the bot by scanning its QR or via a shared contact card, not by
  searching the id.

## Prerequisites

- `aiohttp` + `cryptography` in the Hermes venv (`check_weixin_requirements()`).
- `qrcode` (+ PIL) only if you want a PNG instead of the terminal ASCII render.

## Setup — QR login without the TUI wizard

The wizard (`hermes gateway setup`) is arrow-key driven and painful to drive
programmatically. Use the bundled script instead — it reuses the shipped
`qr_login()` so the result matches the wizard exactly:

```bash
python scripts/weixin_login.py
```

It fetches the QR, writes `weixin_qr.png` + `weixin_qr_url.txt` to the scratch
dir, polls until `confirmed`, then persists the credentials to `.env`
(`WEIXIN_ACCOUNT_ID`, `WEIXIN_TOKEN`, `WEIXIN_BASE_URL`, `WEIXIN_CDN_BASE_URL`,
DM/group policy defaults). Present the PNG to the user via `MEDIA:` so they can
scan it; the QR auto-refreshes up to 3 times on expiry.

On `confirmed`, `qr_login` returns `{account_id, token, base_url, user_id}`.
`user_id` is the **scanner's** WeChat id — keep it; it goes in the allowlist.

## Access policy (allowlist is the clean default)

```bash
# .env — set via hermes_cli.config.save_env_value, then restart the gateway
WEIXIN_DM_POLICY=allowlist          # open | allowlist | disabled | pairing
WEIXIN_ALLOWED_USERS=<id1>,<id2>    # comma-separated sender user_ids
WEIXIN_GROUP_POLICY=disabled        # keep disabled for iLink bots
```

- `pairing` admits everyone at intake so the pairing handshake runs; `allowlist`
  drops unknown senders BEFORE they are logged (so you cannot discover a new
  user's id while in `allowlist` mode — switch to `pairing`, capture the id from
  the `inbound from=…` log line, then set `allowlist`).
- Each account's `user_id` is stable across bots: the old bot's
  `~/.hermes/weixin/accounts/<account_id>.json` stores the scanner's `user_id`
  even after the user unlinks in WeChat — read it there.

## Model-name gotcha (causes HTTP 400)

The gateway uses `model.default` from config.yaml. If it names a model the
active provider does not serve, every bot reply fails with HTTP 400. Symptom:
`DeepSeek rejected the request … but you passed anthropic/claude-opus-4.6`.
Fix and verify:

```bash
hermes config set model.provider deepseek
hermes config set model.default deepseek-v4-pro
hermes gateway restart
# log should show:  Model context warmed: deepseek-v4-pro -> …
```

## Verify

```bash
hermes gateway restart
# log lines to confirm:
#   ✓ weixin connected  /  [Weixin] Connected account=<id> base=https://ilinkai.weixin.qq.com
#   Model context warmed: <model> -> …
hermes gateway status        # process running + Windows login item installed
```

Then have the bound account send the bot a DM; a healthy run logs
`inbound from=<user_id>` and replies.

## Troubleshooting

- `no dependency environment is committed … run hermes pm repair` → run it,
  then `hermes gateway start` again.
- `session timeout` / `errcode=-14` → the bound account unlinked the bot; re-run
  the QR login to bind a fresh bot.
- Bot silent on DMs → check `WEIXIN_DM_POLICY`; under `allowlist` the sender
  must be in `WEIXIN_ALLOWED_USERS`.
