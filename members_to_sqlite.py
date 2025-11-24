#!/usr/bin/env python3
"""
Ghost Members to SQLite Database
Fetches members data from Ghost Admin API and stores it in a SQLite database

Usage:
    python members_to_sqlite.py

Dependencies:
    pip install requests python-dotenv
"""

import json
import time
import hmac
import hashlib
import base64
import requests
import sqlite3
import logging
import sys
import argparse
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# ============================================
# CONFIGURATION
# ============================================


def get_db_connection():
    """Get optimized database connection with performance pragmas"""
    conn = sqlite3.connect(DATABASE_FILE)
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    conn.execute("PRAGMA cache_size = 10000")
    conn.execute("PRAGMA temp_store = MEMORY")
    return conn


GHOST_URL = os.getenv("GHOST_URL")  # Your Ghost URL (no trailing slash)
ADMIN_API_KEY = os.getenv("ADMIN_API_KEY")  # Your Admin API Key (format: id:secret)
MEMBERS_PAGE_SIZE = 100  # Number of members to fetch per page
DATABASE_FILE = os.getenv(
    "DATABASE_FILE", "ghost_members.db"
)  # SQLite database file name
SCHEMA_FILE = "schema.sql"  # Database schema file name


# ============================================
# JWT TOKEN GENERATION (HMAC)
# ============================================


def base64_url_encode(data: bytes) -> str:
    """Base64 URL encode without padding"""
    encoded = base64.b64encode(data).decode("utf-8")
    return encoded.replace("+", "-").replace("/", "_").rstrip("=")


def generate_token(admin_api_key: str) -> str:
    """Generate JWT token for Ghost Admin API"""
    try:
        key_id, key_secret = admin_api_key.split(":")
    except ValueError:
        raise ValueError("Invalid Admin API Key format. Expected: id:secret")

    if not all(c in "0123456789abcdefABCDEF" for c in key_secret):
        raise ValueError("Invalid Admin API Key: secret must be hexadecimal")

    # JWT header
    header = {"alg": "HS256", "typ": "JWT", "kid": key_id}

    # JWT payload
    now = int(time.time())
    payload = {"iat": now, "exp": now + 300, "aud": "/admin/"}

    # Encode header and payload
    header_encoded = base64_url_encode(json.dumps(header).encode("utf-8"))
    payload_encoded = base64_url_encode(json.dumps(payload).encode("utf-8"))
    unsigned = f"{header_encoded}.{payload_encoded}"

    # Convert hex secret to bytes
    secret_bytes = bytes.fromhex(key_secret)

    # Sign with HMAC-SHA256
    signature = hmac.new(
        secret_bytes, unsigned.encode("utf-8"), hashlib.sha256
    ).digest()

    signature_encoded = base64_url_encode(signature)

    return f"{unsigned}.{signature_encoded}"


# ============================================
# GHOST API REQUEST FUNCTION
# ============================================


def make_ghost_request(
    endpoint: str,
    method: str = "GET",
    data: Optional[Dict[str, Any]] = None,
    max_retries: int = 3,
    **kwargs,
) -> Dict[str, Any]:
    """
    Make an authenticated request to the Ghost Admin API with retry logic

    Args:
        endpoint: API endpoint (e.g., '/admin/members/')
        method: HTTP method (default: 'GET')
        data: Request body data for POST/PUT requests
        max_retries: Maximum number of retry attempts (default: 3)
        **kwargs: Additional arguments passed to requests.request

    Returns:
        Parsed JSON response
    """
    if not ADMIN_API_KEY:
        raise ValueError("ADMIN_API_KEY is required")
    if not GHOST_URL:
        raise ValueError("GHOST_URL is required")

    token = generate_token(ADMIN_API_KEY)
    url = GHOST_URL + endpoint

    headers = {
        "Authorization": f"Ghost {token}",
        "Accept-Version": "v5.0",
    }

    if data:
        headers["Content-Type"] = "application/json"

    # Merge with any additional headers
    if "headers" in kwargs:
        headers.update(kwargs.pop("headers"))

    # Retry logic with exponential backoff
    for attempt in range(max_retries + 1):
        try:
            response = requests.request(
                method=method, url=url, headers=headers, json=data, timeout=30, **kwargs
            )

            if response.ok:
                return response.json()
            else:
                raise Exception(
                    f"API returned status {response.status_code}: {response.text}"
                )

        except requests.exceptions.RequestException as e:
            if attempt == max_retries:
                raise Exception(f"Request failed after {max_retries + 1} attempts: {e}")

            wait_time = 2**attempt  # Exponential backoff: 1s, 2s, 4s
            logger.warning(
                f"Request failed (attempt {attempt + 1}/{max_retries + 1}), retrying in {wait_time}s: {e}"
            )
            time.sleep(wait_time)

    # This should never be reached, but satisfies type checker
    raise Exception("Unexpected error in request retry logic")


def fetch_member_attribution(member_id: str) -> Optional[Dict[str, Any]]:
    """
    Fetch attribution data for a single member using the read endpoint
    
    Note: This function uses make_ghost_request which includes exponential backoff retry logic.
    If the API call fails, it will retry up to 3 times with 1s, 2s, and 4s delays before giving up.

    Args:
        member_id: Ghost member ID

    Returns:
        Attribution dict or None if not available
    """
    try:
        endpoint = f"/ghost/api/admin/members/{member_id}/"
        response = make_ghost_request(endpoint)

        members = response.get("members", [])
        if members and len(members) > 0:
            member = members[0]
            return member.get("attribution")

        return None
    except Exception as e:
        logger.warning(f"Failed to fetch attribution for member {member_id}: {e}")
        return None


# ============================================
# DATABASE SETUP
# ============================================


def setup_database():
    """Create SQLite database and tables using schema.sql file"""
    # Read schema from file
    with open(SCHEMA_FILE, "r") as f:
        schema_sql = f.read()

    # Connect to database and execute schema
    conn = get_db_connection()

    # Use executescript to handle the entire schema at once
    # This properly handles multi-line statements and comments
    conn.executescript(schema_sql)

    conn.commit()
    conn.close()
    logger.info(f"Database '{DATABASE_FILE}' initialized successfully")


# ============================================
# DATA INSERTION FUNCTIONS
# ============================================


def insert_member(cursor: sqlite3.Cursor, member: Dict[str, Any], attribution: Optional[Dict[str, Any]] = None) -> None:
    """Insert or update a member record, restoring soft-deleted members if they reappear

    Args:
        cursor: Database cursor
        member: Member data from Ghost API
        attribution: Attribution data (optional). If None, attribution fields will be preserved or set to NULL for new members.
    """
    # Handle email_suppression as JSON string
    email_suppression = member.get("email_suppression")
    email_suppression_json = (
        json.dumps(email_suppression) if email_suppression else None
    )

    # Extract attribution fields if provided
    attribution_id = attribution.get("id") if attribution else None
    attribution_type = attribution.get("type") if attribution else None
    attribution_url = attribution.get("url") if attribution else None
    attribution_title = attribution.get("title") if attribution else None
    attribution_referrer_source = attribution.get("referrer_source") if attribution else None
    attribution_referrer_medium = attribution.get("referrer_medium") if attribution else None
    attribution_referrer_url = attribution.get("referrer_url") if attribution else None

    # Check if member exists and is soft deleted
    cursor.execute("SELECT deleted_at FROM members WHERE id = ?", (member.get("id"),))
    existing = cursor.fetchone()

    if existing and existing[0] is not None:
        # Member was soft deleted, restore them
        logger.info(f"Restoring previously deleted member: {member.get('email')}")
        # For restored members, only update attribution if it was provided
        if attribution is not None:
            cursor.execute(
                """
                UPDATE members SET
                    uuid = ?, email = ?, name = ?, note = ?, geolocation = ?, subscribed = ?,
                    created_at = ?, updated_at = ?, avatar_image = ?, comped = ?,
                    email_count = ?, email_opened_count = ?, email_open_rate = ?,
                    status = ?, last_seen_at = ?, unsubscribe_url = ?, email_suppression = ?,
                    attribution_id = ?, attribution_type = ?, attribution_url = ?, attribution_title = ?,
                    attribution_referrer_source = ?, attribution_referrer_medium = ?, attribution_referrer_url = ?,
                    deleted_at = NULL
                WHERE id = ?
                """,
                (
                    member.get("uuid"),
                    member.get("email"),
                    member.get("name"),
                    member.get("note"),
                    member.get("geolocation"),
                    member.get("subscribed"),
                    member.get("created_at"),
                    member.get("updated_at"),
                    member.get("avatar_image"),
                    member.get("comped"),
                    member.get("email_count"),
                    member.get("email_opened_count"),
                    member.get("email_open_rate"),
                    member.get("status"),
                    member.get("last_seen_at"),
                    member.get("unsubscribe_url"),
                    email_suppression_json,
                    attribution_id,
                    attribution_type,
                    attribution_url,
                    attribution_title,
                    attribution_referrer_source,
                    attribution_referrer_medium,
                    attribution_referrer_url,
                    member.get("id"),
                ),
            )
        else:
            # Don't update attribution fields if not provided
            cursor.execute(
                """
                UPDATE members SET
                    uuid = ?, email = ?, name = ?, note = ?, geolocation = ?, subscribed = ?,
                    created_at = ?, updated_at = ?, avatar_image = ?, comped = ?,
                    email_count = ?, email_opened_count = ?, email_open_rate = ?,
                    status = ?, last_seen_at = ?, unsubscribe_url = ?, email_suppression = ?,
                    deleted_at = NULL
                WHERE id = ?
                """,
                (
                    member.get("uuid"),
                    member.get("email"),
                    member.get("name"),
                    member.get("note"),
                    member.get("geolocation"),
                    member.get("subscribed"),
                    member.get("created_at"),
                    member.get("updated_at"),
                    member.get("avatar_image"),
                    member.get("comped"),
                    member.get("email_count"),
                    member.get("email_opened_count"),
                    member.get("email_open_rate"),
                    member.get("status"),
                    member.get("last_seen_at"),
                    member.get("unsubscribe_url"),
                    email_suppression_json,
                    member.get("id"),
                ),
            )
    else:
        # Normal insert or update
        # If attribution is provided, use it; otherwise preserve existing values
        if attribution is not None:
            cursor.execute(
                """
                INSERT OR REPLACE INTO members (
                    id, uuid, email, name, note, geolocation, subscribed,
                    created_at, updated_at, avatar_image, comped,
                    email_count, email_opened_count, email_open_rate,
                    status, last_seen_at, unsubscribe_url, email_suppression, deleted_at,
                    attribution_id, attribution_type, attribution_url, attribution_title,
                    attribution_referrer_source, attribution_referrer_medium, attribution_referrer_url
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    COALESCE((SELECT deleted_at FROM members WHERE id = ?), NULL),
                    ?, ?, ?, ?, ?, ?, ?
                )
                """,
                (
                    member.get("id"),
                    member.get("uuid"),
                    member.get("email"),
                    member.get("name"),
                    member.get("note"),
                    member.get("geolocation"),
                    member.get("subscribed"),
                    member.get("created_at"),
                    member.get("updated_at"),
                    member.get("avatar_image"),
                    member.get("comped"),
                    member.get("email_count"),
                    member.get("email_opened_count"),
                    member.get("email_open_rate"),
                    member.get("status"),
                    member.get("last_seen_at"),
                    member.get("unsubscribe_url"),
                    email_suppression_json,
                    member.get("id"),  # For COALESCE subquery
                    attribution_id,
                    attribution_type,
                    attribution_url,
                    attribution_title,
                    attribution_referrer_source,
                    attribution_referrer_medium,
                    attribution_referrer_url,
                ),
            )
        else:
            # Don't update attribution fields - preserve existing values
            cursor.execute(
                """
                INSERT OR REPLACE INTO members (
                    id, uuid, email, name, note, geolocation, subscribed,
                    created_at, updated_at, avatar_image, comped,
                    email_count, email_opened_count, email_open_rate,
                    status, last_seen_at, unsubscribe_url, email_suppression, deleted_at,
                    attribution_id, attribution_type, attribution_url, attribution_title,
                    attribution_referrer_source, attribution_referrer_medium, attribution_referrer_url
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    COALESCE((SELECT deleted_at FROM members WHERE id = ?), NULL),
                    COALESCE((SELECT attribution_id FROM members WHERE id = ?), NULL),
                    COALESCE((SELECT attribution_type FROM members WHERE id = ?), NULL),
                    COALESCE((SELECT attribution_url FROM members WHERE id = ?), NULL),
                    COALESCE((SELECT attribution_title FROM members WHERE id = ?), NULL),
                    COALESCE((SELECT attribution_referrer_source FROM members WHERE id = ?), NULL),
                    COALESCE((SELECT attribution_referrer_medium FROM members WHERE id = ?), NULL),
                    COALESCE((SELECT attribution_referrer_url FROM members WHERE id = ?), NULL)
                )
                """,
                (
                    member.get("id"),
                    member.get("uuid"),
                    member.get("email"),
                    member.get("name"),
                    member.get("note"),
                    member.get("geolocation"),
                    member.get("subscribed"),
                    member.get("created_at"),
                    member.get("updated_at"),
                    member.get("avatar_image"),
                    member.get("comped"),
                    member.get("email_count"),
                    member.get("email_opened_count"),
                    member.get("email_open_rate"),
                    member.get("status"),
                    member.get("last_seen_at"),
                    member.get("unsubscribe_url"),
                    email_suppression_json,
                    member.get("id"),  # For COALESCE deleted_at subquery
                    member.get("id"),  # For COALESCE attribution_id subquery
                    member.get("id"),  # For COALESCE attribution_type subquery
                    member.get("id"),  # For COALESCE attribution_url subquery
                    member.get("id"),  # For COALESCE attribution_title subquery
                    member.get("id"),  # For COALESCE attribution_referrer_source subquery
                    member.get("id"),  # For COALESCE attribution_referrer_medium subquery
                    member.get("id"),  # For COALESCE attribution_referrer_url subquery
                ),
            )


def insert_labels(
    cursor: sqlite3.Cursor, member_id: str, labels: List[Dict[str, Any]]
) -> None:
    """Insert labels and member-label relationships"""
    for label in labels:
        # Insert label
        cursor.execute(
            """
            INSERT OR REPLACE INTO labels (
                id, name, slug, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?)
        """,
            (
                label.get("id"),
                label.get("name"),
                label.get("slug"),
                label.get("created_at"),
                label.get("updated_at"),
            ),
        )

        # Insert member-label relationship
        cursor.execute(
            """
            INSERT OR REPLACE INTO member_labels (member_id, label_id)
            VALUES (?, ?)
        """,
            (member_id, label.get("id")),
        )


def insert_newsletters(
    cursor: sqlite3.Cursor, member_id: str, newsletters: List[Dict[str, Any]]
) -> None:
    """Insert newsletters and member-newsletter relationships"""
    for newsletter in newsletters:
        # Insert newsletter
        cursor.execute(
            """
            INSERT OR REPLACE INTO newsletters (
                id, name, description, status
            ) VALUES (?, ?, ?, ?)
        """,
            (
                newsletter.get("id"),
                newsletter.get("name"),
                newsletter.get("description"),
                newsletter.get("status"),
            ),
        )

        # Insert member-newsletter relationship
        cursor.execute(
            """
            INSERT OR REPLACE INTO member_newsletters (member_id, newsletter_id)
            VALUES (?, ?)
        """,
            (member_id, newsletter.get("id")),
        )


def insert_subscriptions(
    cursor: sqlite3.Cursor, member_id: str, subscriptions: List[Dict[str, Any]]
) -> None:
    """Insert subscriptions for a member"""
    for subscription in subscriptions:
        # Store subscription details as JSON strings to avoid complex tables
        customer = subscription.get("customer")
        customer_json = json.dumps(customer) if customer else None

        price = subscription.get("price")
        price_json = json.dumps(price) if price else None

        tier = subscription.get("tier")
        if tier:
            # Extract simple tier info instead of storing full JSON
            tier_id = tier.get("id")
            tier_name = tier.get("name")
        else:
            tier_id = None
            tier_name = None

        offer = subscription.get("offer")
        offer_json = json.dumps(offer) if offer else None

        cursor.execute(
            """
            INSERT OR REPLACE INTO subscriptions (
                id, member_id, customer, status, start_date,
                default_payment_card_last4, cancel_at_period_end,
                cancellation_reason, current_period_end, trial_start_at,
                trial_end_at, price, tier_id, tier_name, offer
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                subscription.get("id"),
                member_id,
                customer_json,
                subscription.get("status"),
                subscription.get("start_date"),
                subscription.get("default_payment_card_last4"),
                subscription.get("cancel_at_period_end"),
                subscription.get("cancellation_reason"),
                subscription.get("current_period_end"),
                subscription.get("trial_start_at"),
                subscription.get("trial_end_at"),
                price_json,
                tier_id,
                tier_name,
                offer_json,
            ),
        )


def insert_tiers(
    cursor: sqlite3.Cursor, member_id: str, tiers: List[Dict[str, Any]]
) -> None:
    """Insert tiers and member-tier relationships"""
    for tier in tiers:
        # Insert tier
        cursor.execute(
            """
            INSERT OR REPLACE INTO tiers (
                id, name, slug, active, trial_days, description,
                type, currency, monthly_price, yearly_price,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                tier.get("id"),
                tier.get("name"),
                tier.get("slug"),
                tier.get("active"),
                tier.get("trial_days"),
                tier.get("description"),
                tier.get("type"),
                tier.get("currency"),
                tier.get("monthly_price"),
                tier.get("yearly_price"),
                tier.get("created_at"),
                tier.get("updated_at"),
            ),
        )

        # Insert member-tier relationship
        cursor.execute(
            """
            INSERT OR REPLACE INTO member_tiers (member_id, tier_id)
            VALUES (?, ?)
        """,
            (member_id, tier.get("id")),
        )


def insert_email_recipients(
    cursor: sqlite3.Cursor, member_id: str, email_recipients: List[Dict[str, Any]]
) -> None:
    """Insert email recipients and related emails"""
    for recipient in email_recipients:
        # Insert email recipient
        cursor.execute(
            """
            INSERT OR REPLACE INTO email_recipients (
                id, email_id, member_id, batch_id, processed_at,
                delivered_at, opened_at, failed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                recipient.get("id"),
                recipient.get("email_id"),
                member_id,
                recipient.get("batch_id"),
                recipient.get("processed_at"),
                recipient.get("delivered_at"),
                recipient.get("opened_at"),
                recipient.get("failed_at"),
            ),
        )

        # Insert related email if present
        email_data = recipient.get("email")
        if email_data:
            cursor.execute(
                """
                INSERT OR REPLACE INTO emails (
                    id, post_id, uuid, status, recipient_filter,
                    error, error_data, email_count, delivered_count, opened_count,
                    failed_count, subject, from_address, reply_to,
                    source, source_type, track_opens, track_clicks,
                    feedback_enabled, submitted_at, newsletter_id,
                    created_at, updated_at, csd_email_count
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    email_data.get("id"),
                    email_data.get("post_id"),
                    email_data.get("uuid"),
                    email_data.get("status"),
                    email_data.get("recipient_filter"),
                    email_data.get("error"),
                    email_data.get("error_data"),
                    email_data.get("email_count"),
                    email_data.get("delivered_count"),
                    email_data.get("opened_count"),
                    email_data.get("failed_count"),
                    email_data.get("subject"),
                    email_data.get("from"),
                    email_data.get("reply_to"),
                    email_data.get("source"),
                    email_data.get("source_type"),
                    email_data.get("track_opens"),
                    email_data.get("track_clicks"),
                    email_data.get("feedback_enabled"),
                    email_data.get("submitted_at"),
                    email_data.get("newsletter_id"),
                    email_data.get("created_at"),
                    email_data.get("updated_at"),
                    email_data.get("csd_email_count"),
                ),
            )


# ============================================
# DATA FETCHING AND PROCESSING
# ============================================


def get_last_sync_time() -> Optional[str]:
    """Get the timestamp of the last successful sync"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT completed_at
            FROM sync_runs
            WHERE status = 'completed'
            ORDER BY completed_at DESC
            LIMIT 1
        """)

        result = cursor.fetchone()
        conn.close()

        if result and result[0]:
            return result[0]
        return None
    except sqlite3.OperationalError:
        # Table doesn't exist yet (first run)
        return None


def soft_delete_missing_members(cursor, fetched_member_ids: set) -> int:
    """
    Soft delete members that are in the database but not in the fetched member IDs

    Args:
        cursor: Database cursor
        fetched_member_ids: Set of member IDs fetched from Ghost API

    Returns:
        Number of members soft deleted
    """
    if not fetched_member_ids:
        return 0

    # Get all active member IDs from database (not already soft deleted)
    cursor.execute(
        """
        SELECT id FROM members 
        WHERE deleted_at IS NULL
        AND id NOT IN ({})
    """.format(",".join(["?" for _ in fetched_member_ids])),
        list(fetched_member_ids),
    )

    missing_ids = [row[0] for row in cursor.fetchall()]

    if not missing_ids:
        return 0

    # Soft delete the missing members
    deleted_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    placeholders = ",".join(["?" for _ in missing_ids])

    cursor.execute(
        f"""
        UPDATE members 
        SET deleted_at = ?, updated_at = ?
        WHERE id IN ({placeholders})
    """,
        [deleted_at, deleted_at] + missing_ids,
    )

    return cursor.rowcount


def fetch_and_save_members(since: Optional[str] = None, fetch_attribution: bool = False) -> int:
    """
    Fetch members from Ghost API using pagination and save them to database as they're fetched

    Args:
        since: ISO timestamp to fetch only members updated since this time
        fetch_attribution: If True, fetch attribution data for each member (slow)

    Returns:
        Total number of members saved to database
    """
    total_saved = 0
    page = 1
    fetched_member_ids = set()

    if since:
        logger.info(f"Fetching and saving members updated since {since}...")
    else:
        logger.info("Fetching and saving all members from Ghost API...")

    # Keep database connection open throughout the process
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Get total count on first page
        total_members = None
        while True:
            # Build endpoint with optional filter
            endpoint = f"/ghost/api/admin/members/?limit={MEMBERS_PAGE_SIZE}&include=email_recipients,subscriptions,newsletters,tiers&page={page}"

            if since:
                # URL encode the filter parameter
                # Format: filter=updated_at:>'2024-01-01T00:00:00.000Z'
                endpoint += f"&filter=updated_at:>'{since}'"

            try:
                response = make_ghost_request(endpoint)
                members = response.get("members", [])

                if not members:
                    break

                # Get total count from first page response
                if total_members is None:
                    meta = response.get("meta", {})
                    pagination = meta.get("pagination", {})
                    total_members = pagination.get("total", 0)
                    if total_members > 0:
                        logger.info(f"Found {total_members} total members to fetch")

                # Save this page of members to database
                page_saved = 0
                for member in members:
                    # Track member IDs for deletion detection
                    fetched_member_ids.add(member["id"])

                    # Fetch attribution data if requested and not already fetched
                    attribution = None
                    if fetch_attribution:
                        # Check if attribution has already been fetched for this member
                        cursor.execute(
                            "SELECT attribution_id FROM members WHERE id = ?",
                            (member["id"],)
                        )
                        existing = cursor.fetchone()

                        # Only fetch if attribution_id is NULL (not yet fetched)
                        if existing is None or existing[0] is None:
                            attribution = fetch_member_attribution(member["id"])
                            if attribution:
                                logger.debug(f"Fetched attribution for {member.get('email')}")
                        
                        # Report progress every 50 members when fetching attribution
                        if total_saved % 50 == 0 and total_saved > 0:
                            attribution_count = cursor.execute(
                                "SELECT COUNT(*) FROM members WHERE attribution_id IS NOT NULL AND attribution_id != ''"
                            ).fetchone()[0]
                            logger.info(f"Progress: {total_saved} members processed, {attribution_count} with attribution")

                    # Insert member with attribution data
                    insert_member(cursor, member, attribution)

                    # Insert labels
                    labels = member.get("labels", [])
                    if labels:
                        insert_labels(cursor, member["id"], labels)

                    # Insert newsletters
                    newsletters = member.get("newsletters", [])
                    if newsletters:
                        insert_newsletters(cursor, member["id"], newsletters)

                    # Insert subscriptions
                    subscriptions = member.get("subscriptions", [])
                    if subscriptions:
                        insert_subscriptions(cursor, member["id"], subscriptions)

                    # Insert tiers
                    tiers = member.get("tiers", [])
                    if tiers:
                        insert_tiers(cursor, member["id"], tiers)

                    # Insert email recipients
                    email_recipients = member.get("email_recipients", [])
                    if email_recipients:
                        insert_email_recipients(cursor, member["id"], email_recipients)

                    page_saved += 1

                # Commit after each page of members is processed
                # This provides a good balance between memory usage and performance
                # Page size is controlled by MEMBERS_PAGE_SIZE (100 members - max allowed by Ghost API)
                conn.commit()
                total_saved += page_saved

                # Show progress vs total
                if total_members:
                    logger.info(
                        f"Progress: {total_saved}/{total_members} members ({(total_saved / total_members) * 100:.1f}%)"
                    )
                else:
                    logger.info(f"Progress: {total_saved} members saved")

                # Check if there are more pages
                meta = response.get("meta", {})
                pagination = meta.get("pagination", {})

                if pagination.get("page", 1) >= pagination.get("pages", 1):
                    break

                page += 1

            except Exception as e:
                logger.error(f"Error fetching page {page}: {e}")
                raise  # Re-raise to be handled by caller

        # Soft delete members that are no longer in Ghost API
        if not since:  # Only do deletion detection on full syncs
            deleted_count = soft_delete_missing_members(cursor, fetched_member_ids)
            if deleted_count > 0:
                logger.info(
                    f"Soft deleted {deleted_count} members no longer in Ghost API"
                )
                conn.commit()

    finally:
        conn.close()

    logger.info(f"Total members saved: {total_saved}")
    return total_saved


def save_members_to_database(members: List[Dict[str, Any]]) -> int:
    """Save members data to SQLite database (legacy function for compatibility)"""
    conn = get_db_connection()
    cursor = conn.cursor()

    logger.info(f"Saving {len(members)} members to database...")

    saved_count = 0
    for i, member in enumerate(members):
        try:
            # Insert member
            insert_member(cursor, member)

            # Insert labels
            labels = member.get("labels", [])
            if labels:
                insert_labels(cursor, member["id"], labels)

            # Insert newsletters
            newsletters = member.get("newsletters", [])
            if newsletters:
                insert_newsletters(cursor, member["id"], newsletters)

            # Insert subscriptions
            subscriptions = member.get("subscriptions", [])
            if subscriptions:
                insert_subscriptions(cursor, member["id"], subscriptions)

            # Insert tiers
            tiers = member.get("tiers", [])
            if tiers:
                insert_tiers(cursor, member["id"], tiers)

            # Insert email recipients
            email_recipients = member.get("email_recipients", [])
            if email_recipients:
                insert_email_recipients(cursor, member["id"], email_recipients)

            saved_count += 1

            if (i + 1) % 100 == 0:
                logger.info(f"Processed {i + 1}/{len(members)} members")
                conn.commit()  # Commit in batches

        except Exception as e:
            logger.error(f"Error processing member {member.get('id', 'unknown')}: {e}")
            # Continue processing other members instead of failing completely

    conn.commit()
    conn.close()
    logger.info(f"Successfully saved {saved_count}/{len(members)} members to database")
    return saved_count


def backfill_attribution() -> int:
    """
    Backfill attribution data for all members in database with NULL attribution_id

    Returns:
        Number of members with attribution fetched
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Get all members with NULL attribution_id
        cursor.execute("""
            SELECT id, email
            FROM members
            WHERE attribution_id IS NULL
            AND deleted_at IS NULL
            ORDER BY created_at DESC
        """)

        members_to_backfill = cursor.fetchall()
        total_members = len(members_to_backfill)

        if total_members == 0:
            logger.info("No members found with missing attribution data")
            return 0

        logger.info(f"Found {total_members} members with missing attribution data")
        logger.info("Starting attribution backfill (this will be slow)...")

        backfilled_count = 0
        failed_count = 0

        for i, (member_id, email) in enumerate(members_to_backfill, 1):
            try:
                attribution = fetch_member_attribution(member_id)

                if attribution:
                    # Update only attribution fields
                    cursor.execute("""
                        UPDATE members
                        SET attribution_id = ?,
                            attribution_type = ?,
                            attribution_url = ?,
                            attribution_title = ?,
                            attribution_referrer_source = ?,
                            attribution_referrer_medium = ?,
                            attribution_referrer_url = ?
                        WHERE id = ?
                    """, (
                        attribution.get("id"),
                        attribution.get("type"),
                        attribution.get("url"),
                        attribution.get("title"),
                        attribution.get("referrer_source"),
                        attribution.get("referrer_medium"),
                        attribution.get("referrer_url"),
                        member_id,
                    ))
                    backfilled_count += 1
                else:
                    # Set attribution_id to empty string to mark as "checked but no attribution"
                    cursor.execute("""
                        UPDATE members
                        SET attribution_id = ''
                        WHERE id = ?
                    """, (member_id,))

                # Commit every 10 members to balance memory usage and performance
                # This ensures progress isn't lost if the process crashes, but avoids
                # excessive disk I/O from committing on every single record
                if i % 10 == 0:
                    conn.commit()
                    logger.info(f"Progress: {i}/{total_members} members processed ({backfilled_count} with attribution)")

            except Exception as e:
                logger.warning(f"Failed to fetch attribution for {email}: {e}")
                failed_count += 1
                continue

        # Final commit
        conn.commit()

        logger.info(f"Backfill complete: {backfilled_count} members with attribution, {total_members - backfilled_count - failed_count} without attribution, {failed_count} failed")
        return backfilled_count

    finally:
        conn.close()


# ============================================
# MAIN FUNCTION
# ============================================


def main():
    """Main execution function"""
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description="Sync Ghost members to SQLite database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Full sync (fetch all members)
  python members_to_sqlite.py

  # Incremental sync (fetch only updated members since last run)
  python members_to_sqlite.py --incremental

  # Sync members updated since specific date
  python members_to_sqlite.py --since 2024-01-01T00:00:00.000Z

  # Full sync with attribution data (slow - requires API call per member)
  python members_to_sqlite.py --attribution

  # Fill in missing attribution data for existing members
  python members_to_sqlite.py --attribution --incremental

  # Backfill attribution for ALL members in database with missing attribution
  python members_to_sqlite.py --backfill-attribution
        """,
    )
    parser.add_argument(
        "--incremental",
        action="store_true",
        help="Only sync members updated since last successful sync",
    )
    parser.add_argument(
        "--since",
        type=str,
        help="Only sync members updated since this ISO timestamp (e.g., 2024-01-01T00:00:00.000Z)",
    )
    parser.add_argument(
        "--attribution",
        action="store_true",
        help="Fetch attribution data for each member (requires individual API call per member - slow)",
    )
    parser.add_argument(
        "--backfill-attribution",
        action="store_true",
        help="Backfill attribution for all members in database with NULL attribution_id (slow)",
    )

    args = parser.parse_args()

    if not GHOST_URL or not ADMIN_API_KEY:
        logger.error(
            "Missing configuration: GHOST_URL and ADMIN_API_KEY must be set in .env file"
        )
        sys.exit(1)

    # Setup database first
    try:
        setup_database()
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        sys.exit(1)

    # Handle backfill-attribution mode (separate from normal sync)
    if args.backfill_attribution:
        logger.info("Starting attribution backfill mode...")
        try:
            backfilled_count = backfill_attribution()
            logger.info(f"✅ Attribution backfill completed! {backfilled_count} members updated")
            sys.exit(0)
        except Exception as e:
            logger.error(f"Attribution backfill failed: {e}", exc_info=True)
            sys.exit(1)

    # Determine sync starting point
    since_timestamp = None
    if args.incremental:
        since_timestamp = get_last_sync_time()
        if since_timestamp:
            logger.info(
                f"Incremental sync mode: fetching updates since {since_timestamp}"
            )
        else:
            logger.info("No previous sync found, performing full sync")
    elif args.since:
        since_timestamp = args.since
        logger.info(f"Syncing members updated since {since_timestamp}")

    # Track sync run
    conn = get_db_connection()
    cursor = conn.cursor()

    # Start tracking this sync run
    started_at = datetime.now(timezone.utc).isoformat()
    cursor.execute(
        "INSERT INTO sync_runs (started_at, status) VALUES (?, ?)",
        (started_at, "running"),
    )
    conn.commit()
    sync_run_id = cursor.lastrowid

    try:
        # Fetch and save members (streaming approach)
        logger.info("Starting sync process...")
        if args.attribution:
            logger.info("Attribution fetching enabled (this will be slow)")
        saved_count = fetch_and_save_members(since=since_timestamp, fetch_attribution=args.attribution)

        if saved_count == 0:
            logger.warning("No members found to process")
            cursor.execute(
                "UPDATE sync_runs SET completed_at = ?, status = ?, members_fetched = 0 WHERE id = ?",
                (datetime.now(timezone.utc).isoformat(), "completed", sync_run_id),
            )
            conn.commit()
            conn.close()
            return

        # Update sync run as completed
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE sync_runs SET completed_at = ?, status = ?, members_fetched = ?, members_saved = ? WHERE id = ?",
            (
                datetime.now(timezone.utc).isoformat(),
                "completed",
                saved_count,
                saved_count,
                sync_run_id,
            ),
        )
        conn.commit()
        conn.close()

        # Checkpoint WAL to clean up .db-wal file
        try:
            conn = get_db_connection()
            conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            conn.close()
        except sqlite3.OperationalError as e:
            logger.warning(f"Could not checkpoint WAL (database may be in use): {e}")

        logger.info(
            f"✅ Sync completed successfully! {saved_count} members saved to '{DATABASE_FILE}'"
        )

    except Exception as e:
        logger.error(f"Sync failed: {e}", exc_info=True)

        # Update sync run as failed
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE sync_runs SET completed_at = ?, status = ?, error_message = ? WHERE id = ?",
            (datetime.now(timezone.utc).isoformat(), "failed", str(e), sync_run_id),
        )
        conn.commit()
        conn.close()

        sys.exit(1)


if __name__ == "__main__":
    main()
