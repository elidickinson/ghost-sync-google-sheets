# Ghost Members to SQLite Database

This Python script fetches member data from the Ghost Admin API and stores it in a SQLite database for analysis and backup purposes.

## Features

- Fetches all members from Ghost Admin API using pagination
- Stores member data including:
  - Basic member information (email, name, subscription status, etc.)
  - Member labels and tags
  - Email recipients data with full email campaign details
  - Subscription information with payment details
  - Newsletter subscriptions
  - Tier information
- Creates a normalized SQLite database with proper relationships
- Handles large datasets efficiently with progress reporting

## Database Schema

The script creates the following tables:

### `members`
Core member information including email, name, subscription status, engagement metrics, and additional API fields like status, last_seen_at, and email_suppression.

### `labels`
Member labels/tags for categorization.

### `member_labels`
Junction table linking members to their labels (many-to-many relationship).

### `newsletters`
Newsletter information for member subscriptions.

### `member_newsletters`
Junction table linking members to newsletters.

### `tiers`
Tier information for member subscriptions.

### `member_tiers`
Junction table linking members to tiers.

### `subscriptions`
Subscription information including payment details and status.

### `email_recipients`
Records of emails sent to each member with delivery and engagement status.

### `emails`
Details of email campaigns including subject, content stats, and delivery metrics (without full HTML/Plaintext content to reduce size).

## Setup

1. **Install uv** (if not already installed):
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. **Install dependencies:**
   ```bash
   uv sync
   ```
   
   Or install directly:
   ```bash
   uv add requests python-dotenv
   ```

3. **Create .env file:**
   Copy the provided `.env.example` file to `.env` and set your configuration:
   ```bash
   cp .env.example .env
   ```
   
   Then edit the `.env` file with your values:
   ```
   GHOST_URL=https://your-site.ghost.io
   ADMIN_API_KEY=your_admin_api_key
   ```

4. **Get your Ghost Admin API Key:**
   - Go to your Ghost Admin dashboard
   - Navigate to Settings → Integrations → Add Custom Integration
   - Give it a name like "Member Export"
   - Copy the Admin API Key (format: `id:secret`)
   - Add it to your `.env` file

## Usage

Run the script:
```bash
uv run python members_to_sqlite.py
```

The script will:
1. Create a SQLite database file named `ghost_members.db`
2. Fetch all members, subscriptions, newsletters, tiers, and email data from your Ghost site
3. Store the data in normalized tables
4. Show progress updates during the process

## Output

After completion, you'll have a `ghost_members.db` file containing:
- All member data with proper relationships
- Email engagement history
- Label associations
- Newsletter subscriptions
- Tier information
- Subscription payment details
- Campaign performance data

You can query this database using any SQLite client or Python script.

## Example Queries

```sql
-- Get total members
SELECT COUNT(*) FROM members;

-- Get members with high open rates
SELECT email, name, status, email_open_rate 
FROM members 
WHERE email_open_rate > 80;

-- Get most recent email campaigns
SELECT subject, created_at, opened_count, delivered_count
FROM emails 
ORDER BY created_at DESC 
LIMIT 10;

-- Get members with specific labels
SELECT m.email, m.name, l.name as label
FROM members m
JOIN member_labels ml ON m.id = ml.member_id
JOIN labels l ON ml.label_id = l.id
WHERE l.name = 'Marketing_Optout';

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
```

## Configuration Options

You can modify these settings in the script:

- `MEMBERS_PAGE_SIZE`: Number of members to fetch per API request (default: 100)
- `DATABASE_FILE`: Output database filename (default: 'ghost_members.db')

## Security Notes

- Keep your Admin API key secure and never commit it to version control
- The `.env` file is already included in `.gitignore` to prevent accidental commits
- The API key provides full admin access to your Ghost site

## Dependencies

- Python 3.8+
- `requests` library for HTTP requests
- `python-dotenv` for loading environment variables
- `sqlite3` (included with Python)

## License

This script follows the same license as the parent project.