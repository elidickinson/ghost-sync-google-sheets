
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

const MEMBERS_PAGE_SIZE = 100;
const MAX_EXECUTION_TIME = 5 * 60 * 1000; // 5 minutes (leaving 1-minute safety buffer)



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

/**
 * Helper function to make API calls with retry logic for rate limiting
 * @param {string} url - The API URL to call
 * @param {Object} options - Options for the UrlFetchApp.fetch call
 * @returns {HTTPResponse} The successful response object
 * @throws {Error} If all retries fail
 */
function makeApiCall(url, options) {
  let retryCount = 0;
  const maxRetries = 5;
  let backoffMs = 2000;

  while (retryCount <= maxRetries) {
    const response = UrlFetchApp.fetch(url, options);
    const responseCode = response.getResponseCode();

    if (responseCode >= 200 && responseCode < 300) {
      return response;
    }

    retryCount++;

    if (retryCount > maxRetries) {
      const responseText = response.getContentText();
      throw new Error(`API returned status code: ${responseCode} - ${responseText}`);
    }

    if (responseCode === 429) {
      Utilities.sleep(backoffMs);
      backoffMs *= 2;
    }
  }
}

function base64UrlEncode(data) {
  const encoded = Utilities.base64Encode(data);
  return encoded.replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}

// ============================================
// STATE MANAGEMENT
// ============================================

const STATE_KEY_PREFIX = 'GHOST_SYNC_STATE_';

function saveState(lastProcessedId, membersSynced, isFullUpdate) {
  const props = PropertiesService.getScriptProperties();
  props.setProperty(STATE_KEY_PREFIX + 'LAST_ID', lastProcessedId || '');
  props.setProperty(STATE_KEY_PREFIX + 'SYNCED_COUNT', membersSynced.toString());
  props.setProperty(STATE_KEY_PREFIX + 'IS_FULL_UPDATE', isFullUpdate.toString());
}

function loadState() {
  const props = PropertiesService.getScriptProperties();
  const lastId = props.getProperty(STATE_KEY_PREFIX + 'LAST_ID');

  if (!lastId && lastId !== '') return null;

  return {
    lastProcessedId: lastId || null,
    membersSynced: parseInt(props.getProperty(STATE_KEY_PREFIX + 'SYNCED_COUNT')) || 0,
    isFullUpdate: props.getProperty(STATE_KEY_PREFIX + 'IS_FULL_UPDATE') === 'true'
  };
}

function clearState() {
  const props = PropertiesService.getScriptProperties();
  props.deleteProperty(STATE_KEY_PREFIX + 'LAST_ID');
  props.deleteProperty(STATE_KEY_PREFIX + 'SYNCED_COUNT');
  props.deleteProperty(STATE_KEY_PREFIX + 'IS_FULL_UPDATE');
}

function createContinuationTrigger() {
  deleteContinuationTriggers();

  ScriptApp.newTrigger('continueSyncFromTrigger')
    .timeBased()
    .after(1 * 60 * 1000)
    .create();
}

function deleteContinuationTriggers() {
  const triggers = ScriptApp.getProjectTriggers();
  for (const trigger of triggers) {
    if (trigger.getHandlerFunction() === 'continueSyncFromTrigger') {
      ScriptApp.deleteTrigger(trigger);
    }
  }
}

// ============================================
// GHOST API
// ============================================

function fetchMembersPage(ghostUrl, adminApiKey, afterId = null) {
  const token = generateToken(adminApiKey);
  let url = `${ghostUrl}/ghost/api/admin/members/?limit=${MEMBERS_PAGE_SIZE}&order=id ASC`;

  if (afterId) {
    const filter = `id:>'${afterId}'`;
    url += `&filter=${encodeURIComponent(filter)}`;
  }

  const response = makeApiCall(url, {
    method: 'get',
    headers: {
      'Authorization': `Ghost ${token}`,
      'Accept-Version': 'v5.0'
    }
  });

  const data = JSON.parse(response.getContentText());
  return data.members || [];
}

function fetchAllMembers(ghostUrl, adminApiKey) {
  let allMembers = [];
  let afterId = null;
  let hasMore = true;

  while (hasMore) {
    const members = fetchMembersPage(ghostUrl, adminApiKey, afterId);

    if (members.length > 0) {
      allMembers = allMembers.concat(members);
      afterId = members[members.length - 1].id;
      hasMore = members.length === MEMBERS_PAGE_SIZE;
    } else {
      hasMore = false;
    }
  }

  return allMembers;
}

function fetchMemberById(ghostUrl, adminApiKey, memberId) {
  const token = generateToken(adminApiKey);
  const url = `${ghostUrl}/ghost/api/admin/members/${memberId}/?include=newsletters,tiers`;

  const response = makeApiCall(url, {
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
// CONTINUATION FUNCTION
// ============================================

function continueSyncFromTrigger() {
  const state = loadState();

  if (!state) {
    Logger.log('No continuation state found, skipping');
    deleteContinuationTriggers();
    return;
  }

  Logger.log(`Resuming sync: afterId=${state.lastProcessedId}, synced=${state.membersSynced}, isFullUpdate=${state.isFullUpdate}`);

  try {
    processMembersSync(state.isFullUpdate, state.lastProcessedId, state.membersSynced);
  } catch (e) {
    Logger.log(`Continuation error: ${e.message}`);
    clearState();
    deleteContinuationTriggers();
    throw e;
  }
}

// ============================================
// SYNC FUNCTION
// ============================================

function syncMembersWithUI(isFullUpdate) {
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

    // For full update, clear existing data
    if (isFullUpdate && sheet.getLastRow() > 1) {
      SpreadsheetApp.getActiveSpreadsheet().toast('🔄 Full Update: Clearing existing data...', 'Ghost Sync', 5);
      sheet.getRange(2, 1, sheet.getLastRow() - 1, sheet.getLastColumn()).clear();
    }

    // Clear any previous state and start fresh
    clearState();
    deleteContinuationTriggers();

    processMembersSync(isFullUpdate, null, 0);

  } catch (e) {
    Logger.log(`Sync error: ${e.message}`);
    SpreadsheetApp.getUi().alert(
      '❌ Sync Failed',
      `Error: ${e.message}\n\nCheck View → Logs for details.`,
      SpreadsheetApp.getUi().ButtonSet.OK
    );
  }
}

function processMembersSync(isFullUpdate, lastProcessedId, membersSynced) {
  const settings = getSettings();
  const sheet = getOrCreateSheet();
  const startTime = Date.now();
  const updateType = isFullUpdate ? 'Full Update' : 'Quick Update';

  Logger.log(`Starting ${updateType}: lastProcessedId=${lastProcessedId || 'null'}, membersSynced=${membersSynced}`);

  let existingMemberIds = {};

  // For quick update on first run, build set of existing IDs
  if (!isFullUpdate && !lastProcessedId && sheet.getLastRow() > 1) {
    SpreadsheetApp.getActiveSpreadsheet().toast('⚡ Quick Update: Checking existing members...', 'Ghost Sync', 5);
    const existingData = sheet.getRange(2, 1, sheet.getLastRow() - 1, 1).getValues();
    for (const row of existingData) {
      if (row[0]) existingMemberIds[row[0]] = true;
    }
    Logger.log(`Quick update: found ${Object.keys(existingMemberIds).length} existing member IDs`);
  }

  let hasMore = true;
  let afterId = lastProcessedId;

  while (hasMore) {
    // Check if we're approaching time limit
    if (Date.now() - startTime > MAX_EXECUTION_TIME) {
      Logger.log(`Time limit reached: ${Date.now() - startTime}ms elapsed. Pausing at afterId=${afterId}, synced=${membersSynced}`);
      saveState(afterId, membersSynced, isFullUpdate);
      createContinuationTrigger();
      SpreadsheetApp.getActiveSpreadsheet().toast(
        `⏸️ ${updateType} paused after ${membersSynced} members. Will resume automatically in 1 minute...`,
        'Ghost Sync',
        10
      );
      return;
    }

    // Fetch next page
    Logger.log(`Fetching members page: afterId=${afterId || 'null'}`);
    const membersPage = fetchMembersPage(settings.ghostUrl, settings.adminApiKey, afterId);
    Logger.log(`Received ${membersPage.length} members from Ghost API`);

    if (membersPage.length === 0) {
      Logger.log('No more members to fetch, completing sync');
      hasMore = false;
      break;
    }

    // Filter for quick update
    const membersToProcess = isFullUpdate
      ? membersPage
      : membersPage.filter(m => !existingMemberIds[m.id]);

    if (membersToProcess.length === 0) {
      Logger.log(`Skipping ${membersPage.length} existing members (quick update)`);
      afterId = membersPage[membersPage.length - 1].id;
      hasMore = membersPage.length === MEMBERS_PAGE_SIZE;
      continue;
    }

    // Fetch full details and build rows
    Logger.log(`Processing ${membersToProcess.length} members`);
    const rows = [];
    for (const member of membersToProcess) {
      const fullMember = fetchMemberById(settings.ghostUrl, settings.adminApiKey, member.id);
      if (fullMember) {
        rows.push(memberToRow(fullMember));
      }
    }

    // Batch write rows
    if (rows.length > 0) {
      const nextRow = sheet.getLastRow() + 1;
      sheet.getRange(nextRow, 1, rows.length, rows[0].length).setValues(rows);
      membersSynced += rows.length;
      Logger.log(`Wrote ${rows.length} rows to sheet at row ${nextRow}. Total synced: ${membersSynced}`);

      SpreadsheetApp.getActiveSpreadsheet().toast(
        `${updateType}: Synced ${membersSynced} members...`,
        'Ghost Sync',
        5
      );
      SpreadsheetApp.flush();
    }

    afterId = membersPage[membersPage.length - 1].id;
    hasMore = membersPage.length === MEMBERS_PAGE_SIZE;
  }

  // Cleanup on completion
  Logger.log(`Sync complete: ${membersSynced} members synced in ${Date.now() - startTime}ms`);
  clearState();
  deleteContinuationTriggers();

  sheet.autoResizeColumns(1, sheet.getLastColumn());

  const lastSyncTime = new Date().toString();
  const currentNote = sheet.getRange('A1').getNote() || '';
  const newNote = isFullUpdate
    ? `Last full sync: ${lastSyncTime}`
    : `Last quick sync: ${lastSyncTime}\n${currentNote}`;
  sheet.getRange('A1').setNote(newNote);

  SpreadsheetApp.getActiveSpreadsheet().toast(
    `✅ ${updateType} complete! Synced ${membersSynced} members`,
    'Ghost Sync',
    5
  );
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
