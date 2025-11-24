-- Ghost Members Database Schema
-- SQLite database structure for storing Ghost CMS members and related data

-- ============================================
-- MEMBERS TABLE
-- ============================================
-- Core member information including profile data and engagement metrics
CREATE TABLE IF NOT EXISTS members (
    id TEXT PRIMARY KEY,                    -- Ghost member ID
    uuid TEXT UNIQUE NOT NULL,              -- Unique UUID for the member
    email TEXT UNIQUE NOT NULL,             -- Member email address
    name TEXT,                              -- Member display name
    note TEXT,                              -- Admin notes about the member
    geolocation TEXT,                       -- JSON string with geolocation data
    subscribed BOOLEAN NOT NULL DEFAULT 0,  -- Newsletter subscription status
    created_at TEXT NOT NULL,               -- ISO timestamp when member was created
    updated_at TEXT NOT NULL,               -- ISO timestamp when member was last updated
    avatar_image TEXT,                      -- URL to member's avatar image
    comped BOOLEAN NOT NULL DEFAULT 0,      -- Whether member has complimentary access
    email_count INTEGER DEFAULT 0,          -- Total emails sent to member
    email_opened_count INTEGER DEFAULT 0,   -- Total emails opened by member
    email_open_rate INTEGER DEFAULT 0,      -- Email open rate percentage
    status TEXT,                            -- Member status (free, paid, etc.)
    last_seen_at TEXT,                      -- ISO timestamp when member was last active
    unsubscribe_url TEXT,                   -- URL for unsubscribing
    email_suppression TEXT,                 -- JSON string with email suppression information
    deleted_at TEXT,                        -- ISO timestamp when member was soft deleted (NULL if active)
    -- Attribution fields (NULL means not pulled yet)
    attribution_id TEXT,                    -- ID of the attributed post/page
    attribution_type TEXT,                  -- Type of attribution (post, page, etc.)
    attribution_url TEXT,                   -- URL of the attributed content
    attribution_title TEXT,                 -- Title of the attributed content
    attribution_referrer_source TEXT,       -- Referrer source (e.g., Google, Twitter)
    attribution_referrer_medium TEXT,       -- Referrer medium (e.g., organic, social)
    attribution_referrer_url TEXT           -- Full referrer URL
);

-- ============================================
-- LABELS TABLE
-- ============================================
-- Member labels/tags used for categorization and segmentation
CREATE TABLE IF NOT EXISTS labels (
    id TEXT PRIMARY KEY,                    -- Ghost label ID
    name TEXT NOT NULL,                     -- Display name of the label
    slug TEXT UNIQUE NOT NULL,              -- URL-friendly slug for the label
    created_at TEXT NOT NULL,               -- ISO timestamp when label was created
    updated_at TEXT NOT NULL                -- ISO timestamp when label was last updated
);

-- ============================================
-- MEMBER_LABELS JUNCTION TABLE
-- ============================================
-- Many-to-many relationship between members and labels
CREATE TABLE IF NOT EXISTS member_labels (
    member_id TEXT NOT NULL,                -- Foreign key to members.id
    label_id TEXT NOT NULL,                 -- Foreign key to labels.id
    PRIMARY KEY (member_id, label_id),      -- Composite primary key
    FOREIGN KEY (member_id) REFERENCES members (id) ON DELETE CASCADE,
    FOREIGN KEY (label_id) REFERENCES labels (id) ON DELETE CASCADE
);

-- ============================================
-- NEWSLETTERS TABLE
-- ============================================
-- Newsletter information for member subscriptions
CREATE TABLE IF NOT EXISTS newsletters (
    id TEXT PRIMARY KEY,                    -- Ghost newsletter ID
    name TEXT NOT NULL,                     -- Display name of the newsletter
    description TEXT,                       -- Newsletter description
    status TEXT NOT NULL                    -- Newsletter status (active, etc.)
);

-- ============================================
-- MEMBER_NEWSLETTERS JUNCTION TABLE
-- ============================================
-- Many-to-many relationship between members and newsletters
CREATE TABLE IF NOT EXISTS member_newsletters (
    member_id TEXT NOT NULL,                -- Foreign key to members.id
    newsletter_id TEXT NOT NULL,            -- Foreign key to newsletters.id
    PRIMARY KEY (member_id, newsletter_id), -- Composite primary key
    FOREIGN KEY (member_id) REFERENCES members (id) ON DELETE CASCADE,
    FOREIGN KEY (newsletter_id) REFERENCES newsletters (id) ON DELETE CASCADE
);

-- ============================================
-- TIERS TABLE
-- ============================================
-- Tier information for member subscriptions
CREATE TABLE IF NOT EXISTS tiers (
    id TEXT PRIMARY KEY,                    -- Ghost tier ID
    name TEXT NOT NULL,                     -- Display name of the tier
    slug TEXT UNIQUE NOT NULL,              -- URL-friendly slug for the tier
    active BOOLEAN NOT NULL DEFAULT 1,      -- Whether the tier is active
    trial_days INTEGER DEFAULT 0,           -- Number of trial days
    description TEXT,                       -- Tier description
    type TEXT,                              -- Tier type (free, paid, etc.)
    currency TEXT,                          -- Currency code (usd, etc.)
    monthly_price INTEGER DEFAULT 0,        -- Monthly price in cents
    yearly_price INTEGER DEFAULT 0,         -- Yearly price in cents
    created_at TEXT NOT NULL,               -- ISO timestamp when tier was created
    updated_at TEXT NOT NULL                -- ISO timestamp when tier was last updated
);

-- ============================================
-- MEMBER_TIERS JUNCTION TABLE
-- ============================================
-- Many-to-many relationship between members and tiers
CREATE TABLE IF NOT EXISTS member_tiers (
    member_id TEXT NOT NULL,                -- Foreign key to members.id
    tier_id TEXT NOT NULL,                  -- Foreign key to tiers.id
    PRIMARY KEY (member_id, tier_id),       -- Composite primary key
    FOREIGN KEY (member_id) REFERENCES members (id) ON DELETE CASCADE,
    FOREIGN KEY (tier_id) REFERENCES tiers (id) ON DELETE CASCADE
);

-- ============================================
-- SUBSCRIPTIONS TABLE
-- ============================================
-- Subscription information for members
CREATE TABLE IF NOT EXISTS subscriptions (
    id TEXT PRIMARY KEY,                    -- Ghost subscription ID (often from Stripe)
    member_id TEXT NOT NULL,                -- Foreign key to members.id
    customer TEXT,                          -- JSON string with customer data
    status TEXT NOT NULL,                   -- Subscription status (active, canceled, etc.)
    start_date TEXT,                        -- ISO timestamp when subscription started
    default_payment_card_last4 TEXT,        -- Last 4 digits of payment card
    cancel_at_period_end BOOLEAN DEFAULT 0, -- Whether to cancel at period end
    cancellation_reason TEXT,               -- Reason for cancellation
    current_period_end TEXT,                -- ISO timestamp when current period ends
    trial_start_at TEXT,                    -- ISO timestamp when trial started
    trial_end_at TEXT,                      -- ISO timestamp when trial ends
    price TEXT,                             -- JSON string with price data
    tier_id TEXT,                           -- Simple tier ID reference
    tier_name TEXT,                         -- Simple tier name for reference
    offer TEXT,                             -- JSON string with offer data
    FOREIGN KEY (member_id) REFERENCES members (id) ON DELETE CASCADE
);

-- ============================================
-- EMAILS TABLE
-- ============================================
-- Email campaign details and performance metrics
CREATE TABLE IF NOT EXISTS emails (
    id TEXT PRIMARY KEY,                    -- Ghost email ID
    post_id TEXT,                           -- Associated post ID (if applicable)
    uuid TEXT UNIQUE NOT NULL,              -- Unique UUID for the email
    status TEXT NOT NULL,                   -- Email status (submitted, sent, etc.)
    recipient_filter TEXT,                  -- Filter used for recipient selection
    error TEXT,                             -- Error message if email failed
    error_data TEXT,                        -- Additional error data (JSON)
    email_count INTEGER DEFAULT 0,          -- Total recipients for this email
    delivered_count INTEGER DEFAULT 0,      -- Successfully delivered emails
    opened_count INTEGER DEFAULT 0,         -- Total opens
    failed_count INTEGER DEFAULT 0,         -- Failed deliveries
    subject TEXT NOT NULL,                  -- Email subject line
    from_address TEXT,                      -- From email address
    reply_to TEXT,                          -- Reply-to address
    source TEXT,                            -- Email source content (JSON)
    source_type TEXT,                       -- Source content type (lexical, etc.)
    track_opens BOOLEAN DEFAULT 1,          -- Whether open tracking is enabled
    track_clicks BOOLEAN DEFAULT 1,         -- Whether click tracking is enabled
    feedback_enabled BOOLEAN DEFAULT 0,     -- Whether feedback is enabled
    submitted_at TEXT,                      -- ISO timestamp when email was submitted
    newsletter_id TEXT,                     -- Associated newsletter ID
    created_at TEXT NOT NULL,               -- ISO timestamp when email was created
    updated_at TEXT NOT NULL,               -- ISO timestamp when email was last updated
    csd_email_count INTEGER                 -- CSD email count (may be null)
);

-- ============================================
-- EMAIL_RECIPIENTS TABLE
-- ============================================
-- Individual email delivery records for each member
CREATE TABLE IF NOT EXISTS email_recipients (
    id TEXT PRIMARY KEY,                    -- Ghost email recipient ID
    email_id TEXT NOT NULL,                 -- Foreign key to emails.id
    member_id TEXT NOT NULL,                -- Foreign key to members.id
    batch_id TEXT,                          -- Batch ID for bulk sending
    processed_at TEXT,                      -- ISO timestamp when email was processed
    delivered_at TEXT,                      -- ISO timestamp when email was delivered
    opened_at TEXT,                         -- ISO timestamp when email was opened
    failed_at TEXT,                         -- ISO timestamp when email failed
    FOREIGN KEY (member_id) REFERENCES members (id) ON DELETE CASCADE,
    FOREIGN KEY (email_id) REFERENCES emails (id) ON DELETE CASCADE
);

-- ============================================
-- INDEXES FOR PERFORMANCE
-- ============================================

-- Members table indexes
CREATE INDEX IF NOT EXISTS idx_members_email ON members(email);
CREATE INDEX IF NOT EXISTS idx_members_created_at ON members(created_at);
CREATE INDEX IF NOT EXISTS idx_members_subscribed ON members(subscribed);
CREATE INDEX IF NOT EXISTS idx_members_email_open_rate ON members(email_open_rate);
CREATE INDEX IF NOT EXISTS idx_members_status ON members(status);
CREATE INDEX IF NOT EXISTS idx_members_last_seen_at ON members(last_seen_at);
CREATE INDEX IF NOT EXISTS idx_members_deleted_at ON members(deleted_at);

-- Labels table indexes
CREATE INDEX IF NOT EXISTS idx_labels_slug ON labels(slug);
CREATE INDEX IF NOT EXISTS idx_labels_name ON labels(name);

-- Newsletters table indexes
CREATE INDEX IF NOT EXISTS idx_newsletters_name ON newsletters(name);
CREATE INDEX IF NOT EXISTS idx_newsletters_status ON newsletters(status);

-- Tiers table indexes
CREATE INDEX IF NOT EXISTS idx_tiers_slug ON tiers(slug);
CREATE INDEX IF NOT EXISTS idx_tiers_name ON tiers(name);
CREATE INDEX IF NOT EXISTS idx_tiers_active ON tiers(active);

-- Subscriptions table indexes
CREATE INDEX IF NOT EXISTS idx_subscriptions_member_id ON subscriptions(member_id);
CREATE INDEX IF NOT EXISTS idx_subscriptions_status ON subscriptions(status);
CREATE INDEX IF NOT EXISTS idx_subscriptions_current_period_end ON subscriptions(current_period_end);

-- Email recipients table indexes
CREATE INDEX IF NOT EXISTS idx_email_recipients_member_id ON email_recipients(member_id);
CREATE INDEX IF NOT EXISTS idx_email_recipients_email_id ON email_recipients(email_id);

-- Emails table indexes
CREATE INDEX IF NOT EXISTS idx_emails_created_at ON emails(created_at);
CREATE INDEX IF NOT EXISTS idx_emails_status ON emails(status);
CREATE INDEX IF NOT EXISTS idx_emails_subject ON emails(subject);
CREATE INDEX IF NOT EXISTS idx_emails_newsletter_id ON emails(newsletter_id);

-- ============================================
-- VIEWS FOR COMMON QUERIES
-- ============================================

-- Member engagement summary view
CREATE VIEW IF NOT EXISTS member_engagement_summary AS
SELECT
    m.id,
    m.email,
    m.name,
    m.subscribed,
    m.status,
    m.email_count,
    m.email_opened_count,
    m.email_open_rate,
    m.created_at as member_since,
    m.last_seen_at,
    COUNT(DISTINCT er.id) as total_emails_received,
    COUNT(DISTINCT CASE WHEN er.opened_at IS NOT NULL THEN er.id END) as total_emails_opened,
    COUNT(DISTINCT CASE WHEN er.delivered_at IS NOT NULL THEN er.id END) as total_emails_delivered,
    MAX(CASE WHEN er.opened_at IS NOT NULL THEN er.opened_at END) as last_opened_at,
    COUNT(DISTINCT s.id) as active_subscriptions,
    GROUP_CONCAT(DISTINCT t.name, ', ') as tier_names
FROM members m
LEFT JOIN email_recipients er ON m.id = er.member_id
LEFT JOIN subscriptions s ON m.id = s.member_id AND s.status = 'active'
LEFT JOIN member_tiers mt ON m.id = mt.member_id
LEFT JOIN tiers t ON mt.tier_id = t.id
GROUP BY m.id, m.email, m.name, m.subscribed, m.status, m.email_count,
         m.email_opened_count, m.email_open_rate, m.created_at, m.last_seen_at;

-- Email campaign performance view
CREATE VIEW IF NOT EXISTS email_campaign_performance AS
SELECT
    e.id,
    e.subject,
    e.status,
    e.email_count,
    e.delivered_count,
    e.opened_count,
    e.failed_count,
    ROUND((CAST(e.opened_count AS FLOAT) / NULLIF(e.delivered_count, 0)) * 100, 2) as actual_open_rate,
    e.created_at,
    e.submitted_at,
    COUNT(DISTINCT er.member_id) as unique_recipients,
    COUNT(DISTINCT CASE WHEN er.opened_at IS NOT NULL THEN er.member_id END) as unique_opens
FROM emails e
LEFT JOIN email_recipients er ON e.id = er.email_id
GROUP BY e.id, e.subject, e.status, e.email_count, e.delivered_count,
         e.opened_count, e.failed_count, e.created_at, e.submitted_at;

-- Members with labels view
CREATE VIEW IF NOT EXISTS members_with_labels AS
SELECT
    m.id,
    m.email,
    m.name,
    m.subscribed,
    m.status,
    m.email_open_rate,
    m.created_at,
    GROUP_CONCAT(l.name, ', ') as labels
FROM members m
LEFT JOIN member_labels ml ON m.id = ml.member_id
LEFT JOIN labels l ON ml.label_id = l.id
GROUP BY m.id, m.email, m.name, m.subscribed, m.status, m.email_open_rate, m.created_at;

-- Subscription overview view
CREATE VIEW IF NOT EXISTS subscription_overview AS
SELECT
    m.id as member_id,
    m.email,
    m.name,
    m.status as member_status,
    COUNT(DISTINCT s.id) as total_subscriptions,
    COUNT(DISTINCT CASE WHEN s.status = 'active' THEN s.id END) as active_subscriptions,
    COUNT(DISTINCT CASE WHEN s.status = 'canceled' THEN s.id END) as canceled_subscriptions,
    GROUP_CONCAT(DISTINCT t.name, ', ') as tier_names,
    MIN(s.start_date) as earliest_subscription,
    MAX(s.current_period_end) as latest_expiry
FROM members m
LEFT JOIN subscriptions s ON m.id = s.member_id
LEFT JOIN member_tiers mt ON m.id = mt.member_id
LEFT JOIN tiers t ON mt.tier_id = t.id
GROUP BY m.id, m.email, m.name, m.status;

-- Newsletter subscription timeline view
-- Calculates approximate join and leave dates based on email delivery history
CREATE VIEW IF NOT EXISTS newsletter_timeline AS
SELECT
    m.id as member_id,
    m.email,
    m.name,
    m.subscribed as currently_subscribed,
    m.status,
    m.created_at as member_created_at,
    MIN(e.submitted_at) as join_date,
    CASE
        -- If currently subscribed to newsletter, leave date is NULL
        WHEN m.subscribed = 1 THEN NULL
        -- Otherwise, use the last email they received
        ELSE MAX(e.submitted_at)
    END as leave_date,
    COUNT(DISTINCT er.id) as total_emails_received,
    COUNT(DISTINCT CASE WHEN er.opened_at IS NOT NULL THEN er.id END) as emails_opened,
    MAX(er.opened_at) as last_email_opened_at
FROM members m
LEFT JOIN email_recipients er ON m.id = er.member_id
LEFT JOIN emails e ON er.email_id = e.id
GROUP BY m.id, m.email, m.name, m.subscribed, m.status, m.created_at
HAVING MIN(e.submitted_at) IS NOT NULL;

-- ============================================
-- SYNC_RUNS TABLE
-- ============================================
-- Track sync execution history and status
CREATE TABLE IF NOT EXISTS sync_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at TEXT NOT NULL,
    completed_at TEXT,
    status TEXT NOT NULL,
    members_fetched INTEGER DEFAULT 0,
    members_saved INTEGER DEFAULT 0,
    error_message TEXT
);
--
-- ======= REPORTS =======
--

-- Member Cohort Retention (Subscription-Based)
-- Shows % of each cohort still subscribed at month 1, 2, 3, 6, 12
-- Only shows retention for periods that have actually elapsed
/*
WITH cohort_data AS (
  SELECT
    date(join_date, 'start of month') AS cohort_month,
    COUNT(DISTINCT member_id) AS cohort_size,
    COUNT(DISTINCT CASE WHEN leave_date IS NULL OR date(leave_date) >= date(join_date, '+1 months') THEN member_id END) AS m1_active,
    COUNT(DISTINCT CASE WHEN leave_date IS NULL OR date(leave_date) >= date(join_date, '+2 months') THEN member_id END) AS m2_active,
    COUNT(DISTINCT CASE WHEN leave_date IS NULL OR date(leave_date) >= date(join_date, '+3 months') THEN member_id END) AS m3_active,
    COUNT(DISTINCT CASE WHEN leave_date IS NULL OR date(leave_date) >= date(join_date, '+6 months') THEN member_id END) AS m6_active,
    COUNT(DISTINCT CASE WHEN leave_date IS NULL OR date(leave_date) >= date(join_date, '+12 months') THEN member_id END) AS m12_active
  FROM newsletter_timeline
  WHERE join_date IS NOT NULL
  GROUP BY cohort_month
  ORDER BY cohort_month DESC
  LIMIT 24
)
SELECT
  cohort_month,
  cohort_size,
  100.0 AS m0_join,
  CASE WHEN date(cohort_month, '+1 months') <= date('now')
       THEN ROUND(100.0 * m1_active / cohort_size, 1)
       ELSE NULL END AS m1_retention,
  CASE WHEN date(cohort_month, '+2 months') <= date('now')
       THEN ROUND(100.0 * m2_active / cohort_size, 1)
       ELSE NULL END AS m2_retention,
  CASE WHEN date(cohort_month, '+3 months') <= date('now')
       THEN ROUND(100.0 * m3_active / cohort_size, 1)
       ELSE NULL END AS m3_retention,
  CASE WHEN date(cohort_month, '+6 months') <= date('now')
       THEN ROUND(100.0 * m6_active / cohort_size, 1)
       ELSE NULL END AS m6_retention,
  CASE WHEN date(cohort_month, '+12 months') <= date('now')
       THEN ROUND(100.0 * m12_active / cohort_size, 1)
       ELSE NULL END AS m12_retention
FROM cohort_data;
*/


-- ============================================
-- SAMPLE QUERIES
-- ============================================

/*
-- Get top 10 most engaged members
SELECT email, name, status, email_open_rate, email_opened_count, email_count
FROM members
WHERE email_count > 0
ORDER BY email_open_rate DESC, email_opened_count DESC
LIMIT 10;

-- Get recent email campaigns with performance
SELECT subject, created_at, delivered_count, opened_count,
       ROUND((CAST(opened_count AS FLOAT) / delivered_count) * 100, 2) as open_rate
FROM emails
WHERE status = 'submitted'
ORDER BY created_at DESC
LIMIT 20;

-- Find members with specific labels
SELECT m.email, m.name, m.status, m.email_open_rate
FROM members m
JOIN member_labels ml ON m.id = ml.member_id
JOIN labels l ON ml.label_id = l.id
WHERE l.name IN ('Marketing_Optout', 'VIP')
ORDER BY m.email_open_rate DESC;

-- Email engagement trends over time
SELECT
    DATE(created_at) as date,
    COUNT(*) as emails_sent,
    SUM(opened_count) as total_opens,
    ROUND(AVG(email_open_rate), 2) as avg_open_rate
FROM emails
WHERE created_at >= date('now', '-30 days')
GROUP BY DATE(created_at)
ORDER BY date DESC;

-- Members who haven't opened recent emails
SELECT DISTINCT m.email, m.name, m.status, m.email_open_rate
FROM members m
JOIN email_recipients er ON m.id = er.member_id
JOIN emails e ON er.email_id = e.id
WHERE e.created_at >= date('now', '-7 days')
  AND er.opened_at IS NULL
  AND er.delivered_at IS NOT NULL
ORDER BY m.email_open_rate DESC;

-- Get active subscribers by tier
SELECT t.name as tier_name, COUNT(DISTINCT m.id) as member_count
FROM members m
JOIN member_tiers mt ON m.id = mt.member_id
JOIN tiers t ON mt.tier_id = t.id
WHERE m.status = 'paid' AND t.active = 1
GROUP BY t.name
ORDER BY member_count DESC;

-- Find members with active subscriptions expiring soon
SELECT m.email, m.name, s.tier_name, s.current_period_end
FROM members m
JOIN subscriptions s ON m.id = s.member_id
WHERE s.status = 'active'
  AND s.current_period_end <= date('now', '+30 days')
ORDER BY s.current_period_end ASC;

-- Member lifecycle analysis - when members become paid subscribers
SELECT
    DATE(m.created_at) as join_date,
    MIN(DATE(s.start_date)) as first_paid_subscription,
    COUNT(m.id) as members
FROM members m
JOIN subscriptions s ON m.id = s.member_id
WHERE m.status = 'paid'
GROUP BY DATE(m.created_at)
ORDER BY join_date DESC;
*/
