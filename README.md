# Ghost Members Sync for Google Sheets

Sync your Ghost members list to Google Sheets (including attribution fields)

## Installation

1. **Create a new Google Sheet** or open an existing one
2. Click **Extensions → Apps Script**
3. Delete any existing code in the editor
4. **Copy and paste** the entire contents of `GhostMembersSync.gs`
5. Click **Save** (disk icon or Ctrl/Cmd+S)
6. **Reload your spreadsheet** - you should see a new "👻 Ghost Sync" menu

### First Run: Authorization

The first time you use any Ghost Sync function, Google will ask you to authorize the script:

1. Click **Ghost Sync → Settings**
2. You'll see: **"Authorization Required"** - click **Continue**
3. **Select your Google account**
4. You'll see a warning: **"Google hasn't verified this app"**
   - This is normal - it's your own script, not a published app reviewed by Google
   - Click **Advanced** (bottom left)
   - Click **"Go to [Your Sheet Name] (unsafe)"**
5. Click **"Allow"** for the permissions
   - The script needs access to your spreadsheet (just the one you install this in) and external services to communicate with Ghost's API

Note: Google will also send you an email alert that you added an unauthorized app. This is expected for custom scripts.

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
- Automatically runs Quick Update once per day (between 1-4 AM)
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
