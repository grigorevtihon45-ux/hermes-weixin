# hermes-weixin

Connect [Hermes Agent](https://github.com/NousResearch/hermes-agent) to personal WeChat (微信) over Tencent's **iLink Bot API**. A Hermes **skill** plus a standalone QR-login script, distilled from a real end-to-end setup.

## What's inside

| Path | Purpose |
|---|---|
| `SKILL.md` | Hermes skill — install into `~/.hermes/skills/` so Hermes knows how to do this |
| `scripts/weixin_login.py` | Non-interactive QR login (bypasses the arrow-key TUI wizard), renders a PNG, polls until confirmed, saves creds to `.env` |

## The hard truth (read first)

QR login connects an **iLink bot identity** (`<hex>@im.bot`), *not* a scriptable personal WeChat account:

- ✅ **DMs work reliably.**
- ❌ **Ordinary WeChat groups do not** — the bot identity usually can't be invited into groups, and iLink doesn't deliver group events. This is Tencent-side, not configurable here.
- Each QR scan creates a **fresh bot** bound to the account that scanned. Add more users via the DM allowlist (`WEIXIN_ALLOWED_USERS`).

## Quick start

```bash
# 1. deps (inside the Hermes venv)
pip install qrcode   # optional — only for the PNG render; ASCII works without it

# 2. login
python scripts/weixin_login.py          # prints a QR + writes weixin_qr.png
#    scan with the WeChat account you want to bind, confirm on phone

# 3. authorize users (their user_id shows in the gateway log: "inbound from=<id>")
hermes config set model.provider deepseek     # example — match your provider
hermes config set model.default deepseek-v4-pro
# .env: WEIXIN_DM_POLICY=allowlist  WEIXIN_ALLOWED_USERS=<id1>,<id2>

# 4. start + verify
hermes gateway restart
# log:  ✓ weixin connected   /   Model context warmed: <model> -> …
```

Full details, access-policy semantics, the model-name HTTP 400 gotcha, and
troubleshooting are in [`SKILL.md`](SKILL.md).

## Notes

- No credentials are stored in this repo — the script writes to your local `.env`.
- For group chat / multi-user corporates, use the **WeCom** (企业微信) adapter instead.
