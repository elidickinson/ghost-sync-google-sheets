
/**
 * Ghost Members Sync for Google Sheets
 *
 * @OnlyCurrentDoc
 */

// ============================================
// GLOBAL CONSTANTS
// ============================================

const GHOST_HEADERS = [
  'Member ID', 'UUID', 'Email', 'Name', 'Status',
  'Created At', 'Updated At', 'Email Open Rate', 'Email Opened Count',
  'Email Count', 'Note', 'Email Suppressed', 'Labels', 'Newsletters',
  'Tiers', 'Subscriptions', 'Stripe Customer ID', 'Complimentary Plan',
  'Geolocation', 'Attribution ID', 'Attribution URL', 'Attribution Type',
  'Attribution Title', 'Referrer Source', 'Referrer Medium', 'Referrer URL',
  'Unsubscribe URL', 'Last Seen At', 'Last Synced'
];

const MEMBERS_PAGE_SIZE = 100;
const MAX_EXECUTION_TIME = 4.5 * 60 * 1000; // There is a 6 minute limit but we must leave a buffer
const API_REQUEST_DELAY_MS = 10; // Delay between API requests to go easy on the server
const GHOST_MEMBERS_SHEET_NAME = 'Ghost Members';
const SPINNER_ALT_TITLE = 'Ghost sync in progress...';
const STATUS_ROW = 1; // Row 1 for status messages and spinner
const HEADER_ROW = 2; // Row 2 for column headers
const DATA_START_ROW = 3; // Row 3 onwards for member data



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
    .addItem('Cancel Update', 'cancelUpdate')
    .addItem('Show Help', 'showHelp')
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
      const members = fetchMembersPage(ghostUrl, adminApiKey);
      ui.alert('✅ Connection Successful', `Found ${members.length} members in first page`, ui.ButtonSet.OK);
    } catch (e) {
      ui.alert('❌ Connection Failed', e.message, ui.ButtonSet.OK);
      return;
    }
  }

  // Save settings
  props.setProperty('GHOST_URL', ghostUrl);
  props.setProperty('ADMIN_API_KEY', adminApiKey);

  ui.alert('✅ Settings Saved', 'Ready to sync members!', ui.ButtonSet.OK);
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
    if (retryCount === 0 && API_REQUEST_DELAY_MS > 0) {
      Utilities.sleep(API_REQUEST_DELAY_MS);
    }

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

function saveState(lastProcessedId, membersSynced, isFullUpdate, syncStartTime) {
  const props = PropertiesService.getScriptProperties();
  props.setProperty(STATE_KEY_PREFIX + 'LAST_ID', lastProcessedId || '');
  props.setProperty(STATE_KEY_PREFIX + 'SYNCED_COUNT', membersSynced.toString());
  props.setProperty(STATE_KEY_PREFIX + 'IS_FULL_UPDATE', isFullUpdate.toString());
  props.setProperty(STATE_KEY_PREFIX + 'SYNC_START_TIME', syncStartTime.toString());
}

function loadState() {
  const props = PropertiesService.getScriptProperties();
  const lastId = props.getProperty(STATE_KEY_PREFIX + 'LAST_ID');

  if (!lastId && lastId !== '') return null;

  return {
    lastProcessedId: lastId || null,
    membersSynced: parseInt(props.getProperty(STATE_KEY_PREFIX + 'SYNCED_COUNT')) || 0,
    isFullUpdate: props.getProperty(STATE_KEY_PREFIX + 'IS_FULL_UPDATE') === 'true',
    syncStartTime: parseInt(props.getProperty(STATE_KEY_PREFIX + 'SYNC_START_TIME')) || Date.now()
  };
}

function clearState() {
  const props = PropertiesService.getScriptProperties();
  props.deleteProperty(STATE_KEY_PREFIX + 'LAST_ID');
  props.deleteProperty(STATE_KEY_PREFIX + 'SYNCED_COUNT');
  props.deleteProperty(STATE_KEY_PREFIX + 'IS_FULL_UPDATE');
  props.deleteProperty(STATE_KEY_PREFIX + 'SYNC_START_TIME');
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

// fetch IDs of current members one page at a time. We get their details one-by-one with fetchMemberById
function fetchMembersPage(ghostUrl, adminApiKey, afterId = null) {
  const token = generateToken(adminApiKey);
  let url = `${ghostUrl}/ghost/api/admin/members/?limit=${MEMBERS_PAGE_SIZE}&order=id ASC&fields=id`;

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

// Must call fetchMemberById to retrieve Attribution fields because they aren't in the browse endpoint
function fetchMemberById(ghostUrl, adminApiKey, memberId) {
  const token = generateToken(adminApiKey);
  const url = `${ghostUrl}/ghost/api/admin/members/${memberId}/?include=newsletters,subscriptions,tiers`;

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
  const sheetName = GHOST_MEMBERS_SHEET_NAME;
  let sheet = ss.getSheetByName(sheetName);

  if (!sheet) {
    sheet = ss.insertSheet(sheetName);
  }

  return sheet;
}

function setupSheet() {
  const sheet = getOrCreateSheet();

  // Setup status row (row 1) - clear any existing content
  const statusRange = sheet.getRange(STATUS_ROW, 1, 1, GHOST_HEADERS.length);
  statusRange.breakApart();
  statusRange.clear();
  statusRange.clearFormat();

  // Setup headers (row 2)
  const headers = GHOST_HEADERS;
  const headerRange = sheet.getRange(HEADER_ROW, 1, 1, headers.length);
  headerRange
    .setValues([headers])
    .setFontWeight('bold')
    .setBackground('#4285f4')
    .setFontColor('#ffffff');

  // Freeze status row and header row
  sheet.setFrozenRows(2);

  // Remove any existing protections
  const sheetProtections = sheet.getProtections(SpreadsheetApp.ProtectionType.SHEET);
  for (const protection of sheetProtections) {
    protection.remove();
  }

  // Protect the entire sheet with warning on edit
  const protection = sheet.protect().setDescription('Used by Ghost Sync - Don\'t delete any columns');
  protection.setWarningOnly(true);

  sheet.autoResizeColumns(1, headers.length);
}

function updateStatusRow(message) {
  const sheet = getOrCreateSheet();

  if (!message) {
    clearStatusRow();
    return;
  }

  // Merge columns for better centering
  const statusCell = sheet.getRange(STATUS_ROW, 1, 1, 20);
  statusCell
    .merge()
    .setValue(message)
    .setHorizontalAlignment('center')
    .setVerticalAlignment('middle')
    .setFontColor('#856404')
    .setFontWeight('bold');

  SpreadsheetApp.flush();
}

function clearStatusRow() {
  const sheet = getOrCreateSheet();

  hideSpinner();

  // Clear content and formatting
  const statusCell = sheet.getRange(STATUS_ROW, 1, 1, GHOST_HEADERS.length);
  statusCell.breakApart();
  statusCell.clear();
  statusCell.clearFormat();

  SpreadsheetApp.flush();
}

function memberToRow(member, syncTimestamp) {
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
    member.last_seen_at || '',
    new Date(syncTimestamp).toISOString()
  ];

  return rowData;
}

// ============================================
// UI FUNCTIONS
// ============================================

function quickUpdateWithUI() {
  const sheet = getOrCreateSheet();

  // Check if sheet has proper structure (headers should be in row 2)
  if (sheet.getLastRow() >= HEADER_ROW) {
    const headers = sheet.getRange(HEADER_ROW, 1, 1, sheet.getLastColumn()).getValues()[0];

    // Expected headers count
    const expectedHeadersLength = GHOST_HEADERS.length;
    const lastSyncedIndex = GHOST_HEADERS.length - 1;

    // Check key columns including Last Synced (required for quick sync)
    if (headers.length < expectedHeadersLength ||
        headers[0] !== GHOST_HEADERS[0] ||
        headers[1] !== GHOST_HEADERS[1] ||
        headers[lastSyncedIndex] !== GHOST_HEADERS[lastSyncedIndex]) {

      const ui = SpreadsheetApp.getUi();
      ui.alert(
        '⚠️ Quick Update Not Available',
        `The sheet doesn't have the correct column structure.\n\nExpected: ${expectedHeadersLength} columns with "${GHOST_HEADERS[0]}", "${GHOST_HEADERS[1]}", and "${GHOST_HEADERS[lastSyncedIndex]}"\nFound: ${headers.length} columns with "${headers[0] || 'Empty'}", "${headers[1] || 'Empty'}", and "${headers[lastSyncedIndex] || 'Missing'}"\n\nPlease run a "Full Update" to recreate the sheet with the correct structure.`,
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

function cancelUpdate() {
  const state = loadState();
  const triggers = ScriptApp.getProjectTriggers();
  const hasTriggers = triggers.some(t => t.getHandlerFunction() === 'continueSyncFromTrigger');

  if (!state && !hasTriggers) {
    SpreadsheetApp.getUi().alert(
      '🛑 Cancel Update',
      'No updates in progress',
      SpreadsheetApp.getUi().ButtonSet.OK
    );
    return;
  }

  deleteContinuationTriggers();
  clearState();
  clearStatusRow();

  SpreadsheetApp.getUi().alert(
    '✅ Update Cancelled',
    'Any in-progress sync has been cancelled and continuation triggers removed.',
    SpreadsheetApp.getUi().ButtonSet.OK
  );
}

// ============================================
// CONTINUATION FUNCTION
// ============================================

function continueSyncFromTrigger() {
  const state = loadState();

  if (!state) {
    Logger.log('No state, skipping');
    deleteContinuationTriggers();
    return;
  }

  Logger.log(`Resuming: afterId=${state.lastProcessedId}, synced=${state.membersSynced}`);

  try {
    processMembersSync(state.isFullUpdate, state.lastProcessedId, state.membersSynced, state.syncStartTime);
  } catch (e) {
    Logger.log(`Error: ${e.message}`);
    clearState();
    deleteContinuationTriggers();
    updateStatusRow(`Last sync attempt failed: ${e.message}`);
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
    SpreadsheetApp.getActiveSpreadsheet().toast('Preparing to update...', 'Ghost Sync', 3);
    const sheet = getOrCreateSheet();

    if (isFullUpdate) {
      // Full update: clear everything and setup fresh
      sheet.clear();
      setupSheet();
    } else if (sheet.getLastRow() < HEADER_ROW) {
      // Quick update: setup headers if needed
      setupSheet();
      SpreadsheetApp.getActiveSpreadsheet().toast('Sheet setup complete...', 'Ghost Sync', 3);
    }

    // Clear any previous state and start fresh
    clearState();
    deleteContinuationTriggers();

    processMembersSync(isFullUpdate);

  } catch (e) {
    Logger.log(`Error: ${e.message}`);
    updateStatusRow(`❌ Sync Failed: ${e.message}`);
    SpreadsheetApp.getUi().alert(
      'Sync Failed',
      `Error: ${e.message}\n\nCheck View → Logs for details.`,
      SpreadsheetApp.getUi().ButtonSet.OK
    );
  }
}

function showSpinner() {
  const sheet = getOrCreateSheet();
  const image = sheet.insertImage('https://files.sidget.com/spinner.gif', STATUS_ROW, 1);
  image.setAltTextTitle(SPINNER_ALT_TITLE);
  image.setWidth(60);
  image.setHeight(30);
}

function hideSpinner() {
  const sheet = getOrCreateSheet();
  const images = sheet.getImages();
  for (const image of images) {
    if (image.getAltTextTitle() === SPINNER_ALT_TITLE) {
      image.remove();
    }
  }
}

function processMembersSync(isFullUpdate, lastProcessedId = null, membersSynced = 0, syncStartTime = null) {
  const settings = getSettings();
  const sheet = getOrCreateSheet();
  const startTime = Date.now();
  const updateType = isFullUpdate ? 'Full Update' : 'Quick Update';

  if (!syncStartTime) {
    syncStartTime = startTime;
  }

  Logger.log(`${updateType}: afterId=${lastProcessedId || 'null'}, synced=${membersSynced}, syncStartTime=${syncStartTime}`);

  if (!lastProcessedId) {
    // first round so show spinner
    hideSpinner();  // just in case any leftover spinner from a previous failed run
    showSpinner();
    updateStatusRow('Starting sync...');
  }

  let existingMemberIds = {};

  // For quick update on first run, build set of existing IDs
  if (!isFullUpdate && !lastProcessedId && sheet.getLastRow() > HEADER_ROW) {
    updateStatusRow('Checking existing members...');
    const existingData = sheet.getRange(DATA_START_ROW, 1, sheet.getLastRow() - HEADER_ROW, 1).getValues();
    for (const row of existingData) {
      if (row[0]) existingMemberIds[row[0]] = true;
    }
    Logger.log(`Found ${Object.keys(existingMemberIds).length} existing members`);
  }

  let hasMore = true;
  let afterId = lastProcessedId;

  while (hasMore) {
    // Check if we're approaching time limit
    if (Date.now() - startTime > MAX_EXECUTION_TIME) {
      Logger.log(`Time limit: pausing at afterId=${afterId}, synced=${membersSynced}`);
      saveState(afterId, membersSynced, isFullUpdate, syncStartTime);
      createContinuationTrigger();
      updateStatusRow(`On hold after syncing ${membersSynced} members and will resume in 1 minute...`);
      return;  // bail from this function early
    }

    // Fetch next page
    Logger.log(`Fetching page: afterId=${afterId || 'null'}`);
    const membersPage = fetchMembersPage(settings.ghostUrl, settings.adminApiKey, afterId);
    Logger.log(`Received ${membersPage.length} members`);

    if (membersPage.length === 0) {
      Logger.log('No more members, completing');
      hasMore = false;
      break;
    }

    // Filter for quick update
    const membersToProcess = isFullUpdate
      ? membersPage
      : membersPage.filter(m => !existingMemberIds[m.id]);

    if (membersToProcess.length === 0) {
      Logger.log(`Skipping ${membersPage.length} existing members`);
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
        rows.push(memberToRow(fullMember, syncStartTime));
      }
    }

    // Batch write rows
    if (rows.length > 0) {
      const lastRow = sheet.getLastRow();
      const nextRow = lastRow < HEADER_ROW ? DATA_START_ROW : lastRow + 1;
      sheet.getRange(nextRow, 1, rows.length, rows[0].length).setValues(rows);
      membersSynced += rows.length;
      Logger.log(`Wrote ${rows.length} rows at row ${nextRow}, total: ${membersSynced}`);

      updateStatusRow(`Synced ${membersSynced} members...`);
      SpreadsheetApp.flush();
    }

    afterId = membersPage[membersPage.length - 1].id;
    hasMore = membersPage.length === MEMBERS_PAGE_SIZE;

    // Save state after each page to survive unexpected timeouts
    saveState(afterId, membersSynced, isFullUpdate, syncStartTime);
  }

  // Only get this far if we have processed every page of members and still have a little time left
  // Remove members no longer in Ghost (rows with stale Last Synced timestamps)
  let removedCount = 0;
  if (!isFullUpdate && sheet.getLastRow() > HEADER_ROW) {
    Logger.log('Checking for removed members');
    const lastSyncedColumnIndex = GHOST_HEADERS.indexOf('Last Synced') + 1;
    const sheetData = sheet.getRange(DATA_START_ROW, lastSyncedColumnIndex, sheet.getLastRow() - HEADER_ROW, 1).getValues();
    const rowsToDelete = [];
    const syncStartTimeIso = new Date(syncStartTime).toISOString();

    for (let i = 0; i < sheetData.length; i++) {
      const lastSyncedValue = sheetData[i][0];
      if (lastSyncedValue && lastSyncedValue < syncStartTimeIso) {
        rowsToDelete.push(i + DATA_START_ROW);
      }
    }

    if (rowsToDelete.length > 0) {
      Logger.log(`Removing ${rowsToDelete.length} deleted members`);
      for (let i = rowsToDelete.length - 1; i >= 0; i--) {
        sheet.deleteRow(rowsToDelete[i]);
        removedCount++;
      }
    }
  }

  // Cleanup on completion
  Logger.log(`Complete: synced=${membersSynced}, removed=${removedCount}, time=${Date.now() - startTime}ms`);
  clearState();
  deleteContinuationTriggers();
  hideSpinner();

  sheet.autoResizeColumns(1, sheet.getLastColumn());

  const lastSyncTime = new Date().toLocaleString();
  const statusMsg = !isFullUpdate && removedCount > 0
    ? `Sync Complete. Synced ${membersSynced}, removed ${removedCount} | Last ${isFullUpdate ? 'full' : 'quick'} sync: ${lastSyncTime}`
    : `Sync Complete. Synced ${membersSynced} members | Last ${isFullUpdate ? 'full' : 'quick'} sync: ${lastSyncTime}`;

  updateStatusRow(statusMsg);
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
