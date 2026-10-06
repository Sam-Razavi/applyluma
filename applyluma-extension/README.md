# ApplyLuma Browser Extension

Save job postings to ApplyLuma with one click, see your CV match score, and
track or tailor for the job without leaving the posting. Manifest V3; one
codebase runs in Chrome and Firefox. Plain JavaScript, no build step.

## Supported sites

| Site | Hosts | Content script |
|---|---|---|
| LinkedIn | `www.linkedin.com/jobs/*` | `content/linkedin.js` |
| Indeed | `se.indeed.com`, `www.indeed.com` | `content/indeed.js` |
| Glassdoor | `www.glassdoor.com` | `content/glassdoor.js` |
| Arbetsförmedlingen (Platsbanken) | `arbetsformedlingen.se`, `www.arbetsformedlingen.se` | `content/platsbanken.js` |

To add a site, add it to `manifest.json` (`host_permissions` + a
`content_scripts` entry), to `JOB_SITE_PATTERNS` in `background.js`, and to
`detectSource()` in both `background.js` and `popup/popup.js`.

## Features

- **Save:** the popup is pre-filled from the page (title, company, URL,
  description, optional note) and saves via `POST /api/v1/jobs/bookmark`.
- **Match score:** shown after saving, scored against the user's default CV.
- **Track application / AI Tailor:** from the popup after saving.
- **Badges:** "Saved ✓" / "Applied ✓" on job cards in search results; the
  toolbar badge shows the saved-job count. The lists refresh every 30 minutes
  (`chrome.alarms`) and whenever the user connects.
- **Quick save:** `Alt+Shift+S` saves the current job without opening the
  popup and confirms with a desktop notification. Users can rebind it at
  `chrome://extensions/shortcuts` (Firefox: Manage Extension Shortcuts).

## Auth

1. Popup → **Login with ApplyLuma** opens https://applyluma.com/extension-auth.
2. That page calls `GET /api/v1/auth/extension-token` (cookie-authenticated)
   and copies a `{access_token, refresh_token}` JSON pair to the clipboard.
3. Paste it into the popup → **Connect**. A bare access token also works.

Tokens live in `chrome.storage.local`. On a 401 the extension calls
`/api/v1/auth/refresh` once; if that fails it clears the tokens and asks the
user to reconnect.

## Development

**Chrome:** `chrome://extensions` → enable Developer mode → **Load unpacked** →
select this folder. Click the reload icon on the card after changes.

**Firefox:** `about:debugging#/runtime/this-firefox` → **Load Temporary
Add-on** → pick `manifest.json`. Firefox runs `background.scripts`; Chrome runs
`background.service_worker`. Both point at the same `background.js`, and each
browser ignores the key it doesn't use.

The API base (`API_BASE`) is hard-coded to production in `background.js` and
`popup/popup.js`, along with the matching `host_permissions` entry. To test
against a local backend, change all three temporarily.

## Release

```bash
./scripts/package.sh --check   # validate manifest, referenced files, JS syntax
./scripts/package.sh           # -> dist/applyluma-extension-<version>.zip
```

1. Bump `version` in `manifest.json`. The stores reject a version they've
   already seen.
2. Run `./scripts/package.sh`.
3. Upload the zip to the
   [Chrome Web Store dashboard](https://chrome.google.com/webstore/devconsole)
   and to [Firefox AMO](https://addons.mozilla.org/developers/). It's the same
   zip for both.
4. Listing text, permission justifications, data disclosures and screenshots
   are in [`store/`](store/STORE_LISTING.md).

CI (`.github/workflows/ci.yml`, `extension` job) runs `package.sh --check` on
every push and PR.

## Privacy

The extension reads only job posting pages on the sites above, and sends data
only when the user saves a job. Disclosed in the
[privacy policy](https://applyluma.com/privacy) under "Browser Extension".
