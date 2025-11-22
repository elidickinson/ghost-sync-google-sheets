# Ghost Members Sync for Google Sheets

Sync your full Ghost CMS member data to a Google Sheet (including attribution/referral fields). 

Features:
 - The sync happens within the Google Sheet. No need to trust a third-party service with your member data.
 - Sync pulls from API to ensure data integrity. Doesn't rely on catching webhooks or being run on a strict schedule. 
 - Can fetch attribution fields (source, utm strings, referrer), which are not available in the normal member export.
 - Optional automatic daily syncing.
 - Open source and free.
 
Limitations:
 - Fetching attribution data is slow because it requires an API call for *each member*. Syncing a Ghost Pro account could do about 125 records per minute.
 - Related to above, Google Sheets has [quota limitations](https://developers.google.com/apps-script/guides/services/quotas) that (I think) won't let you do more than around 20,000 records or 90 minutes of execution per day with a gmail.com account. Or 100,000 records and 6 hours of execution per day for a Google Workspace account. This should only be an issue for getting that first sync to complete with attribution fields enabled.


## Installation

1. **Create a new Google Sheet** or open an existing one
2. Click **Extensions → Apps Script**
3. Delete any existing code in the editor
4. **Copy and paste** the entire contents of `GhostMembersSync.gs`
5. Click **Save** (disk icon or Ctrl/Cmd+S)
6. Go back to your spreadsheet and **Reload the page** - you should see a new "👻 Ghost Sync" menu

### First Run: Authorization

The first time you use any Ghost Sync function, Google will ask you to authorize the script:

1. Click **Ghost Sync → Settings**
2. You'll see: **"Authorization Required"** - click **Continue**
3. **Select your Google account**
4. You may see a warning like: **"Google hasn't verified this app"**
   - This is normal - it's your own script, not a published app reviewed by Google
   - Click **Advanced** (bottom left)
   - Click **"Go to Unnamed Project (unsafe)"**
   - Note: Google will also email you an alert. This is expected for custom Google Sheets scripts.
5. Grant permissions to the script: click **Select All** then scroll to the bottom and **Continue.**
   - The script only requests permission to edit the current Sheet, not anything else in your Google account.

## Dependencies

This project uses [uv](https://github.com/astral-sh/uv) for dependency management.

Install dependencies:
```bash
uv sync
```

## Setup

1. Click **Ghost Sync → Settings**
2. Enter your **Ghost admin site URL** (e.g., `https://example.ghost.io/`)
3. Enter your **Admin API Key** (from Ghost Admin → Settings → Integrations)
4. Choose whether to include **attribution data** (slower sync)
5. Click **Save**

## Using the Sync

### Full Update
**Ghost Sync → Full Update**
- Use for your first sync or when you need to refresh all data
- Clears and rebuilds the sheet completely

### Quick Update
**Ghost Sync → Quick Update**
- Only updates new members or missing attribution data
- Must complete at least one Full Update first

### Daily Auto-Update
**Ghost Sync → Setup Daily Auto-Update**
- Automatically runs Quick Update once per day at midnight
- Requires at least one Full Update to be completed first
- Perfect for keeping your sheet up-to-date without manual intervention
- Use the same menu option to enable, check status, or disable

## Working with Data

**Don't edit the "Ghost Members" sheet directly** - it gets overwritten during sync.

Instead:
1. Create additional sheets that reference the data
2. Use formulas like `=QUERY('Ghost Members'!A:Z, "SELECT * WHERE E='paid'")` to filter
3. Build pivot tables and charts on separate sheets

## Sharing the Sheet & Security Considerations

Your Ghost API key gives full administrative access to your site:
- Only add collaborators to this sheet you trust
- Share as "View only" when possible
- Create separate analysis sheets for untrusted users
- Revoke compromised keys in Ghost Admin → Settings → Integrations

## Troubleshooting

- If sync seems stuck for a long time: Use **Ghost Sync → Cancel Update** then run a new Full Update
- For detailed logs: Go to Extensions → Apps Script → Execution log

## License

MIT
