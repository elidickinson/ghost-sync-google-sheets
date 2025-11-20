# Google Workspace Add-on Deployment Checklist

Use this checklist when deploying Ghost Members Sync as a Google Workspace add-on.

## Pre-Deployment Checklist

- [ ] You have Google Workspace admin access
- [ ] The Apps Script project is owned by a domain account
- [ ] You have tested the script thoroughly in a test spreadsheet
- [ ] You have the Ghost admin API key for testing
- [ ] You have reviewed security considerations

## Cloud Project Setup

- [ ] Created a new Google Cloud Project
- [ ] Named the project appropriately (e.g., "Ghost Members Sync")
- [ ] Noted the Project Number
- [ ] Enabled Google Sheets API
- [ ] Enabled Google Apps Script API
- [ ] Enabled Google Workspace Marketplace SDK

## OAuth Consent Screen

- [ ] Selected "Internal" user type
- [ ] Set app name: "Ghost Members Sync"
- [ ] Added user support email
- [ ] Added developer contact email
- [ ] Added required OAuth scopes:
  - [ ] `https://www.googleapis.com/auth/spreadsheets.currentonly`
  - [ ] `https://www.googleapis.com/auth/script.external_request`
  - [ ] `https://www.googleapis.com/auth/script.scriptapp`
- [ ] Saved consent screen configuration

## Apps Script Configuration

- [ ] Created new Apps Script project
- [ ] Copied `GhostMembersSync.gs` content
- [ ] Copied `appsscript.json` manifest
- [ ] Saved project with meaningful name
- [ ] Linked to the Google Cloud Project (entered Project Number)
- [ ] Verified link in Project Settings

## Deployment Creation

- [ ] Clicked **Deploy → New deployment**
- [ ] Selected **Add-on** deployment type
- [ ] Added version description
- [ ] Clicked **Deploy**
- [ ] **COPIED AND SAVED DEPLOYMENT ID** ← Critical!

## Marketplace Configuration

- [ ] Opened Google Workspace Marketplace SDK Configuration
- [ ] Filled in Application Info:
  - [ ] App name
  - [ ] Short description
  - [ ] Long description
  - [ ] Uploaded app icon (256x256px)
  - [ ] Selected category: Productivity
- [ ] Configured Extensions:
  - [ ] Enabled Google Sheets Add-on
  - [ ] Checked "Deploy using Apps Script Deployment ID"
  - [ ] Pasted Deployment ID
- [ ] Set up Store Listing:
  - [ ] Added privacy policy URL
  - [ ] Added terms of service URL
- [ ] Set Visibility to **Private** (Internal)
- [ ] Saved configuration

## Publication

- [ ] Clicked **Publish** in Marketplace SDK
- [ ] Confirmed publication (no review needed for private)
- [ ] Noted: May take up to 24 hours for changes to propagate

## Testing

- [ ] Opened a new Google Sheet
- [ ] Navigated to **Extensions → Add-ons → Get add-ons**
- [ ] Found "Ghost Members Sync" in organization add-ons
- [ ] Installed the add-on
- [ ] Verified "👻 Ghost Sync" menu appears
- [ ] Opened **Ghost Sync → Settings**
- [ ] Configured Ghost URL and API key
- [ ] Ran **Ghost Sync → Full Update**
- [ ] Verified data synced correctly
- [ ] Tested **Ghost Sync → Quick Update**
- [ ] Tested error handling (invalid API key, etc.)

## Documentation

- [ ] Created internal documentation for users
- [ ] Documented how to get Ghost API keys
- [ ] Documented security best practices
- [ ] Shared installation instructions with team

## Admin Deployment (Optional)

If deploying domain-wide automatically:

- [ ] Logged into Google Admin Console
- [ ] Navigated to **Apps → Google Workspace Marketplace apps**
- [ ] Found "Ghost Members Sync"
- [ ] Selected organizational units for deployment
- [ ] Clicked **Install** or **Add to Domain**
- [ ] Configured installation settings
- [ ] Notified users of new add-on availability

## Post-Deployment

- [ ] Monitored execution logs for errors
- [ ] Checked API quota usage
- [ ] Collected user feedback
- [ ] Set up monitoring/alerting if needed

## Version Update Checklist

When releasing updates:

- [ ] Tested changes in development environment
- [ ] Incremented version number
- [ ] Created new deployment with updated version
- [ ] Noted new Deployment ID
- [ ] Updated Deployment ID in Marketplace SDK
- [ ] Tested update with a single user first
- [ ] Notified users of changes (if significant)
- [ ] Updated documentation as needed

---

## Quick Reference

**Deployment ID Location:** Apps Script Editor → Deploy → Manage deployments → Click deployment → Copy ID

**Marketplace SDK Config:** [Google Cloud Console](https://console.cloud.google.com/) → APIs & Services → Google Workspace Marketplace SDK → Configuration

**Admin Console:** [admin.google.com](https://admin.google.com) → Apps → Google Workspace Marketplace apps

---

## Common Issues & Solutions

### Issue: Can't find add-on in Marketplace
**Solution:** Ensure visibility is set to Private/Internal and you're logged in with domain account

### Issue: OAuth errors after deployment
**Solution:** Verify scopes match in Apps Script manifest, Cloud Console OAuth screen, and Marketplace SDK

### Issue: Deployment ID not working
**Solution:** Ensure you copied the full Deployment ID (format: `AKfycby...`) and it's from an Add-on type deployment

### Issue: Users can't install
**Solution:** Check Google Admin Console → Apps → Google Workspace Marketplace apps → Check allow/block settings

---

## Contact

For technical issues with the script, check the execution logs in Apps Script Editor.
For deployment issues, consult Google Workspace Marketplace documentation.
