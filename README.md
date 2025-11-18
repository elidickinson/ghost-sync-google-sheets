# Ghost Members Sync for Google Sheets

Sync your Ghost members list to Google Sheets for analysis, reporting, and building custom workflows on top of your membership data. This includes the [hard to access](https://forum.ghost.org/t/provide-source-in-member-api-csv/52412) attribution/referral fields.

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
   - Click **"Go to Your Sheet Name (unsafe)"**
5. Review the permissions:
   - **See, edit, create, and delete spreadsheet** - needed to write member data to this spreadsheet
   - **Connect to an external service** - needed to call Ghost API. Member data flows from the API to this spreadsheet and nowhere else.
6. Click **Allow**

You should only have to do this once.

## Setup

1. Click **Ghost Sync → Settings**
2. Enter your **Ghost admin site URL** (e.g., `https://example.ghost.io/`)
3. Enter your **Admin API Key**:
   - Go to Ghost Admin → Settings → Integrations
   - Create a custom integration or use an existing one
   - Copy the Admin API Key (format: `id:secret` with a colon)
4. Choose whether to include **attribution data** (signup sources, and referrers for each member)
   - Attribution fetching significantly increases sync time as it requires individual API calls per member
5. Optionally test the connection before saving

## Sharing & Permissions

**⚠️ Important: Sharing Considerations**

Your Ghost Admin API Key gives full administrative access to your Ghost site (read/write members, posts, settings, etc.). Anyone with **editor** access to this spreadsheet can potentially access the API key:

- **Editors** can view the API key via Apps Script → Project Settings or by running code to read properties
- **Viewers** cannot access the key through normal means

**Best practices when sharing:**
- Only share with trusted collaborators
- Share as **"View only"** when possible - viewers can see member data but not the API key
- Create separate analysis sheets that reference the Ghost Members sheet for untrusted users
- If the API key is compromised, revoke it in Ghost Admin → Settings → Integrations and create a new one

## Using the Sync

### Full Update
**Ghost Sync → Full Update**

- Clears the sheet and rebuilds from scratch
- Fetches all members fresh from Ghost
- Use this:
  - For your first sync
  - If column structure changes
  - If you suspect data inconsistencies

### Quick Update
**Ghost Sync → Quick Update**

- Only fetches attribution data from new members instead of all members.
- Same as Full Update if you are not syncing attribution.
- Must complete at least one Full Update first.


## Working with Your Data

**Do not edit the "Ghost Members" sheet directly.** Instead:

1. **Create additional sheets** that reference the Ghost Members data
2. Use formulas like `=QUERY('Ghost Members'!A:Z, "SELECT * WHERE E='paid'")` to filter
3. Build pivot tables, charts, and custom views on separate sheets
4. This approach preserves your analysis when Ghost Members refreshes

### Useful Examples

Filter paid members:
```
=QUERY('Ghost Members'!A:Z, "SELECT * WHERE E='paid'")
```

Count members by status:
```
=COUNTIF('Ghost Members'!E:E, "paid")
```

Find members with specific label:
```
=FILTER('Ghost Members'!A:Z, REGEXMATCH('Ghost Members'!M:M, "VIP"))
```

## Technical Architecture

### How It Works

This script handles Google Apps Script's 6-minute execution time limit by breaking large sync operations into smaller chunks that can resume automatically:

1. **Authentication**: Generates JWT tokens using Ghost's Admin API Key (HMAC-SHA256 signed)
2. **Pagination**: Fetches members in pages of 100, ordered by ID ascending
3. **Continuation Pass Style**: When approaching the time limit, the script saves its state:
   - Stores current page position, last member processed, and sync mode
   - Sets up a time-based trigger to automatically resume after 1-2 minutes
   - The continuation trigger runs `continueSyncFromTrigger()` to pick up exactly where it left off
4. **State Management**: Saves sync state to these Script Properties:
   - `syncMode`: "fullUpdate" or "quickUpdate"
   - `currentPage`: Current page number being processed
   - `lastMemberId`: ID of last member successfully processed
   - `includeAttribution`: Whether attribution data is being fetched
   - `existingMemberIds`: Map of member IDs for quick updates (stored during first run)
   - `lastSyncTime`: Timestamp of the last sync operation
5. **Automatic Cleanup**: After successful completion, continuation triggers are automatically removed
6. **Row Tracking**: Uses `Last Sync Member` timestamp to identify stale rows for removal

### Data Flow

**Full Update:**
- Clear sheet → Setup headers → Start pagination → Process 100 members/page → Save state & create continuation trigger when near time limit → Continue from trigger → Repeat until all members processed → Optional: fetch attribution per member → Write to sheet → Clean up continuation triggers

**Quick Update:**
- Build existing member ID map → Start pagination → Process 100 members/page → Update existing rows in-place → Append new members → Save state & create continuation trigger when near time limit → Continue from trigger → Repeat until all members processed → Remove stale rows → Clean up continuation triggers

### Synced Fields

**Basic Data:** ID, UUID, Email, Name, Status, Created/Updated timestamps  
**Engagement:** Email open rate, opened count, total email count  
**Segmentation:** Labels, Newsletters, Tiers, Subscriptions  
**Payment:** Stripe Customer ID, Complimentary Plan status  
**Attribution** (optional): ID, URL, Type, Title, Referrer source/medium/URL  
**Tracking:** Geolocation, Unsubscribe URL, Last Seen At  
**Sync Metadata:** Last Sync Member, Last Sync Attribution

### API Endpoints Used

- **Browse Members** (`GET /ghost/api/admin/members/`): Fetches member list with includes for labels, newsletters, subscriptions, tiers
- **Read Member** (`GET /ghost/api/admin/members/{id}/`): Only used when attribution is enabled (attribution fields not available in browse endpoint)

### Rate Limiting & Retry Logic

- 10ms delay between API requests to avoid overwhelming server
- Automatic retry on 429 (rate limit) with exponential backoff: 2s, 4s, 8s, 16s, 32s
- Up to 5 retry attempts before failing
- Ghost Admin API rate limiting depends on your hosting set up

### Security

- Ghost URL and Admin API Key stored in the hidden properties of the spreadsheet
- This script does not save or transmit member data anywhere besides in this spreadsheet
- Anyone with Editor access to the spreadsheet could extract the API Key with a little work

### Limitations

- **Execution Time**: Google Apps Script has 6-minute limit per execution (chunked processing handles this)
- **Quota**: Google Apps Script free tier: 90 minutes/day runtime limit
- **Attribution Cost**: Including attribution requires one API call per member (significantly slower)
- **No Real-Time Sync**: Batch updates only (no webhooks)

### Ghost API Notes

**Member Status Values:** `free`, `paid`, `comped`

**Email Suppression:** Shows suppression reason if suppressed, otherwise "No"

**Filtering:** Uses Ghost's NQL (Node Query Language) for server-side filtering - currently filtering by `id:>'lastId'` for pagination

**Attribution Data:** Not included in browse endpoint - requires individual member lookup. Contains signup source, referrer information from `?ref=` parameters, and attribution tracking.

**Subscriptions vs Status:** Member `status` field shows subscription state, but `subscriptions` array contains historical subscription records including canceled ones.

## Troubleshooting

**Sync seems stuck for a really long time:** Use Cancel Update from menu to clear state, then run a Full Update

**View detailed logs:** Extensions → Apps Script, then click **Execution log** at the top of the editor

## License

MIT
