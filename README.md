# Ghost Members to SQLite

A Python tool to sync Ghost CMS member data to a local SQLite database. This provides fast, local access to your Ghost member data for analysis, reporting, and backup.

## Features

- **Fast local database** - SQLite database with optimized queries and indexes
- **Complete member data** - Includes subscriptions, newsletters, tiers, labels, and email recipients
- **Incremental sync** - Only fetches members updated since last sync
- **Soft delete support** - Tracks deleted members for data integrity
- **Production ready** - Robust error handling and logging
- **Open source** - MIT licensed, no vendor lock-in

## Quick Start

1. **Install dependencies:**
   ```bash
   uv sync
   ```

2. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your Ghost Admin API credentials
   ```

3. **Run the sync:**
   ```bash
   uv run members_to_sqlite.py
   ```

## Configuration

Create a `.env` file with your Ghost Admin API credentials:

```env
GHOST_URL=https://your-site.ghost.io
ADMIN_API_KEY=your_admin_api_key_here
DATABASE_FILE=ghost_members.db
```

Get your Admin API Key from:
- Ghost Admin → Settings → Integrations → Add Integration
- Give it a name and turn on "Admin API"
- Copy the API Key (format: `id:secret`)

## Usage

### Full Sync
Sync all members from Ghost to your local database:
```bash
uv run members_to_sqlite.py
```

### Incremental Sync
Only sync members updated since last run:
```bash
uv run members_to_sqlite.py --incremental
```

### Custom Database Location
Use a custom database file path:
```bash
uv run members_to_sqlite.py --db /path/to/custom.db
```

## Database Schema

The SQLite database includes these tables:

- **`members`** - Core member data and email statistics
- **`labels`** - Member labels and tags
- **`newsletters`** - Newsletter subscriptions
- **`tiers`** - Paid tier information
- **`subscriptions`** - Subscription details and status
- **`email_recipients`** - Email delivery tracking
- **`sync_runs`** - Sync history and metadata

### Key Features

- **Soft deletes** - Members deleted in Ghost are marked but not removed
- **Idempotent updates** - Safe to run multiple times
- **Relationship tracking** - All member relationships preserved
- **Performance optimized** - Batch inserts and proper indexing

## Development

### Running Tests
```bash
uv run pytest -v
```

### Code Quality
```bash
uv run ruff check
uv run ruff format
```

### Project Structure
```
├── members_to_sqlite.py    # Main sync script
├── schema.sql              # Database schema
├── test_*.py               # Test files
├── .env.example            # Environment template
└── README.md               # This file
```

## API Details

This tool uses the Ghost Admin API with:
- **JWT authentication** using HMAC-SHA256
- **Pagination** for handling large member sets
- **Rate limiting** awareness to avoid API limits
- **Error handling** with automatic retries

## Security Considerations

- Your Admin API Key provides full access to your Ghost site
- Store it securely in environment variables, not in code
- Don't commit `.env` files to version control
- Consider using read-only API keys when available

## Troubleshooting

### Common Issues

1. **"Invalid Admin API Key format"**
   - Ensure your key follows the format `id:secret`
   - The secret part must be hexadecimal

2. **"API returned status 401"**
   - Check your API key is correct and not expired
   - Verify the URL matches your Ghost site exactly

3. **Database locked errors**
   - Ensure no other process is using the database
   - The script uses WAL mode for better concurrency

### Debug Mode

Enable debug logging:
```bash
uv run members_to_sqlite.py --debug
```

## Performance

- **Initial sync**: ~1,000 members per minute (depends on API limits)
- **Incremental sync**: Much faster, only processes changes
- **Database size**: ~1KB per member (varies with data)
- **Memory usage**: Low, streams data in batches

## License

MIT License - see LICENSE file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request