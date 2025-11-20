# Admin Quick Start Guide

**5-Minute Summary for Google Workspace Admins**

This guide helps Google Workspace admins deploy Ghost Members Sync as an internal add-on.

## What This Does

Allows your organization's users to sync Ghost CMS member data to Google Sheets for analysis, reporting, and integration with other tools.

## Deployment Summary

1. **Create Google Cloud Project** (5 min)
   - Console: https://console.cloud.google.com/
   - Enable: Sheets API, Apps Script API, Marketplace SDK
   - Configure OAuth consent screen as "Internal"

2. **Set Up Apps Script** (3 min)
   - Create new Apps Script project
   - Copy `GhostMembersSync.gs` and `appsscript.json`
   - Link to your Cloud Project

3. **Deploy as Add-on** (2 min)
   - Deploy → New deployment → Add-on type
   - Save the Deployment ID

4. **Configure Marketplace** (5 min)
   - Enable Google Workspace Marketplace SDK
   - Configure app details and paste Deployment ID
   - Set visibility to **Private/Internal**
   - Publish (no review needed for private)

5. **Test & Roll Out** (5 min)
   - Install in a test sheet
   - Test with your Ghost API key
   - Deploy domain-wide via Admin Console (optional)

**Total Time: ~20 minutes**

## Key Files

- **WORKSPACE_DEPLOYMENT.md** - Complete step-by-step guide
- **DEPLOYMENT_CHECKLIST.md** - Checklist for deployment process
- **README.md** - User documentation

## Permissions Required

This add-on requests minimal permissions:
- ✅ `spreadsheets.currentonly` - Access only to the specific sheet where installed (not all sheets)
- ✅ `script.external_request` - Make API calls to Ghost CMS
- ✅ `script.scriptapp` - Required for add-on functionality

## Security Notes

- Deployment as "Internal" restricts to your Google Workspace domain only
- Users store their own Ghost API keys (not centralized)
- Keys are encrypted at rest by Google Apps Script Properties Service
- No data leaves Google's infrastructure except API calls to user's Ghost site

## User Experience

1. User opens Google Sheets
2. Extensions → Add-ons → Get add-ons
3. Search "Ghost Members Sync" (in organization add-ons)
4. Install
5. Configure settings (Ghost URL + API key)
6. Run sync

## Admin Deployment Option

You can deploy this add-on automatically to all users or specific OUs:

1. Google Admin Console → Apps → Google Workspace Marketplace apps
2. Search for your add-on
3. Click "Install" and select OUs
4. Add-on appears automatically for selected users

## Support Resources

- **Detailed Guide**: See WORKSPACE_DEPLOYMENT.md
- **Checklist**: See DEPLOYMENT_CHECKLIST.md
- **Google Docs**: https://developers.google.com/workspace/add-ons
- **Marketplace SDK**: https://developers.google.com/workspace/marketplace

## Troubleshooting

**Can't find add-on in Marketplace?**
- Ensure visibility is "Internal/Private"
- Allow up to 24 hours for propagation
- Verify you're logged in with domain account

**OAuth errors?**
- Check scopes match in Apps Script and Cloud Console
- Re-link Cloud Project if needed

**Users report authorization issues?**
- Ensure OAuth consent screen is configured as "Internal"
- Verify all required scopes are added

## Update Process

To release updates:
1. Modify Apps Script code
2. Create new deployment with incremented version
3. Update Deployment ID in Marketplace SDK
4. Changes roll out automatically to users

## Cost Considerations

- Google Apps Script is free for standard use
- Apps Script has daily quotas (sufficient for most use cases)
- Google Workspace Marketplace private apps are free
- Cloud Project is free (no API costs for this add-on)

## Next Steps

1. Review [WORKSPACE_DEPLOYMENT.md](WORKSPACE_DEPLOYMENT.md) for complete instructions
2. Use [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md) during deployment
3. Test thoroughly before rolling out domain-wide
4. Create internal documentation for your users

---

**Questions?** Consult the detailed deployment guide or Google Workspace support.
