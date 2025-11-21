
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
  'Geolocation', 'Unsubscribe URL', 'Last Seen At', 'Last Sync Member',
  'Attribution ID', 'Attribution URL', 'Attribution Type',
  'Attribution Title', 'Referrer Source', 'Referrer Medium', 'Referrer URL',
  'Last Sync Attribution'
];

const MEMBERS_PAGE_SIZE = 100;
const MAX_EXECUTION_TIME = 4.5 * 60 * 1000; // There is a 6 minute limit but we must leave a buffer
const API_REQUEST_DELAY_MS = 100; // Delay between API requests to go easy on the server
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
    .addItem('⚡ Run Sync Now', 'syncWithUI')
    .addItem('⚡ Quick Sync: new members only', 'addNewOnlyWithUI')
    .addSeparator()
    .addItem('📅 Setup Daily Auto-Update', 'setupDailyAutoUpdate')
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
  const currentIncludeAttribution = props.getProperty('INCLUDE_ATTRIBUTION') !== 'false';

  // Get Ghost URL
  const urlResponse = ui.prompt(
    '⚙️ Ghost URL',
    `Enter your Ghost site URL:\n\nExample: https://yoursite.com\n\nCurrent: ${currentUrl || 'Not set'}\nLeave empty to keep current setting.`,
    ui.ButtonSet.OK_CANCEL
  );

  if (urlResponse.getSelectedButton() !== ui.Button.OK) return;

  let ghostUrl = urlResponse.getResponseText().trim();

  // Empty string means "leave unchanged"
  if (ghostUrl === '') {
    ghostUrl = currentUrl;
  }

  if (!ghostUrl) {
    ui.alert('❌ Error', 'Ghost URL is required', ui.ButtonSet.OK);
    return;
  }

  // remove trailing slash
  if (ghostUrl.endsWith('/')) {
    ghostUrl = ghostUrl.slice(0, -1);
  }

  // Get Admin API Key
  const keyResponse = ui.prompt(
    '🔑 Admin API Key',
    `Enter your Ghost Admin API Key:\n\nFormat: id:secret (with colon)\nGet it from: Ghost Admin → Settings → Integrations\n\nCurrent: ${currentKey ? '(set)' : 'Not set'}\nLeave empty to keep current setting.`,
    ui.ButtonSet.OK_CANCEL
  );

  if (keyResponse.getSelectedButton() !== ui.Button.OK) return;

  let adminApiKey = keyResponse.getResponseText().trim();

  // Empty string means "leave unchanged"
  if (adminApiKey === '') {
    adminApiKey = currentKey;
  }

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

  // Get attribution preference
  const attributionResponse = ui.alert(
    '📊 Attribution Data',
    `Include member attribution data in sync?\n\nAttribution data includes signup source, referrer, and other info about how someone signed up. This data can be useful but including it significantly increases sync time.\n\nCurrent: ${currentIncludeAttribution ? 'Yes' : 'No'}`,
    ui.ButtonSet.YES_NO
  );

  if (attributionResponse === ui.Button.CANCEL) return;

  const includeAttribution = attributionResponse === ui.Button.YES;

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
  props.setProperty('INCLUDE_ATTRIBUTION', includeAttribution.toString());

  ui.alert('✅ Settings Saved', 'Ready to sync members!', ui.ButtonSet.OK);
}

function getSettings() {
  const props = PropertiesService.getDocumentProperties();
  return {
    ghostUrl: props.getProperty('GHOST_URL') || '',
    adminApiKey: props.getProperty('ADMIN_API_KEY') || '',
    includeAttribution: props.getProperty('INCLUDE_ATTRIBUTION') !== 'false'
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
 * @param {string} ghostUrl - Ghost site URL (optional, for auto-authentication)
 * @param {string} adminApiKey - Ghost Admin API Key (optional, for auto-authentication)
 * @returns {HTTPResponse} The successful response object
 * @throws {Error} If all retries fail
 */
function makeApiCall(url, options, ghostUrl = null, adminApiKey = null) {
  let retryCount = 0;
  const maxRetries = 5;
  let backoffMs = 2000;

  options = options || {};
  options.muteHttpExceptions = true;

  // Auto-add Ghost authentication if provided
  if (ghostUrl && adminApiKey) {
    const token = generateToken(adminApiKey);
    options.headers = options.headers || {};
    options.headers['Authorization'] = `Ghost ${token}`;
    options.headers['Accept-Version'] = 'v5.0';
  }

  while (retryCount <= maxRetries) {
    if (retryCount === 0 && API_REQUEST_DELAY_MS > 0) {
      // this is the delay between each new API request (usually very short)
      Utilities.sleep(API_REQUEST_DELAY_MS);
    }

    let rateLimited = false;

    try {
      const response = UrlFetchApp.fetch(url, options);
      const responseCode = response.getResponseCode();

      if (responseCode >= 200 && responseCode < 300) {
        return response;
      }

      if (responseCode === 429) {
        rateLimited = true;
      }

      const responseText = response.getContentText();
      throw new Error(`API returned status code: ${responseCode} - ${responseText}`);

    } catch (e) {
      Logger.log(`API call failed (attempt ${retryCount + 1}/${maxRetries + 1}): ${e.message}`);

      retryCount++;

      if (retryCount > maxRetries) {
        throw e;
      }

      if (rateLimited) {
        // only do the extra sleep on 429
        Utilities.sleep(backoffMs);
        backoffMs *= 2;
      }
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

function saveState(lastProcessedId, membersSynced, isAddNewOnly, syncStartTime) {
  const props = PropertiesService.getScriptProperties();
  props.setProperty(STATE_KEY_PREFIX + 'LAST_ID', lastProcessedId || '');
  props.setProperty(STATE_KEY_PREFIX + 'SYNCED_COUNT', membersSynced.toString());
  props.setProperty(STATE_KEY_PREFIX + 'IS_ADD_NEW_ONLY', isAddNewOnly.toString());
  props.setProperty(STATE_KEY_PREFIX + 'SYNC_START_TIME', syncStartTime.toString());
}

function loadState() {
  const props = PropertiesService.getScriptProperties();
  const lastId = props.getProperty(STATE_KEY_PREFIX + 'LAST_ID');

  if (!lastId && lastId !== '') return null;

  return {
    lastProcessedId: lastId || null,
    membersSynced: parseInt(props.getProperty(STATE_KEY_PREFIX + 'SYNCED_COUNT')) || 0,
    isAddNewOnly: props.getProperty(STATE_KEY_PREFIX + 'IS_ADD_NEW_ONLY') === 'true',
    syncStartTime: parseInt(props.getProperty(STATE_KEY_PREFIX + 'SYNC_START_TIME')) || Date.now()
  };
}

function clearState() {
  const props = PropertiesService.getScriptProperties();
  props.deleteProperty(STATE_KEY_PREFIX + 'LAST_ID');
  props.deleteProperty(STATE_KEY_PREFIX + 'SYNCED_COUNT');
  props.deleteProperty(STATE_KEY_PREFIX + 'IS_ADD_NEW_ONLY');
  props.deleteProperty(STATE_KEY_PREFIX + 'SYNC_START_TIME');
}

function createContinuationTrigger() {
  deleteContinuationTriggers();

  // make a trigger for just slightly in the future for the next batch
  // (seems like Google effectively makes it 1min minmum any way)
  ScriptApp.newTrigger('continueSyncFromTrigger')
    .timeBased()
    .after(100)
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
// DAILY TRIGGER MANAGEMENT
// ============================================

/**
 * Setup or manage the daily auto-update trigger
 * Automatically detects if trigger is enabled and provides appropriate options
 */
function setupDailyAutoUpdate() {
  const ui = SpreadsheetApp.getUi();
  const existingTrigger = getDailyTrigger();

  if (existingTrigger) {
    // Already enabled - offer to disable
    const response = ui.alert(
      '📅 Daily Auto-Update',
      'Status: ENABLED\n\nSync runs automatically every day at midnight.\n\nView execution history: Extensions → Apps Script → Executions\n\nWould you like to disable it?',
      ui.ButtonSet.YES_NO
    );

    if (response === ui.Button.YES) {
      ScriptApp.deleteTrigger(existingTrigger);
      ui.alert('✅ Disabled', 'Daily Auto-Update has been disabled.', ui.ButtonSet.OK);
    }
    return;
  }

  // Not enabled - check settings and offer to enable
  const settings = getSettings();
  if (!settings.ghostUrl || !settings.adminApiKey) {
    ui.alert(
      '⚙️ Settings Required',
      'Please configure your Ghost URL and Admin API Key first:\n\nGhost Sync → Settings',
      ui.ButtonSet.OK
    );
    return;
  }

  const response = ui.alert(
    '📅 Enable Daily Auto-Update?',
    'This will automatically run a Sync once per day at midnight.\n\nEnable now?',
    ui.ButtonSet.YES_NO
  );

  if (response === ui.Button.YES) {
    ScriptApp.newTrigger('dailyQuickUpdate')
      .timeBased()
      .atHour(0)
      .everyDays(1)
      .create();

    ui.alert(
      '✅ Enabled',
      'Daily Auto-Update is now active!\n\nSync will run every day at midnight.\n\nMonitor runs: Extensions → Apps Script → Executions',
      ui.ButtonSet.OK
    );
  }
}

/**
 * Gets the existing daily trigger if it exists
 * @returns {Trigger|null} The daily trigger or null if not found
 */
function getDailyTrigger() {
  const triggers = ScriptApp.getProjectTriggers();
  for (const trigger of triggers) {
    if (trigger.getHandlerFunction() === 'dailyQuickUpdate') {
      return trigger;
    }
  }
  return null;
}

/**
 * Function called by the daily trigger - runs Sync without UI dialogs
 * Errors are automatically logged to Cloud Logging (Extensions → Apps Script → Executions)
 */
function dailyQuickUpdate() {
  const settings = getSettings();

  if (!settings.ghostUrl || !settings.adminApiKey) {
    return;
  }

  startSync(false); // false = not add-new-only mode (full sync with updates and deletions)
}

// ============================================
// GHOST API
// ============================================

// Fetch members with full data (except attribution which requires fetchMemberById)
function fetchMembersPage(ghostUrl, adminApiKey, afterId = null, createdAfter = null) {
  let url = `${ghostUrl}/ghost/api/admin/members/?limit=${MEMBERS_PAGE_SIZE}&order=id ASC&include=labels,newsletters,subscriptions,tiers`;

  const filters = [];
  if (afterId) {
    filters.push(`id:>'${afterId}'`);
  }
  if (createdAfter) {
    filters.push(`created_at:>='${createdAfter}'`);
  }

  if (filters.length > 0) {
    url += `&filter=${encodeURIComponent(filters.join('+'))}`;
  }

  const response = makeApiCall(url, { method: 'get' }, ghostUrl, adminApiKey);
  const data = JSON.parse(response.getContentText());
  return data.members || [];
}

// Must call fetchMemberById to retrieve Attribution fields because they aren't in the browse endpoint
function fetchMemberById(ghostUrl, adminApiKey, memberId) {
  const url = `${ghostUrl}/ghost/api/admin/members/${memberId}/?include=newsletters,subscriptions,tiers`;

  const response = makeApiCall(url, { method: 'get' }, ghostUrl, adminApiKey);
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
    // Protect the entire sheet with warning on edit
    const protection = sheet.protect().setDescription('Used by Ghost Sync - Don\'t delete any columns');
    protection.setWarningOnly(true);
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

}

function setupStatusRowFormatting() {
  const sheet = getOrCreateSheet();
  const statusCell = sheet.getRange(STATUS_ROW, 2, 1, 19);

  if (!statusCell.isPartOfMerge()) {
    statusCell
      .merge()
      .setVerticalAlignment('middle')
      .setFontColor('#856404')
      .setFontWeight('bold')
      .setBackground('#98FB98');
  }
}

function updateStatusRow(message) {
  const sheet = getOrCreateSheet();
  const statusCell = sheet.getRange(STATUS_ROW, 2, 1, 19);
  statusCell.setValue(message);
  SpreadsheetApp.flush();
}

function memberToRow(member, memberSyncTimestamp, attributionSyncTimestamp = null) {
  const attribution = member.attribution || {};

  const mapAndJoin = (arr, key = 'name') => (arr && Array.isArray(arr))
    ? arr.map(item => item[key]).join(', ') : '';

  const labels = mapAndJoin(member.labels) || '';
  const newsletters = mapAndJoin(member.newsletters) || '';
  const tiers = mapAndJoin(member.tiers) || '';
  const subscriptions = mapAndJoin(member.subscriptions, 'status') || '';

  const emailSuppression = (member.email_suppression && member.email_suppression.suppressed === true)
    ? member.email_suppression.info : '';

  const rowData = [
    member.id || '',
    member.uuid || '',
    member.email || '',
    member.name || '',
    member.status || '',
    member.created_at ? new Date(member.created_at) : '',
    member.updated_at ? new Date(member.updated_at) : '',
    member.email_open_rate || '',
    member.email_opened_count || '',
    member.email_count || '',
    member.note || '',
    emailSuppression,
    labels,
    newsletters,
    tiers,
    subscriptions,
    member.stripe_customer_id || '',
    member.comped ? 'Yes' : 'No',
    member.geolocation || '',
    member.unsubscribe_url || '',
    member.last_seen_at ? new Date(member.last_seen_at) : '',
    new Date(memberSyncTimestamp).toISOString()
  ];

  // Include attribution data only if we fetched it
  if (attributionSyncTimestamp !== null) {
    rowData.push(
      attribution.id || '',
      attribution.url || '',
      attribution.type || '',
      attribution.title || '',
      attribution.referrer_source || '',
      attribution.referrer_medium || '',
      attribution.referrer_url || '',
      new Date(attributionSyncTimestamp).toISOString()
    );
  }

  return rowData;
}

// ============================================
// UI FUNCTIONS
// ============================================

/**
 * Validates sheet structure for sync operations
 * @returns {boolean} true if valid, false if invalid (shows alert)
 */
function validateSheetStructure(syncTypeName) {
  const sheet = getOrCreateSheet();

  if (sheet.getLastRow() < HEADER_ROW) return true;

  const headers = sheet.getRange(HEADER_ROW, 1, 1, sheet.getLastColumn()).getValues()[0];
  const expectedHeadersLength = GHOST_HEADERS.length;
  const lastSyncMemberIndex = GHOST_HEADERS.indexOf('Last Sync Member');

  if (headers.length >= expectedHeadersLength &&
      headers[0] === GHOST_HEADERS[0] &&
      headers[1] === GHOST_HEADERS[1] &&
      headers[lastSyncMemberIndex] === GHOST_HEADERS[lastSyncMemberIndex]) {
    return true;
  }

  SpreadsheetApp.getUi().alert(
    `⚠️ ${syncTypeName} Not Available`,
    `The sheet doesn't have the correct column structure.\n\nExpected: ${expectedHeadersLength} columns with "${GHOST_HEADERS[0]}", "${GHOST_HEADERS[1]}", and "${GHOST_HEADERS[lastSyncMemberIndex]}"\nFound: ${headers.length} columns with "${headers[0] || 'Empty'}", "${headers[1] || 'Empty'}", and "${headers[lastSyncMemberIndex] || 'Missing'}"\n\nPlease delete the sheet and run Sync again to recreate it with the correct structure.`,
    SpreadsheetApp.getUi().ButtonSet.OK
  );
  return false;
}

function syncWithUI() {
  if (!validateSheetStructure('Sync')) return;
  syncMembersWithUI(false);
}

function addNewOnlyWithUI() {
  if (!validateSheetStructure('Quick Sync')) return;
  syncMembersWithUI(true);
}

function cancelUpdate() {
  const ui = SpreadsheetApp.getUi();
  const state = loadState();
  const triggers = ScriptApp.getProjectTriggers();
  const hasTriggers = triggers.some(t => t.getHandlerFunction() === 'continueSyncFromTrigger');

  if (!state && !hasTriggers) {
    ui.alert('🛑 Cancel Update', 'No updates in progress', ui.ButtonSet.OK);
    return;
  }

  deleteContinuationTriggers();
  clearState();
  hideSpinner();
  updateStatusRow("Update cancelled");

  ui.alert(
    '✅ Update Cancelled',
    'Any in-progress sync has been cancelled and continuation triggers removed.',
    ui.ButtonSet.OK
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
    processMembersSync(state.isAddNewOnly, state.lastProcessedId, state.membersSynced, state.syncStartTime);
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

/**
 * Core sync logic shared by UI and trigger-based syncs
 * Handles setup and calls processMembersSync
 */
function startSync(isAddNewOnly) {
  const sheet = getOrCreateSheet();

  // Ensure sheet has headers
  if (sheet.getLastRow() < HEADER_ROW) {
    setupSheet();
  }

  clearState();
  deleteContinuationTriggers();
  processMembersSync(isAddNewOnly);
}

function syncMembersWithUI(isAddNewOnly) {
  const settings = getSettings();

  if (!settings.ghostUrl || !settings.adminApiKey) {
    SpreadsheetApp.getActiveSpreadsheet().toast('⚙️ Please configure settings: Ghost Sync → Settings', 'Ghost Sync', 5);
    return;
  }

  SpreadsheetApp.getActiveSpreadsheet().toast('Preparing to sync...', 'Ghost Sync', 3);

  try {
    startSync(isAddNewOnly);
  } catch (e) {
    updateStatusRow(`❌ Sync Failed: ${e.message}`);
    SpreadsheetApp.getUi().alert(
      'Sync Failed',
      `Error: ${e.message}\n\nCheck Extensions → Apps Script → Executions for details.`,
      SpreadsheetApp.getUi().ButtonSet.OK
    );
  }
}

function showSpinner() {
  const sheet = getOrCreateSheet();

  // Base64 encoded spinner GIF
  const base64Gif = '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';
  const blob = Utilities.newBlob(Utilities.base64Decode(base64Gif), 'image/gif', 'spinner.gif');

  sheet.insertImage(blob, STATUS_ROW, 1, 40, 0)
    .setAltTextTitle(SPINNER_ALT_TITLE);
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

/**
 * Fetches member with attribution data if settings enable it
 * @returns {Object} Object with memberData and attributionTimestamp
 */
function getMemberWithAttribution(member, settings, syncStartTime) {
  if (!settings.includeAttribution) {
    return { memberData: member, attributionTimestamp: null };
  }

  const fullMember = fetchMemberById(settings.ghostUrl, settings.adminApiKey, member.id);
  return fullMember
    ? { memberData: fullMember, attributionTimestamp: syncStartTime }
    : { memberData: member, attributionTimestamp: null };
}

function processMembersSync(isAddNewOnly, lastProcessedId = null, membersSynced = 0, syncStartTime = null) {
  const settings = getSettings();
  const sheet = getOrCreateSheet();
  const startTime = Date.now();
  const updateType = isAddNewOnly ? 'Quick Sync (Add New Only)' : 'Sync';

  if (!syncStartTime) {
    syncStartTime = startTime;
  }

  Logger.log(`${updateType}: afterId=${lastProcessedId || 'null'}, synced=${membersSynced}, syncStartTime=${syncStartTime}, includeAttribution=${settings.includeAttribution}`);

  if (!lastProcessedId) {
    // first round so show spinner and setup status row formatting
    hideSpinner();  // just in case any leftover spinner from a previous failed run
    showSpinner();
    setupStatusRowFormatting();
    updateStatusRow('Starting sync...');
  }

  let existingMemberIdToRow = {};
  let createdAfterFilter = null;

  // On first run, build map of member IDs to row numbers
  if (!lastProcessedId && sheet.getLastRow() > HEADER_ROW) {
    updateStatusRow('Checking existing members...');
    const numRows = sheet.getLastRow() - HEADER_ROW;
    const memberIds = sheet.getRange(DATA_START_ROW, 1, numRows, 1).getValues();
    for (let i = 0; i < memberIds.length; i++) {
      if (memberIds[i][0]) {
        existingMemberIdToRow[memberIds[i][0]] = i + DATA_START_ROW;
      }
    }
    Logger.log(`Found ${Object.keys(existingMemberIdToRow).length} existing members`);

    // For Quick Sync, find max Created At to filter API query
    if (isAddNewOnly) {
      const createdAtColumnIndex = GHOST_HEADERS.indexOf('Created At') + 1;
      const createdAtDates = sheet.getRange(DATA_START_ROW, createdAtColumnIndex, numRows, 1).getValues();
      const validDates = createdAtDates.map(row => row[0]).filter(d => d);
      if (validDates.length > 0) {
        const maxDate = validDates.reduce((max, d) => d > max ? d : max);
        createdAfterFilter = new Date(maxDate).toISOString();
        Logger.log(`Quick Sync: filtering for members created after ${createdAfterFilter}`);
      }
    }
  }

  let hasMore = true;
  let afterId = lastProcessedId;

  while (hasMore) {
    // Check if we're approaching time limit
    if (Date.now() - startTime > MAX_EXECUTION_TIME) {
      Logger.log(`Time limit: pausing at afterId=${afterId}, synced=${membersSynced}`);
      saveState(afterId, membersSynced, isAddNewOnly, syncStartTime);
      createContinuationTrigger();
      updateStatusRow(`On hold after syncing ${membersSynced} members and will resume in 1 minute...`);
      return;  // bail from this function early
    }

    // Fetch next page with full member data
    Logger.log(`Fetching page: afterId=${afterId || 'null'}`);
    const membersPage = fetchMembersPage(settings.ghostUrl, settings.adminApiKey, afterId, createdAfterFilter);
    Logger.log(`Received ${membersPage.length} members`);

    if (membersPage.length === 0) {
      Logger.log('No more members, completing');
      hasMore = false;
      break;
    }

    // Split members into existing and new
    const existingMembers = [];
    const newMembers = [];

    for (const member of membersPage) {
      if (existingMemberIdToRow[member.id]) {
        existingMembers.push(member);
      } else {
        newMembers.push(member);
      }
    }

    // Update existing members (unless in add-new-only mode)
    if (!isAddNewOnly && existingMembers.length > 0) {
      for (const member of existingMembers) {
        const rowNumber = existingMemberIdToRow[member.id];
        const row = memberToRow(member, syncStartTime, null);
        sheet.getRange(rowNumber, 1, 1, row.length).setValues([row]);
        membersSynced++;
      }
    } else if (isAddNewOnly) {
      // Count existing members as synced even though we're not updating them
      membersSynced += existingMembers.length;
    }

    // Add new members with attribution fetch
    if (newMembers.length > 0) {
      const rows = newMembers.map(member => {
        const { memberData, attributionTimestamp } = getMemberWithAttribution(member, settings, syncStartTime);
        return memberToRow(memberData, syncStartTime, attributionTimestamp);
      });

      const lastRow = sheet.getLastRow();
      const nextRow = lastRow < HEADER_ROW ? DATA_START_ROW : lastRow + 1;
      sheet.getRange(nextRow, 1, rows.length, rows[0].length).setValues(rows);
      membersSynced += rows.length;
      Logger.log(`Added ${rows.length} new members`);
    }

    updateStatusRow(`Synced ${membersSynced} members...`);
    SpreadsheetApp.flush();

    afterId = membersPage[membersPage.length - 1].id;
    hasMore = membersPage.length === MEMBERS_PAGE_SIZE;

    // Save state after each page to survive unexpected timeouts
    saveState(afterId, membersSynced, isAddNewOnly, syncStartTime);
  }

  // Only get this far if we have processed every page of members and still have a little time left
  // Remove members no longer in Ghost (unless in add-new-only mode). This requires that we've been updating
  //  the `Last Sync Member` column as we go.
  let removedCount = 0;
  if (!isAddNewOnly && sheet.getLastRow() > HEADER_ROW) {
    Logger.log('Checking for removed members');
    const lastSyncMemberColumnIndex = GHOST_HEADERS.indexOf('Last Sync Member') + 1;
    const sheetData = sheet.getRange(DATA_START_ROW, lastSyncMemberColumnIndex, sheet.getLastRow() - HEADER_ROW, 1).getValues();
    const rowsToDelete = [];
    const syncStartTimeIso = new Date(syncStartTime).toISOString();

    for (let i = 0; i < sheetData.length; i++) {
      const lastSyncMemberValue = sheetData[i][0];
      if (lastSyncMemberValue && lastSyncMemberValue < syncStartTimeIso) {
        rowsToDelete.push(i + DATA_START_ROW);
      }
    }

    if (rowsToDelete.length > 0) {
      Logger.log(`Removing ${rowsToDelete.length} deleted members`);
      for (let i = rowsToDelete.length - 1; i >= 0; i--) {
        sheet.deleteRow(rowsToDelete[i]);
      }
      removedCount = rowsToDelete.length;
    }
  }

  // Cleanup on completion
  Logger.log(`Complete: synced=${membersSynced}, removed=${removedCount}, time=${Date.now() - startTime}ms`);
  clearState();
  deleteContinuationTriggers();
  hideSpinner();
  SpreadsheetApp.flush();

  // Brief pause to let Spreadsheet service recover after heavy sync
  Utilities.sleep(1000);

  const syncMode = isAddNewOnly ? 'quick sync' : 'sync';
  const removedMsg = removedCount > 0 ? `, removed ${removedCount}` : '';
  updateStatusRow(`Synced ${membersSynced} members${removedMsg}. Completed ${syncMode}: ${new Date().toLocaleString()}`);
  sheet.getRange(STATUS_ROW, 1, 1, 20).clearFormat();
}

// ============================================
// HELP
// ============================================

function showHelp() {
  const ui = SpreadsheetApp.getUi();

  ui.alert(
  '❓ Help - Ghost Members Sync',
  `QUICK START:
1. Ghost Sync → Settings (enter URL and API key)
2. Ghost Sync → Sync
3. Optional: Ghost Sync → Setup Daily Auto-Update

SYNC OPTIONS:
• Sync: Adds new members, updates existing, removes deleted
• Quick Sync: Only adds new members (doesn't update or remove)
• Daily Auto-Update: Runs Sync daily at midnight

When to use Quick Sync:
• When you only care about seeing data for new members and don't need to remove deleted ones
• Will be much faster if you are fetching attribution data

GETTING YOUR API KEY:
• Ghost Admin → Settings → Integrations
• Click "Add custom integration"
• Copy the Admin API Key (format: id:secret)

WHAT GETS SYNCED:
✓ Member info (email, name, status)
✓ Engagement metrics (opens, clicks)
✓ Attribution data (signup source)
✓ Labels, newsletters, tiers

TROUBLESHOOTING:
• Extensions → Apps Script → Executions for logs

Visit: https://github.com/elidickinson/ghost-sync-google-sheets#readme`,
  ui.ButtonSet.OK
);
}
