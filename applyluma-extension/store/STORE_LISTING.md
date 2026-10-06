# ApplyLuma — store listing

Copy-paste source for the Chrome Web Store and Firefox Add-ons (AMO)
submission forms. Keep it in sync with `manifest.json` and the privacy policy
at https://applyluma.com/privacy (section "Browser Extension").

## Basics

| Field | Value |
|---|---|
| Name | ApplyLuma |
| Summary (≤132 chars, = manifest `description`) | Save job postings from LinkedIn, Indeed, Glassdoor, and Arbetsförmedlingen to ApplyLuma with one click. |
| Category (Chrome) | Productivity → Tools |
| Category (Firefox) | Search Tools / Other |
| Language | English |
| Homepage | https://applyluma.com |
| Support | support@applyluma.com |
| Privacy policy URL | https://applyluma.com/privacy |

## Detailed description

```
ApplyLuma turns the job posting you're reading into a tracked, scored lead in your ApplyLuma account — in one click.

SAVE JOBS FROM WHERE YOU FIND THEM
Open a posting on LinkedIn, Indeed, Glassdoor or Arbetsförmedlingen (Platsbanken) and click the ApplyLuma icon. The title, company, link and description are filled in for you. Add a note if you like, then save.

SEE HOW WELL YOU MATCH
Right after saving, the popup shows an AI match score comparing the job against your default CV in ApplyLuma.

TRACK AND TAILOR WITHOUT SWITCHING TABS
Add the job to your application tracker, or start an AI-tailored version of your CV for that specific role, directly from the popup.

NEVER SAVE THE SAME JOB TWICE
Job listings you've already saved or applied to are marked "Saved ✓" / "Applied ✓" in search results, and the toolbar badge shows how many jobs you've saved.

KEYBOARD SHORTCUT
Press Alt+Shift+S on a job posting to save it without opening the popup. (Change it at chrome://extensions/shortcuts.)

Requires a free ApplyLuma account at https://applyluma.com.
```

## Single purpose (Chrome)

```
Save job postings the user is viewing on supported job boards to their ApplyLuma account, and show which postings they have already saved or applied to.
```

## Permission justifications (Chrome "Privacy practices" tab)

| Permission | Justification |
|---|---|
| `storage` | Stores the user's ApplyLuma sign-in token, the job details read from the current posting (kept 15 minutes) and the list of already-saved/applied job URLs used to badge listings. |
| `alarms` | Refreshes the saved/applied job URL list from the ApplyLuma API every 30 minutes so badges stay current. |
| `notifications` | Confirms success or failure when a job is saved with the keyboard shortcut, since no popup is open in that case. |
| Host: `www.linkedin.com`, `se.indeed.com`, `www.indeed.com`, `www.glassdoor.com`, `arbetsformedlingen.se`, `www.arbetsformedlingen.se` | Content scripts read the job title, company, URL and description from job posting pages on these sites, and mark listings the user already saved or applied to. No other sites are accessed. |
| Host: `applyluma-production.up.railway.app` | The ApplyLuma API, where saved jobs are sent and the user's saved/applied list is read. |
| Remote code | No. All JavaScript ships in the package; there is no `eval` and no remotely loaded script. |

## Data usage disclosures (Chrome)

Data collected — tick:
- **Authentication information** — the ApplyLuma access/refresh token.
- **Website content** — job title, company, description and URL of a posting the user chooses to save.

Leave unticked: personally identifiable info, health, financial, personal
communications, location, web history, user activity.

Certify all three:
- Not sold or transferred to third parties outside the approved use cases.
- Not used or transferred for purposes unrelated to the single purpose.
- Not used or transferred to determine creditworthiness or for lending.

## Data collection (Firefox)

Declared in `manifest.json` → `browser_specific_settings.gecko.data_collection_permissions.required`:
`websiteContent`, `authenticationInfo`. Firefox shows these at install time.

## Assets (in this folder)

| File | Use | Size |
|---|---|---|
| `../icons/icon128.png` | Store icon (96px artwork + 16px transparent padding) | 128×128 |
| `screenshot-1-save.png` | Screenshot | 1280×800 |
| `screenshot-2-match.png` | Screenshot | 1280×800 |
| `screenshot-3-synced.png` | Screenshot | 1280×800 |
| `promo-small-440x280.png` | Chrome small promo tile | 440×280 |

Regenerate with `node store/generate-assets.js` after changing the popup UI.

## Reviewer notes (both stores)

```
The extension requires an ApplyLuma account. Test account: <fill in before submitting — a normal (non-admin) user with one CV uploaded>.

To connect: click the toolbar icon → "Login with ApplyLuma" → sign in at applyluma.com → the page copies a token → paste it into the popup → Connect.
Then open any job posting, e.g. https://www.linkedin.com/jobs/view/<id>, and click the icon.

Source is plain, unminified JavaScript with no build step; the uploaded zip is the source.
```
