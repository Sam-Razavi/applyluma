# ApplyLuma Browser Extension — Phase 1

Save LinkedIn job postings to ApplyLuma with one click.

## Development setup (Load unpacked)

1. Open Chrome and go to `chrome://extensions`
2. Enable **Developer mode** (toggle in the top-right corner)
3. Click **Load unpacked** and select this `applyluma-extension/` folder
4. Pin the extension from the puzzle-piece menu in the toolbar

To reload after code changes: click the refresh icon on the extension card in `chrome://extensions`.

## How to connect

1. Log into [applyluma.com](https://applyluma.com)
2. Go to **Settings → Browser Extension**
3. Click **Copy Access Token**
4. Click the ApplyLuma extension icon in Chrome
5. Paste the token and click **Connect**

The token is stored in `chrome.storage.local` and persists across browser restarts.
Paste a new token any time you re-login to ApplyLuma (tokens rotate on each login).

## Usage

1. Navigate to any LinkedIn job posting (URL must contain `/jobs/view/`)
2. Click the extension icon — fields are pre-filled from the page
3. Edit any field if needed, then click **Save to ApplyLuma**
4. The job appears in your **Saved Jobs** page with list name `Extension`

## Phase 1 scope

- LinkedIn job pages only
- Token paste authentication (no in-extension login)
- Save to ApplyLuma Saved Jobs (list name: "Extension")

## Phase 2 ideas

- Multi-site support (Indeed, Glassdoor, Arbetsförmedlingen)
- In-extension OAuth login
- AI match score preview in popup
- Chrome Web Store publication
