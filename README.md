# Ghost Members to SQLite

Sync Ghost CMS member data to a local SQLite database for fast analysis and backup.

## Quick Start

```bash
# Install
uv sync

# Configure
cp .env.example .env
# Edit .env with your Ghost Admin API credentials

# Sync
uv run members_to_sqlite.py
```

## Configuration

Create `.env` with your Ghost Admin API credentials:

```env
GHOST_URL=https://your-site.ghost.io
ADMIN_API_KEY=your_admin_api_key_here
DATABASE_FILE=ghost_members.db
```

Get your Admin API Key from Ghost Admin → Settings → Integrations.

## Usage

```bash
# Full sync
uv run members_to_sqlite.py

# Incremental sync (changes only)
uv run members_to_sqlite.py --incremental

# Custom database location
uv run members_to_sqlite.py --db /path/to/custom.db
```

## Development

```bash
# Run tests
uv run pytest -v

# Code quality
uv run ruff check
uv run ruff format
```

MIT License