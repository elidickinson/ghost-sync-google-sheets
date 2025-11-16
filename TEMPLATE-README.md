# Ghost Members Sync - Template Sheet

A ready-to-use Google Sheets template for syncing Ghost CMS member data with attribution tracking.

## 🚀 How to Use This Template

### For Users (Super Simple!)

1. **Click "Use Template"** on this sheet
2. **Open the menu**: Ghost Sync → Settings
3. **Enter your Ghost credentials:**
   - Ghost URL: `https://yoursite.com`
   - Admin API Key: Get from Ghost Admin → Settings → Integrations
4. **Click "Sync Members Now"**
5. **Done!** Your members are now in the sheet

## 📋 Getting Your API Key

1. Log into your Ghost Admin panel
2. Go to **Settings → Integrations**
3. Click **"Add custom integration"**
4. Give it a name (e.g., "Google Sheets Sync")
5. Copy the **Admin API Key** (looks like: `abc123:def456...`)
6. Copy your site URL

## ✨ Features

- ✅ Complete member data (email, name, status, etc.)
- ✅ **Source attribution** (where members signed up)
- ✅ **Referrer tracking** (Google, Twitter, Direct, etc.)
- ✅ Engagement metrics (opens, clicks)
- ✅ Labels, newsletters, tiers
- ✅ One-click sync
- ✅ Optional auto-sync every hour

## 🎯 What Gets Synced

### Member Info
- ID, Email, Name, Status
- Created/Updated dates
- Notes

### Engagement
- Email count, open rate
- Last seen date

### Attribution ⭐
- **Where they signed up** (URL, post/page)
- **Referrer source** (Google, Twitter, etc.)
- **Referrer medium** (organic, social, etc.)
- **UTM parameters** (if available)

### Organization
- Labels
- Newsletters
- Tiers
- Stripe info

## 📖 Menu Guide

- **⚙️ Settings** - Configure Ghost connection
- **🔄 Sync Members Now** - Import/update members
- **⏰ Enable Auto-Sync** - Sync every hour automatically
- **⏸️ Disable Auto-Sync** - Turn off auto-sync
- **❓ Help** - Show help info

## 🔧 Troubleshooting

### "Settings Required" error
→ Click Ghost Sync → Settings and enter your API credentials

### "Invalid Admin API Key" error
→ Make sure you copied the **Admin API Key** (not Content API Key)
→ It should have a colon (`:`) in the middle

### Connection test fails
→ Check your Ghost URL is correct (no trailing slash)
→ Verify the API key is valid
→ Check View → Logs for details

### Attribution fields empty
→ Attribution only exists for members who signed up after Ghost 5.0
→ Old members won't have this data

## 🔐 Privacy & Security

- Your API keys are stored securely in this spreadsheet's properties
- No data is sent to third parties
- Direct connection between your sheet and Ghost
- You can revoke access anytime in Ghost Admin

## 💡 Tips

- **First sync**: Takes 1-2 minutes for 1000+ members
- **Auto-sync**: Enable it to keep data fresh
- **Multiple sites**: Make a new copy for each Ghost site
- **Sharing**: Share the sheet, settings stay private per copy

## 🆘 Need Help?

1. Check **View → Logs** for error details
2. Verify your API key in Ghost Admin
3. Test connection in Settings dialog
4. Make sure you're on Ghost 5.0+

## 📦 For Developers

Want to modify this template or install manually?

### Files in Apps Script
- Single file: `GhostMembersSync.gs`
- Everything included (no dependencies)

### To Deploy Your Own Template

1. Create a new Google Sheet
2. Go to Extensions → Apps Script
3. Paste `GhostMembersSync.gs`
4. Save and refresh sheet
5. File → Make a copy → Publish as template

## 🎉 Credits

Built to solve the Zapier attribution problem - now you can track exactly where your Ghost members come from!

---

**Template Version 1.0** | Last updated: November 2025
