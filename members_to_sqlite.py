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
import logging
import sys
import argparse
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
import os
from dotenv import load_dotenv
from peewee import (
    SqliteDatabase,
    Model,
    CharField,
    TextField,
    BooleanField,
    IntegerField,
    ForeignKeyField,
    ManyToManyField,
    DatabaseError,
    fn,
    AutoField,
)

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


GHOST_URL = os.getenv("GHOST_URL")  # Your Ghost URL (no trailing slash)
ADMIN_API_KEY = os.getenv("ADMIN_API_KEY")  # Your Admin API Key (format: id:secret)
MEMBERS_PAGE_SIZE = 100  # Number of members to fetch per page
DATABASE_FILE = os.getenv(
    "DATABASE_FILE", "ghost_members.db"
)  # SQLite database file name
SCHEMA_FILE = "schema.sql"  # Database schema file name

# Initialize peewee database
database = SqliteDatabase(DATABASE_FILE)


# ============================================
# PEEWEE MODELS
# ============================================


class BaseModel(Model):
    """Base model class that uses our database"""

    class Meta:
        database = database


class Member(BaseModel):
    """Ghost member model"""

    id = CharField(primary_key=True)
    uuid = CharField(unique=True)
    email = CharField(unique=True)
    name = TextField(null=True)
    note = TextField(null=True)
    geolocation = TextField(null=True)
    subscribed = BooleanField(default=False)
    created_at = TextField()
    updated_at = TextField()
    avatar_image = TextField(null=True)
    comped = BooleanField(default=False)
    email_count = IntegerField(default=0)
    email_opened_count = IntegerField(default=0)
    email_open_rate = IntegerField(default=0)
    status = TextField(null=True)
    last_seen_at = TextField(null=True)
    unsubscribe_url = TextField(null=True)
    email_suppression = TextField(null=True)
    deleted_at = TextField(null=True)
    attribution_id = TextField(null=True)
    attribution_type = TextField(null=True)
    attribution_url = TextField(null=True)
    attribution_title = TextField(null=True)
    attribution_referrer_source = TextField(null=True)
    attribution_referrer_medium = TextField(null=True)
    attribution_referrer_url = TextField(null=True)

    class Meta:
        table_name = "members"
        indexes = (
            (("email",), False),
            (("created_at",), False),
            (("subscribed",), False),
            (("email_open_rate",), False),
            (("status",), False),
            (("last_seen_at",), False),
            (("deleted_at",), False),
        )


class Label(BaseModel):
    """Member label model"""

    id = CharField(primary_key=True)
    name = TextField()
    slug = CharField(unique=True)
    created_at = TextField()
    updated_at = TextField()

    class Meta:
        table_name = "labels"
        indexes = ((("name",), False),)


class Newsletter(BaseModel):
    """Newsletter model"""

    id = CharField(primary_key=True)
    name = TextField()
    description = TextField(null=True)
    status = TextField()

    class Meta:
        table_name = "newsletters"
        indexes = (
            (("name",), False),
            (("status",), False),
        )


class Tier(BaseModel):
    """Tier model"""

    id = CharField(primary_key=True)
    name = TextField()
    slug = CharField(unique=True)
    active = BooleanField(default=True)
    trial_days = IntegerField(default=0)
    description = TextField(null=True)
    type = TextField(null=True)
    currency = TextField(null=True)
    monthly_price = IntegerField(default=0)
    yearly_price = IntegerField(default=0)
    created_at = TextField()
    updated_at = TextField()

    class Meta:
        table_name = "tiers"
        indexes = (
            (("name",), False),
            (("active",), False),
        )


class Subscription(BaseModel):
    """Subscription model"""

    id = CharField(primary_key=True)
    member = ForeignKeyField(Member, backref="subscriptions", on_delete="CASCADE")
    customer = TextField(null=True)
    status = TextField()
    start_date = TextField(null=True)
    default_payment_card_last4 = TextField(null=True)
    cancel_at_period_end = BooleanField(default=False)
    cancellation_reason = TextField(null=True)
    current_period_end = TextField(null=True)
    trial_start_at = TextField(null=True)
    trial_end_at = TextField(null=True)
    price = TextField(null=True)
    tier_id = TextField(null=True)
    tier_name = TextField(null=True)
    offer = TextField(null=True)

    class Meta:
        table_name = "subscriptions"
        indexes = (
            (("member",), False),
            (("status",), False),
            (("current_period_end",), False),
        )


class Email(BaseModel):
    """Email model"""

    id = CharField(primary_key=True)
    post_id = TextField(null=True)
    uuid = CharField(unique=True)
    status = TextField()
    recipient_filter = TextField(null=True)
    error = TextField(null=True)
    error_data = TextField(null=True)
    email_count = IntegerField(default=0)
    delivered_count = IntegerField(default=0)
    opened_count = IntegerField(default=0)
    failed_count = IntegerField(default=0)
    subject = TextField()
    from_address = TextField(null=True)
    reply_to = TextField(null=True)
    source = TextField(null=True)
    source_type = TextField(null=True)
    track_opens = BooleanField(default=True)
    track_clicks = BooleanField(default=True)
    feedback_enabled = BooleanField(default=False)
    submitted_at = TextField(null=True)
    newsletter_id = TextField(null=True)
    created_at = TextField()
    updated_at = TextField()
    csd_email_count = IntegerField(null=True)

    class Meta:
        table_name = "emails"
        indexes = (
            (("created_at",), False),
            (("status",), False),
            (("subject",), False),
            (("newsletter_id",), False),
        )


class EmailRecipient(BaseModel):
    """Email recipient model"""

    id = CharField(primary_key=True)
    email = ForeignKeyField(Email, backref="recipients", on_delete="CASCADE")
    member = ForeignKeyField(Member, backref="email_recipients", on_delete="CASCADE")
    batch_id = TextField(null=True)
    processed_at = TextField(null=True)
    delivered_at = TextField(null=True)
    opened_at = TextField(null=True)
    failed_at = TextField(null=True)

    class Meta:
        table_name = "email_recipients"
        indexes = (
            (("member",), False),
            (("email",), False),
        )


class SyncRun(BaseModel):
    """Sync run tracking model"""

    id = AutoField()
    started_at = TextField()
    completed_at = TextField(null=True)
    status = TextField()
    members_fetched = IntegerField(default=0)
    members_saved = IntegerField(default=0)
    error_message = TextField(null=True)

    class Meta:
        table_name = "sync_runs"


# Define explicit through models for many-to-many relationships
class MemberLabel(BaseModel):
    member = ForeignKeyField(Member, backref="member_labels")
    label = ForeignKeyField(Label, backref="label_members")

    class Meta:
        table_name = "member_labels"
        indexes = (
            (("member", "label"), True),  # Unique constraint on member-label pair
        )


class MemberNewsletter(BaseModel):
    member = ForeignKeyField(Member, backref="member_newsletters")
    newsletter = ForeignKeyField(Newsletter, backref="newsletter_members")

    class Meta:
        table_name = "member_newsletters"
        indexes = (
            (
                ("member", "newsletter"),
                True,
            ),  # Unique constraint on member-newsletter pair
        )


class MemberTier(BaseModel):
    member = ForeignKeyField(Member, backref="member_tiers")
    tier = ForeignKeyField(Tier, backref="tier_members")

    class Meta:
        table_name = "member_tiers"
        indexes = (
            (("member", "tier"), True),  # Unique constraint on member-tier pair
        )


def setup_database_pragmas():
    """Set up performance pragmas for the database"""
    database.execute_sql("PRAGMA journal_mode = WAL")
    database.execute_sql("PRAGMA synchronous = NORMAL")
    database.execute_sql("PRAGMA cache_size = 10000")
    database.execute_sql("PRAGMA temp_store = MEMORY")


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
    """Create SQLite database and tables using peewee models"""
    models = [Member, Label, Newsletter, Tier, Subscription, Email,
              EmailRecipient, SyncRun, MemberLabel, MemberNewsletter, MemberTier]

    database.bind(models)
    database.connect()
    setup_database_pragmas()
    database.create_tables(models)
    database.close()
    logger.info(f"Database '{DATABASE_FILE}' initialized successfully")


# ============================================
# DATA INSERTION FUNCTIONS
# ============================================


def insert_member(
    member: Dict[str, Any], attribution: Optional[Dict[str, Any]] = None
) -> None:
    """Insert or update a member record, restoring soft-deleted members if they reappear"""
    email_suppression_json = (
        json.dumps(member["email_suppression"])
        if member.get("email_suppression")
        else None
    )

    existing_member = Member.get_or_none(Member.id == member["id"])

    # Base member data
    member_data = {
        "id": member["id"],
        "uuid": member["uuid"],
        "email": member["email"],
        "name": member.get("name"),
        "note": member.get("note"),
        "geolocation": member.get("geolocation"),
        "subscribed": member.get("subscribed", False),
        "created_at": member["created_at"],
        "updated_at": member["updated_at"],
        "avatar_image": member.get("avatar_image"),
        "comped": member.get("comped", False),
        "email_count": member.get("email_count", 0),
        "email_opened_count": member.get("email_opened_count", 0),
        "email_open_rate": member.get("email_open_rate", 0),
        "status": member.get("status"),
        "last_seen_at": member.get("last_seen_at"),
        "unsubscribe_url": member.get("unsubscribe_url"),
        "email_suppression": email_suppression_json,
    }

    # Handle attribution
    attribution_fields = ["id", "type", "url", "title", "referrer_source", "referrer_medium", "referrer_url"]
    if attribution:
        member_data.update({f"attribution_{k}": attribution.get(k) for k in attribution_fields})
    elif existing_member:
        # Preserve existing attribution
        member_data.update({f"attribution_{k}": getattr(existing_member, f"attribution_{k}") for k in attribution_fields})

    # Restore soft-deleted members
    if existing_member and existing_member.deleted_at:
        logger.info(f"Restoring previously deleted member: {member['email']}")
        member_data["deleted_at"] = None
    elif existing_member:
        member_data["deleted_at"] = existing_member.deleted_at

    Member.replace(member_data).execute()


def _insert_many_to_many(member_id: str, items: List[Dict[str, Any]],
                         model_class, relationship_class, fields: List[str]) -> None:
    """Generic helper for inserting many-to-many relationships"""
    member = Member.get_by_id(member_id)
    for item_data in items:
        data = {field: item_data.get(field) for field in fields}
        model_class.replace(**data).execute()
        item = model_class.get_by_id(item_data["id"])
        relationship_class.get_or_create(member=member, **{model_class.__name__.lower(): item})


def insert_labels(member_id: str, labels: List[Dict[str, Any]]) -> None:
    """Insert labels and member-label relationships"""
    _insert_many_to_many(member_id, labels, Label, MemberLabel,
                         ["id", "name", "slug", "created_at", "updated_at"])


def insert_newsletters(member_id: str, newsletters: List[Dict[str, Any]]) -> None:
    """Insert newsletters and member-newsletter relationships"""
    _insert_many_to_many(member_id, newsletters, Newsletter, MemberNewsletter,
                         ["id", "name", "description", "status"])


def insert_subscriptions(member_id: str, subscriptions: List[Dict[str, Any]]) -> None:
    """Insert subscriptions for a member"""
    for sub in subscriptions:
        tier = sub.get("tier", {})
        Subscription.replace(
            id=sub["id"],
            member_id=member_id,
            customer=json.dumps(sub["customer"]) if sub.get("customer") else None,
            status=sub["status"],
            start_date=sub.get("start_date"),
            default_payment_card_last4=sub.get("default_payment_card_last4"),
            cancel_at_period_end=sub.get("cancel_at_period_end", False),
            cancellation_reason=sub.get("cancellation_reason"),
            current_period_end=sub.get("current_period_end"),
            trial_start_at=sub.get("trial_start_at"),
            trial_end_at=sub.get("trial_end_at"),
            price=json.dumps(sub["price"]) if sub.get("price") else None,
            tier_id=tier.get("id"),
            tier_name=tier.get("name"),
            offer=json.dumps(sub["offer"]) if sub.get("offer") else None,
        ).execute()


def insert_tiers(member_id: str, tiers: List[Dict[str, Any]]) -> None:
    """Insert tiers and member-tier relationships"""
    _insert_many_to_many(member_id, tiers, Tier, MemberTier,
                         ["id", "name", "slug", "active", "trial_days", "description",
                          "type", "currency", "monthly_price", "yearly_price",
                          "created_at", "updated_at"])


def insert_email_recipients(
    member_id: str, email_recipients: List[Dict[str, Any]]
) -> None:
    """Insert email recipients and related emails"""
    for recipient in email_recipients:
        EmailRecipient.replace(
            id=recipient["id"],
            email_id=recipient["email_id"],
            member_id=member_id,
            batch_id=recipient.get("batch_id"),
            processed_at=recipient.get("processed_at"),
            delivered_at=recipient.get("delivered_at"),
            opened_at=recipient.get("opened_at"),
            failed_at=recipient.get("failed_at"),
        ).execute()

        if email_data := recipient.get("email"):
            Email.replace(
                id=email_data["id"],
                post_id=email_data.get("post_id"),
                uuid=email_data["uuid"],
                status=email_data["status"],
                recipient_filter=email_data.get("recipient_filter"),
                error=email_data.get("error"),
                error_data=email_data.get("error_data"),
                email_count=email_data.get("email_count", 0),
                delivered_count=email_data.get("delivered_count", 0),
                opened_count=email_data.get("opened_count", 0),
                failed_count=email_data.get("failed_count", 0),
                subject=email_data["subject"],
                from_address=email_data.get("from"),
                reply_to=email_data.get("reply_to"),
                source=email_data.get("source"),
                source_type=email_data.get("source_type"),
                track_opens=email_data.get("track_opens", True),
                track_clicks=email_data.get("track_clicks", True),
                feedback_enabled=email_data.get("feedback_enabled", False),
                submitted_at=email_data.get("submitted_at"),
                newsletter_id=email_data.get("newsletter_id"),
                created_at=email_data["created_at"],
                updated_at=email_data["updated_at"],
                csd_email_count=email_data.get("csd_email_count"),
            ).execute()


# ============================================
# DATA FETCHING AND PROCESSING
# ============================================


def process_member_relationships(member: Dict[str, Any]) -> None:
    """Process and insert all relationships for a member"""
    member_id = member["id"]

    if labels := member.get("labels"):
        insert_labels(member_id, labels)

    if newsletters := member.get("newsletters"):
        insert_newsletters(member_id, newsletters)

    if subscriptions := member.get("subscriptions"):
        insert_subscriptions(member_id, subscriptions)

    if tiers := member.get("tiers"):
        insert_tiers(member_id, tiers)

    if email_recipients := member.get("email_recipients"):
        insert_email_recipients(member_id, email_recipients)


def get_last_sync_time() -> Optional[str]:
    """Get the timestamp of the last successful sync"""
    try:
        sync_run = (
            SyncRun.select(SyncRun.completed_at)
            .where(SyncRun.status == "completed")
            .order_by(SyncRun.completed_at.desc())
            .first()
        )
        return sync_run.completed_at if sync_run else None
    except (DatabaseError, Exception):
        # Table doesn't exist yet or other error (first run)
        return None


def soft_delete_missing_members(fetched_member_ids: set) -> int:
    """
    Soft delete members that are in the database but not in the fetched member IDs

    Args:
        fetched_member_ids: Set of member IDs fetched from Ghost API

    Returns:
        Number of members soft deleted
    """
    if not fetched_member_ids:
        return 0

    try:
        # Soft delete members not in fetched set
        deleted_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        return (
            Member.update(deleted_at=deleted_at, updated_at=deleted_at)
            .where((Member.deleted_at.is_null()) & ~(Member.id.in_(fetched_member_ids)))
            .execute()
        )
    except DatabaseError as e:
        logger.error(f"Database error soft deleting missing members: {e}")
        raise


def fetch_and_save_members(
    since: Optional[str] = None, fetch_attribution: bool = False
) -> int:
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
    if database.is_closed():
        database.connect()

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
                        existing_member = Member.get_or_none(Member.id == member["id"])

                        # Only fetch if attribution_id is NULL (not yet fetched)
                        if (
                            existing_member is None
                            or existing_member.attribution_id is None
                        ):
                            attribution = fetch_member_attribution(member["id"])
                            if attribution:
                                logger.debug(
                                    f"Fetched attribution for {member.get('email')}"
                                )

                    # Insert member with attribution data
                    insert_member(member, attribution)
                    process_member_relationships(member)
                    page_saved += 1

                # Commit this page
                database.commit()
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
            deleted_count = soft_delete_missing_members(fetched_member_ids)
            if deleted_count > 0:
                logger.info(
                    f"Soft deleted {deleted_count} members no longer in Ghost API"
                )
                database.commit()

    finally:
        database.close()

    logger.info(f"Total members saved: {total_saved}")
    return total_saved


def backfill_attribution() -> int:
    """
    Backfill attribution data for all members in database with NULL attribution_id

    Returns:
        Number of members with attribution fetched
    """
    database.connect()

    try:
        members_to_backfill = (
            Member.select(Member.id, Member.email)
            .where((Member.attribution_id.is_null()) & (Member.deleted_at.is_null()))
            .order_by(Member.created_at.desc())
        )

        total_members = members_to_backfill.count()

        if total_members == 0:
            logger.info("No members found with missing attribution data")
            return 0

        logger.info(f"Found {total_members} members with missing attribution data")
        logger.info("Starting attribution backfill (this will be slow)...")

        backfilled_count = 0
        failed_count = 0

        attribution_fields = ["id", "type", "url", "title", "referrer_source", "referrer_medium", "referrer_url"]

        for i, member in enumerate(members_to_backfill, 1):
            try:
                attribution = fetch_member_attribution(member.id)

                if attribution:
                    update_data = {f"attribution_{k}": attribution.get(k) for k in attribution_fields}
                    Member.update(**update_data).where(Member.id == member.id).execute()
                    backfilled_count += 1
                else:
                    Member.update(attribution_id="").where(Member.id == member.id).execute()

                if i % 10 == 0:
                    database.commit()
                    logger.info(
                        f"Progress: {i}/{total_members} members processed ({backfilled_count} with attribution)"
                    )

            except Exception as e:
                logger.warning(f"Failed to fetch attribution for {member.email}: {e}")
                failed_count += 1

        database.commit()

        logger.info(
            f"Backfill complete: {backfilled_count} members with attribution, "
            f"{total_members - backfilled_count - failed_count} without attribution, {failed_count} failed"
        )
        return backfilled_count

    finally:
        database.close()


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
            logger.info(
                f"✅ Attribution backfill completed! {backfilled_count} members updated"
            )
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
    database.connect()

    # Start tracking this sync run
    started_at = datetime.now(timezone.utc).isoformat()
    with database.atomic():
        sync_run = SyncRun.create(started_at=started_at, status="running")
        sync_run_id = sync_run.id

    try:
        # Fetch and save members (streaming approach)
        logger.info("Starting sync process...")
        if args.attribution:
            logger.info("Attribution fetching enabled (this will be slow)")
        saved_count = fetch_and_save_members(
            since=since_timestamp, fetch_attribution=args.attribution
        )

        if saved_count == 0:
            logger.warning("No members found to process")
            SyncRun.update(
                completed_at=datetime.now(timezone.utc).isoformat(),
                status="completed",
                members_fetched=0,
            ).where(SyncRun.id == sync_run_id).execute()
            database.close()
            return

        # Update sync run as completed
        SyncRun.update(
            completed_at=datetime.now(timezone.utc).isoformat(),
            status="completed",
            members_fetched=saved_count,
            members_saved=saved_count,
        ).where(SyncRun.id == sync_run_id).execute()

        # Checkpoint WAL to clean up .db-wal file
        try:
            database.execute_sql("PRAGMA wal_checkpoint(TRUNCATE)")
        except DatabaseError as e:
            logger.warning(f"Could not checkpoint WAL (database may be in use): {e}")

        logger.info(
            f"✅ Sync completed successfully! {saved_count} members saved to '{DATABASE_FILE}'"
        )

    except Exception as e:
        logger.error(f"Sync failed: {e}", exc_info=True)

        # Update sync run as failed
        SyncRun.update(
            completed_at=datetime.now(timezone.utc).isoformat(),
            status="failed",
            error_message=str(e),
        ).where(SyncRun.id == sync_run_id).execute()

        database.close()
        sys.exit(1)

    database.close()


if __name__ == "__main__":
    main()
