
/**
 * Ghost Members Sync for Google Sheets
 *
 * @OnlyCurrentDoc
 */

// ============================================
// GLOBAL CONSTANTS
// ============================================

const GHOST_HEADERS = [
  'Member ID', 'UUID', 'Email', 'Name', 'Status', 'Subscribed',
  'Created At', 'Updated At', 'Email Open Rate', 'Email Opened Count',
  'Email Count', 'Note', 'Email Suppressed', 'Labels', 'Newsletters',
  'Tiers', 'Subscriptions', 'Stripe Customer ID', 'Complimentary Plan',
  'Geolocation', 'Attribution ID', 'Attribution URL', 'Attribution Type',
  'Attribution Title', 'Referrer Source', 'Referrer Medium', 'Referrer URL',
  'Unsubscribe URL', 'Last Seen At'
];



// ============================================
// MENU
// ============================================

function onOpen() {
  SpreadsheetApp.getUi()
    .createMenu('👻 Ghost Sync')
    .addItem('⚙️ Settings', 'showSettings')
    .addSeparator()
    .addItem('⚡ Quick Update', 'quickUpdateWithUI')
    .addItem('🔄 Full Update', 'fullUpdateWithUI')
    .addSeparator()
    .addItem('❓ Help', 'showHelp')
    .addToUi();
}

// ============================================
// SETTINGS (USING SIMPLE PROMPTS)
// ============================================

function showSettings() {
  const ui = SpreadsheetApp.getUi();
  const props = PropertiesService.getDocumentProperties();

  const currentUrl = props.getProperty('GHOST_URL') || '';
  const currentKey = props.getProperty('ADMIN_API_KEY') || '';

  // Get Ghost URL
  const urlResponse = ui.prompt(
    '⚙️ Ghost URL',
    `Enter your Ghost site URL (without trailing slash):\n\nExample: https://yoursite.com\n\nCurrent: ${currentUrl || 'Not set'}`,
    ui.ButtonSet.OK_CANCEL
  );

  if (urlResponse.getSelectedButton() !== ui.Button.OK) return;

  let ghostUrl = urlResponse.getResponseText().trim();
  if (!ghostUrl) {
    ui.alert('❌ Error', 'Ghost URL is required', ui.ButtonSet.OK);
    return;
  }

  // Remove trailing slash
  if (ghostUrl.endsWith('/')) {
    ghostUrl = ghostUrl.slice(0, -1);
  }

  // Get Admin API Key
  const keyResponse = ui.prompt(
    '🔑 Admin API Key',
    `Enter your Ghost Admin API Key:\n\nFormat: id:secret (with colon)\n\nGet it from: Ghost Admin → Settings → Integrations\n\nCurrent: ${currentKey ? '(set)' : 'Not set'}`,
    ui.ButtonSet.OK_CANCEL
  );

  if (keyResponse.getSelectedButton() !== ui.Button.OK) return;

  const adminApiKey = keyResponse.getResponseText().trim();
  if (!adminApiKey) {
    ui.alert('❌ Error', 'Admin API Key is required', ui.ButtonSet.OK);
    return;
  }

  // Validate format
  if (!adminApiKey.includes(':')) {
    ui.alert(
      '❌ Invalid Format',
      'Admin API Key should be in format: id:secret\n\nMake sure you copied the full key from Ghost.',
      ui.ButtonSet.OK
    );
    return;
  }

  // Test connection
  const testResponse = ui.alert(
    '🔌 Test Connection?',
    'Would you like to test the connection before saving?',
    ui.ButtonSet.YES_NO_CANCEL
  );

  if (testResponse === ui.Button.CANCEL) return;

  if (testResponse === ui.Button.YES) {
    try {
      const members = fetchAllMembers(ghostUrl, adminApiKey);
      SpreadsheetApp.getActiveSpreadsheet().toast(`✅ Connection Successful! Found ${members.length} members`, 'Ghost Sync', 5);
    } catch (e) {
      SpreadsheetApp.getActiveSpreadsheet().toast(`❌ Connection Failed: ${e.message}`, 'Ghost Sync', 5);
      return;
    }
  }

  // Save settings
  props.setProperty('GHOST_URL', ghostUrl);
  props.setProperty('ADMIN_API_KEY', adminApiKey);

  SpreadsheetApp.getActiveSpreadsheet().toast('✅ Settings saved! Ready to sync members.', 'Ghost Sync', 5);
}

function getSettings() {
  const props = PropertiesService.getDocumentProperties();
  return {
    ghostUrl: props.getProperty('GHOST_URL') || '',
    adminApiKey: props.getProperty('ADMIN_API_KEY') || ''
  };
}

// ============================================
// JWT TOKEN GENERATION
// ============================================

function generateToken(adminApiKey) {
  const [keyId, keySecret] = adminApiKey.split(':');

  if (!keyId || !keySecret) {
    throw new Error('Invalid Admin API Key format');
  }

  if (!/^[0-9a-fA-F]+$/.test(keySecret)) {
    throw new Error('Invalid Admin API Key: secret must be hexadecimal');
  }

  const header = {
    alg: 'HS256',
    typ: 'JWT',
    kid: keyId
  };

  const now = Math.floor(Date.now() / 1000);
  const payload = {
    iat: now,
    exp: now + 300,
    aud: '/admin/'
  };

  const headerEncoded = base64UrlEncode(JSON.stringify(header));
  const payloadEncoded = base64UrlEncode(JSON.stringify(payload));
  const unsigned = headerEncoded + '.' + payloadEncoded;

  const secretBytes = [];
  for (let i = 0; i < keySecret.length; i += 2) {
    secretBytes.push(parseInt(keySecret.substring(i, i + 2), 16));
  }

  const unsignedBytes = Utilities.newBlob(unsigned).getBytes();
  const signature = Utilities.computeHmacSha256Signature(unsignedBytes, secretBytes);
  const signatureEncoded = base64UrlEncode(signature);

  return unsigned + '.' + signatureEncoded;
}

function base64UrlEncode(data) {
  const encoded = Utilities.base64Encode(data);
  return encoded.replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}

// ============================================
// GHOST API
// ============================================

function fetchAllMembers(ghostUrl, adminApiKey) {
  const token = generateToken(adminApiKey);
  let allMembers = [];
  let page = 1;
  let hasMore = true;

  while (hasMore) {
    const url = `${ghostUrl}/ghost/api/admin/members/?limit=100&page=${page}`;

    const response = UrlFetchApp.fetch(url, {
      method: 'get',
      headers: {
        'Authorization': `Ghost ${token}`,
        'Accept-Version': 'v5.0'
      }
    });

    const data = JSON.parse(response.getContentText());

    if (data.members && data.members.length > 0) {
      allMembers = allMembers.concat(data.members);
      hasMore = data.meta && data.meta.pagination && page < data.meta.pagination.pages;
      page++;
    } else {
      hasMore = false;
    }
  }

  return allMembers;
}

function fetchMemberById(ghostUrl, adminApiKey, memberId) {
  const token = generateToken(adminApiKey);
  const url = `${ghostUrl}/ghost/api/admin/members/${memberId}/?include=newsletters,tiers`;

  const response = UrlFetchApp.fetch(url, {
    method: 'get',
    headers: {
      'Authorization': `Ghost ${token}`,
      'Accept-Version': 'v5.0'
    }
  });

  const data = JSON.parse(response.getContentText());
  return data.members && data.members[0] ? data.members[0] : null;
}

// ============================================
// SHEETS FUNCTIONS
// ============================================

function getOrCreateSheet() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sheetName = 'Ghost Members';
  let sheet = ss.getSheetByName(sheetName);

  if (!sheet) {
    sheet = ss.insertSheet(sheetName);
  }

  return sheet;
}

function setupSheet() {
  const sheet = getOrCreateSheet();

  const headers = GHOST_HEADERS;

  sheet.getRange(1, 1, 1, headers.length).setValues([headers]);

  const headerRange = sheet.getRange(1, 1, 1, headers.length);
  headerRange.setFontWeight('bold');
  headerRange.setBackground('#4285f4');
  headerRange.setFontColor('#ffffff');

  sheet.setFrozenRows(1);

  // Protect the header row to prevent editing
  const protections = sheet.getProtections(SpreadsheetApp.ProtectionType.RANGE);
  for (const protection of protections) {
    protection.remove();
  }

  // Protect the header row to prevent editing
  protectSheetRange(sheet, 1, 1, 1, headers.length, 'Ghost Sync Headers - Do not edit');

  // Protect all data rows to prevent editing
  if (sheet.getLastRow() > 1) {
    protectSheetRange(sheet, 2, 1, sheet.getLastRow() - 1, headers.length, 'Ghost Sync Data - Do not edit');
  }

  for (let i = 1; i <= headers.length; i++) {
    sheet.autoResizeColumn(i);
  }
}

function memberToRow(member) {
  // Get nested objects with fallback
  const attribution = member.attribution || {};

  // Helper function to safely map and join arrays
  const mapAndJoin = (arr, key = 'name') => (arr && Array.isArray(arr))
    ? arr.map(item => item[key]).join(', ') : '';

  // Extract array fields with proper formatting
  const labels = mapAndJoin(member.labels) || '';
  const newsletters = mapAndJoin(member.newsletters) || '';
  const tiers = mapAndJoin(member.tiers) || '';
  const subscriptions = mapAndJoin(member.subscriptions, 'status') || '';

  // Handle email_suppression: show info if suppressed=true, otherwise "No"
  const emailSuppression = (member.email_suppression && member.email_suppression.suppressed === true)
    ? member.email_suppression.info : 'No';

  // Build the row data object first for clarity
  const rowData = [
    // Basic member info
    member.id || '',
    member.uuid || '',
    member.email || '',
    member.name || '',
    member.status || '',
    member.subscribed ? 'Yes' : 'No',
    member.created_at || '',
    member.updated_at || '',

    // Email metrics
    member.email_open_rate || '',
    member.email_opened_count || '',
    member.email_count || '',

    // Additional info
    member.note || '',
    emailSuppression,
    labels,
    newsletters,
    tiers,
    subscriptions,
    member.stripe_customer_id || '',
    member.comped ? 'Yes' : 'No',
    member.geolocation || '',

    // Attribution data
    attribution.id || '',
    attribution.url || '',
    attribution.type || '',
    attribution.title || '',
    attribution.referrer_source || '',
    attribution.referrer_medium || '',
    attribution.referrer_url || '',

    // Tracking
    member.unsubscribe_url || '',
    member.last_seen_at || ''
  ];

  return rowData;
}


// ============================================
// PROTECTION HELPER
// ============================================

function protectSheetRange(sheet, startRow, startCol, numRows, numCols, description) {
  const range = sheet.getRange(startRow, startCol, numRows, numCols);
  const protection = range.protect()
    .setDescription(description)
    .setWarningOnly(false);

  // Remove all editors except the sheet owner
  protection.removeEditors(protection.getEditors());
  if (protection.canDomainEdit()) {
    setDomainEdit(false);
  }
}

// ============================================
// UI FUNCTIONS
// ============================================

function quickUpdateWithUI() {
  const sheet = getOrCreateSheet();

  // Check if sheet has proper structure
  if (sheet.getLastRow() > 0) {
    const headers = sheet.getRange(1, 1, 1, sheet.getLastColumn()).getValues()[0];

    // Expected headers count
    const expectedHeadersLength = GHOST_HEADERS.length;

    // Check both count and key header names
    if (headers.length !== expectedHeadersLength ||
        headers[0] !== GHOST_HEADERS[0] ||
        headers[1] !== GHOST_HEADERS[1] ||
        headers[2] !== GHOST_HEADERS[2]) {

      const ui = SpreadsheetApp.getUi();
      ui.alert(
        '⚠️ Quick Update Not Available',
        `The sheet doesn't have the correct column structure.\n\nExpected: ${expectedHeadersLength} columns starting with "${GHOST_HEADERS[0]}", "${GHOST_HEADERS[1]}", "${GHOST_HEADERS[2]}"\nFound: ${headers.length} columns starting with "${headers[0] || 'Empty'}", "${headers[1] || 'Empty'}", "${headers[2] || 'Empty'}"\n\nPlease run a "Full Update" to recreate the sheet with the correct structure.`,
        ui.ButtonSet.OK
      );
      return;
    }
  }

  syncMembersWithUI(false); // false = quick update (don't clear)
}

function fullUpdateWithUI() {
  syncMembersWithUI(true); // true = full update (clear all)
}

// ============================================
// SYNC FUNCTION
// ============================================

function syncMembersWithUI(isFullUpdate) {
  const ui = SpreadsheetApp.getUi();
  const settings = getSettings();

  if (!settings.ghostUrl || !settings.adminApiKey) {
    SpreadsheetApp.getActiveSpreadsheet().toast('⚙️ Please configure settings: Ghost Sync → Settings', 'Ghost Sync', 5);
    return;
  }

  try {
    const sheet = getOrCreateSheet();

    // Setup headers if needed or if doing a full update
    if (sheet.getLastRow() === 0 || isFullUpdate) {
      setupSheet();
    }

    const updateType = isFullUpdate ? 'Full Update' : 'Quick Update';
    SpreadsheetApp.getActiveSpreadsheet().toast(`🔄 ${updateType}: Fetching members list...`, 'Ghost Sync', 10);

    // Fetch all members list
    const membersList = fetchAllMembers(settings.ghostUrl, settings.adminApiKey);

    if (membersList.length === 0) {
      SpreadsheetApp.getActiveSpreadsheet().toast('ℹ️ No members found in Ghost', 'Ghost Sync', 5);
      return;
    }

    let existingMemberIds = {};

    // For Quick Update, get existing member IDs
    if (!isFullUpdate && sheet.getLastRow() > 1) {
      SpreadsheetApp.getActiveSpreadsheet().toast(`⚡ Quick Update: Checking existing members...`, 'Ghost Sync', 5);
      const existingDataRange = sheet.getRange(2, 1, sheet.getLastRow() - 1, sheet.getLastColumn());
      const existingData = existingDataRange.getValues();

      // Member ID is in column 1 (index 0)
      for (let i = 0; i < existingData.length; i++) {
        const memberId = existingData[i][0];
        if (memberId) {
          existingMemberIds[memberId] = true;
        }
      }
    }

    // Filter to get only new members for quick update
    let newMembersList = [];
    if (isFullUpdate) {
      newMembersList = membersList;
    } else {
      for (let i = 0; i < membersList.length; i++) {
        if (!existingMemberIds[membersList[i].id]) {
          newMembersList.push(membersList[i]);
        }
      }

      if (newMembersList.length === 0) {
        SpreadsheetApp.getActiveSpreadsheet().toast('ℹ️ No new members to sync', 'Ghost Sync', 5);
        return;
      }
    }

    // For full update, clear existing data
    if (isFullUpdate && sheet.getLastRow() > 1) {
      SpreadsheetApp.getActiveSpreadsheet().toast(`🔄 Full Update: Clearing existing data...`, 'Ghost Sync', 5);
      sheet.getRange(2, 1, sheet.getLastRow() - 1, sheet.getLastColumn()).clear();
    }

    // Fetch full details for new members and update sheet as we go
    let membersCount = 0;
    const totalToFetch = newMembersList.length;
    let startRow = isFullUpdate ? 2 : sheet.getLastRow() + 1;

    for (let i = 0; i < totalToFetch; i++) {
      // Update progress every 10 members or at the end
      if (i % 20 === 0 || i === totalToFetch - 1) {
        const progressMessage = `${updateType}: Syncing ${i+1}/${totalToFetch} members...`;
        SpreadsheetApp.getActiveSpreadsheet().toast(progressMessage, 'Ghost Sync', 5);

        // Force the UI to update by using a small flush
        SpreadsheetApp.flush();
      }

      const fullMember = fetchMemberById(settings.ghostUrl, settings.adminApiKey, newMembersList[i].id);

       if (fullMember) {
        // Convert member to row and immediately add to sheet
        const row = memberToRow(fullMember);
        if (row.length > 0) {
          sheet.getRange(startRow + i, 1, 1, row.length).setValues([row]);
          membersCount++;

        }
      } else {
        // Log when a member is skipped
        Logger.log(`Skipping member at index ${i}: ID ${newMembersList[i].id}`);
      }
    }

    // Format
    sheet.autoResizeColumns(1, sheet.getLastColumn());

    // Add timestamp as note on first cell
    const lastSyncTime = new Date().toString();
    const currentNote = sheet.getRange('A1').getNote() || '';
    const newNote = isFullUpdate
      ? `Last full sync: ${lastSyncTime}`
      : `Last quick sync: ${lastSyncTime}\n${currentNote}`;

    sheet.getRange('A1').setNote(newNote);

    SpreadsheetApp.getActiveSpreadsheet().toast(`✅ ${updateType} complete! Synced ${membersCount} members`, 'Ghost Sync', 5);

  } catch (e) {
    Logger.log(`Sync error: ${e.message}`);
    ui.alert(
      '❌ Sync Failed',
      `Error: ${e.message}\n\nCheck View → Logs for details.`,
      ui.ButtonSet.OK
    );
  }
}

// ============================================
// HELP
// ============================================

function showHelp() {
  const ui = SpreadsheetApp.getUi();

  ui.alert(
  '❓ Help - Ghost Members Sync',
  `QUICK START:
1. Click "Ghost Sync → Settings"
2. Enter your Ghost URL and Admin API Key
3. Click "Ghost Sync → Quick Update" or "Full Update"

UPDATE TYPES:
• Quick Update: Only adds new members (faster, incremental)
• Full Update: Replaces all data with fresh data from Ghost

GETTING YOUR API KEY:
• Go to Ghost Admin → Settings → Integrations
• Click "Add custom integration"
• Copy the Admin API Key (format: id:secret)

WHAT GETS SYNCED:
✓ Member info (email, name, status)
✓ Engagement metrics (opens, clicks)
✓ Attribution data (signup source)
✓ Referrer tracking (Google, Twitter, etc.)
✓ Labels, newsletters, tiers

PERMISSIONS:
This add-on only requests:
• Access to THIS spreadsheet (not all your sheets)
• External service access (to call Ghost API)

No auto-sync or background triggers.

TROUBLESHOOTING:
• Check View → Logs for errors
• Verify API key format has colon (:)
• Make sure Ghost URL has no trailing slash

Visit: ghost.org/docs/admin-api`,
  ui.ButtonSet.OK
);
}
