# Inbound Email Setup

How to connect a mailbox so job mail is matched against tracked applications.

Nothing here is live until the environment variables in step 4 are set — the
webhook returns `503` while they are empty, so the feature ships dark.

## How it works

```
Recruiter emails you
  → your mailbox (Hotmail, Gmail, anything) auto-forwards a copy
  → to u-<your token>@in.applyluma.com
  → Mailgun accepts the delivery (it is the MX for that subdomain)
  → Mailgun POSTs the parsed message to /api/v1/inbound/email
  → ApplyLuma matches it to one of your applications
  → the result appears at /admin/inbound-mail
```

The forwarding step is what makes this provider-agnostic: nothing depends on
which mailbox the user has.

## What this does NOT do yet

Reading `/admin/inbound-mail` is currently the whole point. Matched mail does
**not** change an application's status, send a notification, or write to the
timeline. That is deliberate: the first question is whether matching is
accurate enough on real mail to be trusted with those actions.

---

## 1. Add the MX record (Namecheap)

In **Domain List → applyluma.com → Advanced DNS**, add one record:

| Field | Value |
| --- | --- |
| Type | `MX Record` |
| Host | `in` |
| Value | `mxa.mailgun.org` |
| Priority | `10` |

Add a second with `mxb.mailgun.org` at priority `10` for redundancy.

> **Leave the `@` (apex) MX records alone.** Those carry your normal mail.
> Adding a record on the `in` host cannot affect them.

Confirm once DNS propagates (up to ~30 minutes):

```bash
dig MX in.applyluma.com +short
```

## 2. Add the domain in Mailgun

Add `in.applyluma.com` as a domain. Mailgun will ask for verification records —
add whatever it lists at Namecheap on the `in` host, not the apex.

Pick the **EU region** if offered. It keeps mail processing inside the EU,
which is the easier position to defend under GDPR for a Swedish user base.

## 3. Create the inbound route

Under **Receiving → Routes**, create a route:

- **Expression**: `match_recipient(".*@in.applyluma.com")`
- **Action**: `forward("https://applyluma-production.up.railway.app/api/v1/inbound/email")`
- **Priority**: `0`

Do **not** add a `store()` action. We keep only a short excerpt of each
message, and having Mailgun retain full copies would undercut that.

## 4. Set the environment variables (Railway)

On the backend service:

```
INBOUND_EMAIL_VENDOR=mailgun
INBOUND_EMAIL_DOMAIN=in.applyluma.com
INBOUND_EMAIL_WEBHOOK_SECRET=<Mailgun HTTP webhook signing key>
```

The secret is the **HTTP webhook signing key** from Mailgun's dashboard
(Sending → Webhooks). It is *not* the sending API key — using the wrong one
makes every message fail signature verification with a `400`.

Railway redeploys automatically. The migration runs on boot via
`scripts/start-web.sh`, so there is nothing to apply by hand.

## 5. Find your forwarding address

Open `/admin/users`, click your own user, and copy the address from the
**Inbound mail address** panel.

It looks like `u-a1b2c3d4e5f60718@in.applyluma.com`.

> Treat this address as a credential. Anyone who knows it can post mail into
> your account. It is deliberately admin-only for now.

## 6. Forward your mail

**Outlook / Hotmail**: Settings → Mail → Forwarding → enable, paste the
address, and tick "Keep a copy of forwarded messages".

**A domain you own**: instead of forwarding, point that subdomain's MX
straight at Mailgun — fewer moving parts and no SPF breakage.

Prefer a rule that forwards only recruiting mail if your provider can express
one. Blanket forwarding works, but it sends us your whole inbox, and anything
that isn't job mail is stored as an unmatched row with a short excerpt.

## 7. Check it worked

Send yourself a test, then open `/admin/inbound-mail`. You should see the
message with either a matched application or an "Unmatched" chip plus the
reason it decided that.

---

## Testing without any of the above

The `generic` adapter accepts a signed JSON body, so the pipeline can be
exercised end to end before touching DNS or creating a vendor account.

Set `INBOUND_EMAIL_VENDOR=generic` plus a secret of your choosing, then run:

```
python backend/scripts/send_test_inbound_email.py \
    --address u-YOURTOKEN@in.applyluma.com \
    --secret  YOUR_INBOUND_EMAIL_WEBHOOK_SECRET
```

Standard library only, so it needs no virtualenv and works the same on
Windows, macOS and Linux. It prints the HTTP status and what to do about it.
Expect `HTTP 202`, then check `/admin/inbound-mail`.

Useful flags:

- `--from "HR <hr@klarna.com>"` and `--subject "..."` — simulate a company you
  actually have an application for, to see a match rather than an unmatched row.
- `--message-id "<fixed@test>"` — reuse an id across runs to confirm duplicates
  are dropped (the second run should not create a second row).
- `--dry-run` — print the signed request without sending it.
- `--url http://localhost:8000/api/v1/inbound/email` — target a local server.

Switch `INBOUND_EMAIL_VENDOR` back to `mailgun` afterwards.

## Troubleshooting

| Symptom | Cause |
| --- | --- |
| `503` from the webhook | `INBOUND_EMAIL_WEBHOOK_SECRET` or `INBOUND_EMAIL_DOMAIN` is empty |
| `400 Invalid signature` | Wrong Mailgun key — use the *webhook signing* key, not the API key |
| `200 {"status":"ignored"}` | Recipient did not resolve: wrong domain, or a token with no matching user |
| Mail never arrives | MX not propagated, or the route expression does not match |
| Everything lands unmatched | Expected for *manual* forwards — see below |

**Manual forwards land unmatched.** Only auto-forwarding preserves the
original `From:` header. When you forward by hand, your mail client sends a
new message *from you*, and the original sender survives only as quoted text
in the body, which the matcher does not read. Use an auto-forward rule.

## Privacy

- Only metadata and a 2000-character excerpt are stored; full bodies are
  discarded in the request handler, before the message reaches the queue.
- Rows cascade-delete with the user account.
- **`PrivacyPolicy.tsx` must be updated before this is exposed to any
  non-admin user** — it ingests personal correspondence.
