# Google Workspace Add-on Deployment Guide

This guide will help you deploy Ghost Members Sync as an internal add-on within your Google Workspace domain.

## Deployment Options

There are two ways to deploy this add-on:

1. **Domain-Wide Internal Add-on** (Recommended) - Deploy to your entire Google Workspace domain via Google Workspace Marketplace
2. **Shared Script** (Quick Start) - Share the script directly with users in your organization

---

## Option 1: Domain-Wide Internal Add-on (Recommended)

This method publishes the add-on privately to your Google Workspace domain, making it available to all users through the Google Workspace Marketplace.

### Benefits
- Users can install from Google Workspace Marketplace within your domain
- Centralized management and updates
- Professional deployment experience
- Admin can deploy to entire organization or specific OUs

### Prerequisites

- Google Workspace admin access
- Domain-owned Google Cloud project
- The Apps Script project must be owned by an account in your domain

### Step-by-Step Deployment

#### 1. Prepare the Apps Script Project

1. Open the Apps Script Editor:
   - Create a new Google Sheet or use an existing one
   - Go to **Extensions → Apps Script**

2. Copy the project files:
   - Copy the contents of `GhostMembersSync.gs` into the editor
   - Replace the `appsscript.json` content with the provided manifest

3. Save the project with a meaningful name like "Ghost Members Sync"

#### 2. Set Up Google Cloud Project

1. Create a standard Google Cloud Project:
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Click **Create Project**
   - Name it (e.g., "Ghost Members Sync")
   - Select your organization
   - Note the Project Number

2. Enable Required APIs:
   - Go to **APIs & Services → Library**
   - Enable **Google Sheets API**
   - Enable **Google Apps Script API**

3. Configure OAuth Consent Screen:
   - Go to **APIs & Services → OAuth consent screen**
   - Select **Internal** (this limits to your domain)
   - Fill in:
     - App name: "Ghost Members Sync"
     - User support email: Your admin email
     - Developer contact: Your admin email
   - Add scopes:
     - `https://www.googleapis.com/auth/spreadsheets.currentonly`
     - `https://www.googleapis.com/auth/script.external_request`
     - `https://www.googleapis.com/auth/script.scriptapp`

#### 3. Link Apps Script to Cloud Project

1. In Apps Script Editor, go to **Project Settings** (gear icon)
2. Under **Google Cloud Platform (GCP) Project**:
   - Click **Change project**
   - Enter your Cloud Project Number
   - Click **Set project**

#### 4. Create a Deployment

1. In Apps Script Editor, click **Deploy → New deployment**
2. Click the **Select type** gear icon
3. Select **Add-on**
4. Fill in deployment details:
   - Description: "Production deployment for Ghost Members Sync"
   - Version: v1
5. Click **Deploy**
6. **IMPORTANT**: Copy and save the **Deployment ID** (you'll need this)

#### 5. Enable Google Workspace Marketplace SDK

1. In Google Cloud Console, go to **APIs & Services → Library**
2. Search for "Google Workspace Marketplace SDK"
3. Click **Enable**
4. Go to **APIs & Services → Google Workspace Marketplace SDK → Configuration**

#### 6. Configure Marketplace Listing

1. In the Marketplace SDK Configuration:

   **Application Info:**
   - App name: `Ghost Members Sync`
   - Short description: `Sync your Ghost members list to Google Sheets with attribution tracking`
   - Long description: (Copy from README.md and expand)
   - App Icon: Upload the Ghost logo (256x256px)
   - Category: `Productivity`

   **Extensions:**
   - ✓ Enable Google Sheets Add-on
   - Check "Deploy using Apps Script Deployment ID"
   - Paste your **Deployment ID** from Step 4

   **Store Listing:**
   - Privacy policy URL: Your company's privacy policy URL
   - Terms of service URL: Your company's ToS URL (or use MIT license URL)

   **Visibility:**
   - Select **Private** (Internal)
   - This restricts installation to your domain only

2. Save the configuration

#### 7. Publish the Add-on

1. In Marketplace SDK Configuration, click **Publish**
2. Since this is a private add-on, it will be published immediately without Google review
3. Note: Changes may take up to 24 hours to propagate (usually faster)

#### 8. Install the Add-on

For individual users:
1. Open Google Sheets
2. Go to **Extensions → Add-ons → Get add-ons**
3. Search for "Ghost Members Sync" (filter by "My Organization")
4. Click **Install**

For admin-wide deployment:
1. Go to [Google Admin Console](https://admin.google.com)
2. Navigate to **Apps → Google Workspace Marketplace apps**
3. Search for your add-on
4. Click **Add to Domain** or deploy to specific OUs
5. Configure installation settings

---

## Option 2: Shared Script (Quick Start)

This is a simpler method where you share the Apps Script directly with users.

### Steps

1. Create the Apps Script project as described in Option 1, Step 1
2. Copy both `GhostMembersSync.gs` and `appsscript.json` into the editor
3. Save and test the script
4. Share access:
   - Click **Deploy → Test deployments**
   - Click **Install** to test yourself

5. For other users:
   - Each user copies the script files into their own Sheet's Apps Script editor
   - OR you share a template sheet with the script pre-installed

### Limitations of Shared Script Method

- Users must manually copy the script or sheet
- No centralized updates
- Less professional experience
- Each user maintains their own copy

---

## Testing Your Deployment

1. Open a new Google Sheet
2. Install the add-on (via Marketplace or manual installation)
3. Verify the "👻 Ghost Sync" menu appears
4. Click **Ghost Sync → Settings** and configure:
   - Ghost site URL
   - Admin API Key
   - Attribution preferences
5. Run a test sync with **Ghost Sync → Full Update**
6. Verify data appears correctly in the sheet

---

## Post-Deployment Management

### Updating the Add-on

1. Make changes to your Apps Script code
2. Create a new deployment:
   - **Deploy → New deployment**
   - Select **Add-on** type
   - Increment version (e.g., v2)
3. Update the Deployment ID in Marketplace SDK configuration
4. Users will automatically get updates on their next use

### Monitoring Usage

- Check execution logs: **Apps Script Editor → Executions**
- Monitor API quotas in Google Cloud Console
- Review user feedback

### Best Practices

1. **Test thoroughly** before deploying domain-wide
2. **Document clearly** - provide internal documentation for users
3. **Monitor scopes** - only request necessary permissions
4. **Handle errors gracefully** - ensure good error messages
5. **Version carefully** - test updates before pushing to users
6. **Communicate changes** - notify users of major updates

---

## Security Considerations

### OAuth Scopes

This add-on requests minimal permissions:
- **spreadsheets.currentonly**: Access only to the spreadsheet where it's installed (not all user sheets)
- **script.external_request**: Ability to make external API calls to Ghost
- **script.scriptapp**: Required for add-on functionality

### API Key Storage

- API keys are stored using Apps Script Properties Service
- Keys are encrypted at rest by Google
- Keys are only accessible within the specific spreadsheet
- Recommend users share sheets as "View Only" when possible

### Domain-Wide Considerations

- Even as a private add-on, follow security best practices
- Educate users about protecting their Ghost API keys
- Consider creating a dedicated Ghost integration with limited permissions
- Regularly audit who has access to sheets with API keys

---

## Troubleshooting

### "Add-on not found in Marketplace"

- Ensure you published as Private/Internal
- Check that you're logged in with a domain account
- Allow up to 24 hours for propagation

### "Authorization Required" errors

- Verify OAuth scopes match in both Apps Script and Cloud Console
- Re-link the Cloud Project if needed
- Clear authorization and re-authorize

### "API limit exceeded"

- Apps Script has daily quotas
- For large member lists (>10k), sync may take multiple executions
- Consider requesting quota increases in Cloud Console

### Users can't install the add-on

- Verify user is part of your Google Workspace domain
- Check admin hasn't blocked add-on installations
- Ensure add-on is published with correct visibility settings

---

## Support Resources

- [Google Apps Script Add-ons Documentation](https://developers.google.com/apps-script/add-ons)
- [Google Workspace Marketplace SDK](https://developers.google.com/workspace/marketplace)
- [Apps Script Quotas](https://developers.google.com/apps-script/guides/services/quotas)
- [Ghost Admin API Documentation](https://ghost.org/docs/admin-api/)

---

## Migration from Manual Installation

If users are currently using the manual installation method (copying the script):

1. Deploy the add-on to your domain following Option 1
2. Have users install the add-on from Marketplace
3. Existing sheets with the manual script will continue working
4. For new sheets, they can use the add-on installation
5. Optionally, remove the manual script from existing sheets after installing the add-on

---

## License

MIT License - This deployment guide and the Ghost Members Sync add-on are provided as-is.
