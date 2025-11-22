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
from typing import Dict, Any, Optional, List
from datetime import datetime
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


# ============================================
# CONFIGURATION
# ============================================

GHOST_URL = os.getenv('GHOST_URL')  # Your Ghost URL (no trailing slash)
ADMIN_API_KEY = os.getenv('ADMIN_API_KEY')  # Your Admin API Key (format: id:secret)
MEMBERS_PAGE_SIZE = 100    # Number of members to fetch per page
DATABASE_FILE = 'ghost_members.db'  # SQLite database file name
SCHEMA_FILE = 'schema.sql'  # Database schema file name


# ============================================
# JWT TOKEN GENERATION (HMAC)
# ============================================

def base64_url_encode(data: bytes) -> str:
    """Base64 URL encode without padding"""
    encoded = base64.b64encode(data).decode('utf-8')
    return encoded.replace('+', '-').replace('/', '_').rstrip('=')


def generate_token(admin_api_key: str) -> str:
    """Generate JWT token for Ghost Admin API"""
    try:
        key_id, key_secret = admin_api_key.split(':')
    except ValueError:
        raise ValueError('Invalid Admin API Key format. Expected: id:secret')

    if not all(c in '0123456789abcdefABCDEF' for c in key_secret):
        raise ValueError('Invalid Admin API Key: secret must be hexadecimal')

    # JWT header
    header = {
        'alg': 'HS256',
        'typ': 'JWT',
        'kid': key_id
    }

    # JWT payload
    now = int(time.time())
    payload = {
        'iat': now,
        'exp': now + 300,
        'aud': '/admin/'
    }

    # Encode header and payload
    header_encoded = base64_url_encode(json.dumps(header).encode('utf-8'))
    payload_encoded = base64_url_encode(json.dumps(payload).encode('utf-8'))
    unsigned = f'{header_encoded}.{payload_encoded}'

    # Convert hex secret to bytes
    secret_bytes = bytes.fromhex(key_secret)

    # Sign with HMAC-SHA256
    signature = hmac.new(
        secret_bytes,
        unsigned.encode('utf-8'),
        hashlib.sha256
    ).digest()

    signature_encoded = base64_url_encode(signature)

    return f'{unsigned}.{signature_encoded}'


# ============================================
# GHOST API REQUEST FUNCTION
# ============================================

def make_ghost_request(
    endpoint: str,
    method: str = 'GET',
    data: Optional[Dict[str, Any]] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Make an authenticated request to the Ghost Admin API

    Args:
        endpoint: The API endpoint (e.g., '/ghost/api/admin/members/')
        method: HTTP method (GET, POST, PUT, DELETE)
        data: Optional JSON data for POST/PUT requests
        **kwargs: Additional arguments to pass to requests

    Returns:
        Parsed JSON response
    """
    token = generate_token(ADMIN_API_KEY)
    url = GHOST_URL + endpoint

    headers = {
        'Authorization': f'Ghost {token}',
        'Accept-Version': 'v5.0',
    }

    if data:
        headers['Content-Type'] = 'application/json'

    # Merge with any additional headers
    if 'headers' in kwargs:
        headers.update(kwargs.pop('headers'))

    response = requests.request(
        method=method,
        url=url,
        headers=headers,
        json=data,
        **kwargs
    )

    if response.ok:
        return response.json()
    else:
        raise Exception(f'API returned status {response.status_code}: {response.text}')


# ============================================
# DATABASE SETUP
# ============================================

def setup_database():
    """Create SQLite database and tables using schema.sql file"""
    # Read schema from file
    with open(SCHEMA_FILE, 'r') as f:
        schema_sql = f.read()
    
    # Connect to database and execute schema
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    
    # Execute the schema (split by semicolons to handle multiple statements)
    statements = [stmt.strip() for stmt in schema_sql.split(';') if stmt.strip()]
    
    for statement in statements:
        # Skip comments and empty statements
        if statement.startswith('--') or not statement.strip():
            continue
        cursor.execute(statement)
    
    conn.commit()
    conn.close()
    print(f"Database '{DATABASE_FILE}' created successfully using schema.sql")


# ============================================
# DATA INSERTION FUNCTIONS
# ============================================

def insert_member(cursor: sqlite3.Cursor, member: Dict[str, Any]) -> None:
    """Insert or update a member record"""
    # Handle email_suppression as JSON string
    email_suppression = member.get('email_suppression')
    email_suppression_json = json.dumps(email_suppression) if email_suppression else None
    
    cursor.execute('''
        INSERT OR REPLACE INTO members (
            id, uuid, email, name, note, geolocation, subscribed,
            created_at, updated_at, avatar_image, comped,
            email_count, email_opened_count, email_open_rate,
            status, last_seen_at, unsubscribe_url, email_suppression
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        member.get('id'),
        member.get('uuid'),
        member.get('email'),
        member.get('name'),
        member.get('note'),
        member.get('geolocation'),
        member.get('subscribed'),
        member.get('created_at'),
        member.get('updated_at'),
        member.get('avatar_image'),
        member.get('comped'),
        member.get('email_count'),
        member.get('email_opened_count'),
        member.get('email_open_rate'),
        member.get('status'),
        member.get('last_seen_at'),
        member.get('unsubscribe_url'),
        email_suppression_json
    ))


def insert_labels(cursor: sqlite3.Cursor, member_id: str, labels: List[Dict[str, Any]]) -> None:
    """Insert labels and member-label relationships"""
    for label in labels:
        # Insert label
        cursor.execute('''
            INSERT OR REPLACE INTO labels (
                id, name, slug, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?)
        ''', (
            label.get('id'),
            label.get('name'),
            label.get('slug'),
            label.get('created_at'),
            label.get('updated_at')
        ))

        # Insert member-label relationship
        cursor.execute('''
            INSERT OR REPLACE INTO member_labels (member_id, label_id)
            VALUES (?, ?)
        ''', (member_id, label.get('id')))


def insert_newsletters(cursor: sqlite3.Cursor, member_id: str, newsletters: List[Dict[str, Any]]) -> None:
    """Insert newsletters and member-newsletter relationships"""
    for newsletter in newsletters:
        # Insert newsletter
        cursor.execute('''
            INSERT OR REPLACE INTO newsletters (
                id, name, description, status
            ) VALUES (?, ?, ?, ?)
        ''', (
            newsletter.get('id'),
            newsletter.get('name'),
            newsletter.get('description'),
            newsletter.get('status')
        ))

        # Insert member-newsletter relationship
        cursor.execute('''
            INSERT OR REPLACE INTO member_newsletters (member_id, newsletter_id)
            VALUES (?, ?)
        ''', (member_id, newsletter.get('id')))


def insert_subscriptions(cursor: sqlite3.Cursor, member_id: str, subscriptions: List[Dict[str, Any]]) -> None:
    """Insert subscriptions for a member"""
    for subscription in subscriptions:
        # Store subscription details as JSON strings to avoid complex tables
        customer = subscription.get('customer')
        customer_json = json.dumps(customer) if customer else None
        
        price = subscription.get('price')
        price_json = json.dumps(price) if price else None
        
        tier = subscription.get('tier')
        if tier:
            # Extract simple tier info instead of storing full JSON
            tier_id = tier.get('id')
            tier_name = tier.get('name')
        else:
            tier_id = None
            tier_name = None
        
        offer = subscription.get('offer')
        offer_json = json.dumps(offer) if offer else None
        
        cursor.execute('''
            INSERT OR REPLACE INTO subscriptions (
                id, member_id, customer, status, start_date,
                default_payment_card_last4, cancel_at_period_end,
                cancellation_reason, current_period_end, trial_start_at,
                trial_end_at, price, tier_id, tier_name, offer
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            subscription.get('id'),
            member_id,
            customer_json,
            subscription.get('status'),
            subscription.get('start_date'),
            subscription.get('default_payment_card_last4'),
            subscription.get('cancel_at_period_end'),
            subscription.get('cancellation_reason'),
            subscription.get('current_period_end'),
            subscription.get('trial_start_at'),
            subscription.get('trial_end_at'),
            price_json,
            tier_id,
            tier_name,
            offer_json
        ))


def insert_tiers(cursor: sqlite3.Cursor, member_id: str, tiers: List[Dict[str, Any]]) -> None:
    """Insert tiers and member-tier relationships"""
    for tier in tiers:
        # Insert tier
        cursor.execute('''
            INSERT OR REPLACE INTO tiers (
                id, name, slug, active, trial_days, description,
                type, currency, monthly_price, yearly_price,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            tier.get('id'),
            tier.get('name'),
            tier.get('slug'),
            tier.get('active'),
            tier.get('trial_days'),
            tier.get('description'),
            tier.get('type'),
            tier.get('currency'),
            tier.get('monthly_price'),
            tier.get('yearly_price'),
            tier.get('created_at'),
            tier.get('updated_at')
        ))

        # Insert member-tier relationship
        cursor.execute('''
            INSERT OR REPLACE INTO member_tiers (member_id, tier_id)
            VALUES (?, ?)
        ''', (member_id, tier.get('id')))


def insert_email_recipients(cursor: sqlite3.Cursor, member_id: str, email_recipients: List[Dict[str, Any]]) -> None:
    """Insert email recipients and related emails"""
    for recipient in email_recipients:
        # Insert email recipient
        cursor.execute('''
            INSERT OR REPLACE INTO email_recipients (
                id, email_id, member_id, batch_id, processed_at,
                delivered_at, opened_at, failed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            recipient.get('id'),
            recipient.get('email_id'),
            member_id,
            recipient.get('batch_id'),
            recipient.get('processed_at'),
            recipient.get('delivered_at'),
            recipient.get('opened_at'),
            recipient.get('failed_at')
        ))

        # Insert related email if present
        email_data = recipient.get('email')
        if email_data:
            cursor.execute('''
                INSERT OR REPLACE INTO emails (
                    id, post_id, uuid, status, recipient_filter,
                    error, error_data, email_count, delivered_count, opened_count,
                    failed_count, subject, from_address, reply_to,
                    source, source_type, track_opens, track_clicks,
                    feedback_enabled, submitted_at, newsletter_id,
                    created_at, updated_at, csd_email_count
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                email_data.get('id'),
                email_data.get('post_id'),
                email_data.get('uuid'),
                email_data.get('status'),
                email_data.get('recipient_filter'),
                email_data.get('error'),
                email_data.get('error_data'),
                email_data.get('email_count'),
                email_data.get('delivered_count'),
                email_data.get('opened_count'),
                email_data.get('failed_count'),
                email_data.get('subject'),
                email_data.get('from'),
                email_data.get('reply_to'),
                email_data.get('source'),
                email_data.get('source_type'),
                email_data.get('track_opens'),
                email_data.get('track_clicks'),
                email_data.get('feedback_enabled'),
                email_data.get('submitted_at'),
                email_data.get('newsletter_id'),
                email_data.get('created_at'),
                email_data.get('updated_at'),
                email_data.get('csd_email_count')
            ))


# ============================================
# DATA FETCHING AND PROCESSING
# ============================================

def fetch_all_members() -> List[Dict[str, Any]]:
    """Fetch all members from Ghost API using pagination"""
    all_members = []
    page = 1
    
    print("Fetching members from Ghost API...")
    
    while True:
        endpoint = f'/ghost/api/admin/members/?limit={MEMBERS_PAGE_SIZE}&include=email_recipients,subscriptions,newsletters,tiers&page={page}'
        
        try:
            response = make_ghost_request(endpoint)
            members = response.get('members', [])
            
            if not members:
                break
                
            all_members.extend(members)
            print(f"Fetched page {page}, {len(members)} members (total: {len(all_members)})")
            
            # Check if there are more pages
            meta = response.get('meta', {})
            pagination = meta.get('pagination', {})
            
            if pagination.get('page', 1) >= pagination.get('pages', 1):
                break
                
            page += 1
            
        except Exception as e:
            print(f"Error fetching page {page}: {e}")
            break
    
    print(f"Total members fetched: {len(all_members)}")
    return all_members


def save_members_to_database(members: List[Dict[str, Any]]) -> None:
    """Save members data to SQLite database"""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    
    print(f"Saving {len(members)} members to database...")
    
    for i, member in enumerate(members):
        try:
            # Insert member
            insert_member(cursor, member)
            
            # Insert labels
            labels = member.get('labels', [])
            if labels:
                insert_labels(cursor, member['id'], labels)
            
            # Insert newsletters
            newsletters = member.get('newsletters', [])
            if newsletters:
                insert_newsletters(cursor, member['id'], newsletters)
            
            # Insert subscriptions
            subscriptions = member.get('subscriptions', [])
            if subscriptions:
                insert_subscriptions(cursor, member['id'], subscriptions)
            
            # Insert tiers
            tiers = member.get('tiers', [])
            if tiers:
                insert_tiers(cursor, member['id'], tiers)
            
            # Insert email recipients
            email_recipients = member.get('email_recipients', [])
            if email_recipients:
                insert_email_recipients(cursor, member['id'], email_recipients)
            
            if (i + 1) % 100 == 0:
                print(f"Processed {i + 1}/{len(members)} members")
                
        except Exception as e:
            print(f"Error processing member {member.get('id', 'unknown')}: {e}")
    
    conn.commit()
    conn.close()
    print("All members saved to database successfully")


# ============================================
# MAIN FUNCTION
# ============================================

def main():
    """Main execution function"""
    if not ADMIN_API_KEY:
        print("❌ Error: Please set your ADMIN_API_KEY in the configuration section")
        return
    
    try:
        # Setup database
        setup_database()
        
        # Fetch all members
        members = fetch_all_members()
        
        if not members:
            print("No members found to process")
            return
        
        # Save to database
        save_members_to_database(members)
        
        print(f"\n✅ Success! {len(members)} members have been saved to '{DATABASE_FILE}'")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")


if __name__ == '__main__':
    main()