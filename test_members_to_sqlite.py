#!/usr/bin/env python3
"""
Strategic tests for members_to_sqlite.py
These tests cover critical functionality without being exhaustive
"""

import pytest
import sqlite3
import tempfile
import os
import json
from unittest.mock import patch, MagicMock
from datetime import datetime

# Import the module to test
import members_to_sqlite


class TestJWTGeneration:
    """Test JWT token generation for Ghost API authentication"""

    def test_generate_token_valid_key(self):
        """Test JWT generation with a valid admin API key"""
        # Use a sample key format (id:hex_secret)
        test_key = "abc123:0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"

        token = members_to_sqlite.generate_token(test_key)

        # Token should have 3 parts separated by dots
        parts = token.split('.')
        assert len(parts) == 3, "JWT should have 3 parts: header.payload.signature"

        # Each part should be non-empty
        assert all(part for part in parts), "All JWT parts should be non-empty"

    def test_generate_token_invalid_format(self):
        """Test JWT generation fails with invalid key format"""
        with pytest.raises(ValueError, match="Invalid Admin API Key format"):
            members_to_sqlite.generate_token("invalid-key-no-colon")

    def test_generate_token_non_hex_secret(self):
        """Test JWT generation fails with non-hexadecimal secret"""
        with pytest.raises(ValueError, match="secret must be hexadecimal"):
            members_to_sqlite.generate_token("abc123:not-a-hex-string!")


class TestDatabaseSetup:
    """Test database initialization and schema setup"""

    def test_database_creation(self, tmp_path):
        """Test that database and tables are created correctly"""
        # Use temporary database
        db_file = tmp_path / "test_ghost.db"

        # Temporarily override the DATABASE_FILE
        original_db = members_to_sqlite.DATABASE_FILE
        members_to_sqlite.DATABASE_FILE = str(db_file)

        try:
            members_to_sqlite.setup_database()

            # Verify database file exists
            assert db_file.exists(), "Database file should be created"

            # Verify tables exist
            conn = sqlite3.connect(str(db_file))
            cursor = conn.cursor()

            # Check for key tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = {row[0] for row in cursor.fetchall()}

            expected_tables = {
                'members', 'labels', 'member_labels',
                'newsletters', 'member_newsletters',
                'tiers', 'member_tiers', 'subscriptions',
                'email_recipients', 'emails', 'sync_runs'
            }

            assert expected_tables.issubset(tables), f"Missing tables: {expected_tables - tables}"

            conn.close()
        finally:
            members_to_sqlite.DATABASE_FILE = original_db

    def test_sync_runs_table_structure(self, tmp_path):
        """Test that sync_runs table has correct structure"""
        db_file = tmp_path / "test_ghost.db"

        original_db = members_to_sqlite.DATABASE_FILE
        members_to_sqlite.DATABASE_FILE = str(db_file)

        try:
            members_to_sqlite.setup_database()

            conn = sqlite3.connect(str(db_file))
            cursor = conn.cursor()

            # Get table info
            cursor.execute("PRAGMA table_info(sync_runs)")
            columns = {row[1]: row[2] for row in cursor.fetchall()}

            # Verify key columns exist
            assert 'id' in columns
            assert 'started_at' in columns
            assert 'completed_at' in columns
            assert 'status' in columns
            assert 'members_fetched' in columns
            assert 'members_saved' in columns

            conn.close()
        finally:
            members_to_sqlite.DATABASE_FILE = original_db


class TestMemberInsertion:
    """Test member data insertion and updates"""

    def test_insert_member_basic(self, tmp_path):
        """Test inserting a basic member record"""
        db_file = tmp_path / "test_ghost.db"

        original_db = members_to_sqlite.DATABASE_FILE
        members_to_sqlite.DATABASE_FILE = str(db_file)

        try:
            members_to_sqlite.setup_database()

            conn = sqlite3.connect(str(db_file))
            cursor = conn.cursor()

            # Sample member data
            member = {
                'id': 'test_id_123',
                'uuid': 'test-uuid-456',
                'email': 'test@example.com',
                'name': 'Test User',
                'status': 'free',
                'subscribed': True,
                'created_at': '2024-01-01T00:00:00.000Z',
                'updated_at': '2024-01-01T00:00:00.000Z',
                'email_count': 10,
                'email_opened_count': 5,
                'email_open_rate': 50
            }

            members_to_sqlite.insert_member(cursor, member)
            conn.commit()

            # Verify insertion
            cursor.execute("SELECT email, name, status FROM members WHERE id = ?", ('test_id_123',))
            result = cursor.fetchone()

            assert result is not None, "Member should be inserted"
            assert result[0] == 'test@example.com'
            assert result[1] == 'Test User'
            assert result[2] == 'free'

            conn.close()
        finally:
            members_to_sqlite.DATABASE_FILE = original_db

    def test_insert_member_idempotency(self, tmp_path):
        """Test that inserting the same member twice updates instead of duplicating"""
        db_file = tmp_path / "test_ghost.db"

        original_db = members_to_sqlite.DATABASE_FILE
        members_to_sqlite.DATABASE_FILE = str(db_file)

        try:
            members_to_sqlite.setup_database()

            conn = sqlite3.connect(str(db_file))
            cursor = conn.cursor()

            # Initial member data
            member_v1 = {
                'id': 'test_id_123',
                'uuid': 'test-uuid-456',
                'email': 'test@example.com',
                'name': 'Test User V1',
                'status': 'free',
                'subscribed': True,
                'created_at': '2024-01-01T00:00:00.000Z',
                'updated_at': '2024-01-01T00:00:00.000Z',
                'email_count': 10,
                'email_opened_count': 5,
                'email_open_rate': 50
            }

            # Updated member data
            member_v2 = member_v1.copy()
            member_v2['name'] = 'Test User V2'
            member_v2['email_count'] = 15
            member_v2['updated_at'] = '2024-01-02T00:00:00.000Z'

            # Insert first version
            members_to_sqlite.insert_member(cursor, member_v1)
            conn.commit()

            # Insert second version (should update, not duplicate)
            members_to_sqlite.insert_member(cursor, member_v2)
            conn.commit()

            # Verify only one record exists with updated data
            cursor.execute("SELECT COUNT(*), name, email_count FROM members WHERE id = ?", ('test_id_123',))
            result = cursor.fetchone()

            assert result[0] == 1, "Should have exactly one member record"
            assert result[1] == 'Test User V2', "Name should be updated"
            assert result[2] == 15, "Email count should be updated"

            conn.close()
        finally:
            members_to_sqlite.DATABASE_FILE = original_db


class TestAPIFetching:
    """Test API fetching with mocked responses"""

    @patch('members_to_sqlite.make_ghost_request')
    def test_fetch_single_page(self, mock_request):
        """Test fetching members when all fit in one page"""
        # Mock API response
        mock_request.return_value = {
            'members': [
                {'id': '1', 'email': 'user1@example.com', 'name': 'User 1'},
                {'id': '2', 'email': 'user2@example.com', 'name': 'User 2'}
            ],
            'meta': {
                'pagination': {
                    'page': 1,
                    'pages': 1
                }
            }
        }

        members = members_to_sqlite.fetch_all_members()

        assert len(members) == 2, "Should fetch all members from single page"
        assert members[0]['email'] == 'user1@example.com'

    @patch('members_to_sqlite.make_ghost_request')
    def test_fetch_multiple_pages(self, mock_request):
        """Test fetching members across multiple pages"""
        # Mock paginated API responses
        def mock_response(endpoint, **kwargs):
            if 'page=1' in endpoint:
                return {
                    'members': [{'id': '1', 'email': 'user1@example.com'}],
                    'meta': {'pagination': {'page': 1, 'pages': 2}}
                }
            elif 'page=2' in endpoint:
                return {
                    'members': [{'id': '2', 'email': 'user2@example.com'}],
                    'meta': {'pagination': {'page': 2, 'pages': 2}}
                }
            return {'members': [], 'meta': {'pagination': {'page': 3, 'pages': 2}}}

        mock_request.side_effect = mock_response

        members = members_to_sqlite.fetch_all_members()

        assert len(members) == 2, "Should fetch members from all pages"
        assert members[0]['id'] == '1'
        assert members[1]['id'] == '2'

    @patch('members_to_sqlite.make_ghost_request')
    def test_fetch_incremental_with_since(self, mock_request):
        """Test fetching members with since parameter for incremental sync"""
        # Mock API response
        mock_request.return_value = {
            'members': [
                {'id': '3', 'email': 'newuser@example.com', 'name': 'New User'}
            ],
            'meta': {
                'pagination': {
                    'page': 1,
                    'pages': 1
                }
            }
        }

        since_time = '2024-01-01T00:00:00.000Z'
        members = members_to_sqlite.fetch_all_members(since=since_time)

        # Verify the filter was included in the endpoint
        call_args = mock_request.call_args[0][0]
        assert f"filter=updated_at:>'{since_time}'" in call_args, "Should include since filter in API call"
        assert len(members) == 1, "Should fetch only updated members"
        assert members[0]['email'] == 'newuser@example.com'


class TestIncrementalSync:
    """Test incremental sync functionality"""

    def test_get_last_sync_time_no_database(self):
        """Test getting last sync time when database doesn't exist"""
        original_db = members_to_sqlite.DATABASE_FILE
        members_to_sqlite.DATABASE_FILE = '/tmp/nonexistent_test.db'

        try:
            result = members_to_sqlite.get_last_sync_time()
            assert result is None, "Should return None when database doesn't exist"
        finally:
            members_to_sqlite.DATABASE_FILE = original_db

    def test_get_last_sync_time_with_history(self, tmp_path):
        """Test getting last sync time from existing sync history"""
        db_file = tmp_path / "test_ghost.db"
        original_db = members_to_sqlite.DATABASE_FILE
        members_to_sqlite.DATABASE_FILE = str(db_file)

        try:
            members_to_sqlite.setup_database()

            # Insert a completed sync run
            conn = sqlite3.connect(str(db_file))
            cursor = conn.cursor()

            test_time = '2024-01-01T12:00:00.000Z'
            cursor.execute(
                'INSERT INTO sync_runs (started_at, completed_at, status) VALUES (?, ?, ?)',
                ('2024-01-01T11:00:00.000Z', test_time, 'completed')
            )
            conn.commit()
            conn.close()

            # Get last sync time
            result = members_to_sqlite.get_last_sync_time()

            assert result == test_time, f"Should return the last completed sync time, got {result}"

        finally:
            members_to_sqlite.DATABASE_FILE = original_db


class TestSaveMembers:
    """Test the save_members_to_database function"""

    def test_save_members_returns_count(self, tmp_path):
        """Test that save_members_to_database returns correct count"""
        db_file = tmp_path / "test_ghost.db"

        original_db = members_to_sqlite.DATABASE_FILE
        members_to_sqlite.DATABASE_FILE = str(db_file)

        try:
            members_to_sqlite.setup_database()

            members = [
                {
                    'id': f'id_{i}',
                    'uuid': f'uuid_{i}',
                    'email': f'user{i}@example.com',
                    'name': f'User {i}',
                    'status': 'free',
                    'subscribed': True,
                    'created_at': '2024-01-01T00:00:00.000Z',
                    'updated_at': '2024-01-01T00:00:00.000Z',
                }
                for i in range(5)
            ]

            saved_count = members_to_sqlite.save_members_to_database(members)

            assert saved_count == 5, "Should save all members"

            # Verify in database
            conn = sqlite3.connect(str(db_file))
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM members")
            db_count = cursor.fetchone()[0]
            assert db_count == 5, "All members should be in database"
            conn.close()

        finally:
            members_to_sqlite.DATABASE_FILE = original_db

    def test_save_members_handles_errors_gracefully(self, tmp_path):
        """Test that save process continues even if individual members fail"""
        db_file = tmp_path / "test_ghost.db"

        original_db = members_to_sqlite.DATABASE_FILE
        members_to_sqlite.DATABASE_FILE = str(db_file)

        try:
            members_to_sqlite.setup_database()

            members = [
                {  # Valid member
                    'id': 'valid_1',
                    'uuid': 'uuid_1',
                    'email': 'user1@example.com',
                    'name': 'User 1',
                    'status': 'free',
                    'subscribed': True,
                    'created_at': '2024-01-01T00:00:00.000Z',
                    'updated_at': '2024-01-01T00:00:00.000Z',
                },
                {  # Invalid member (missing required uuid)
                    'id': 'invalid_2',
                    'email': 'user2@example.com',
                    'name': 'User 2',
                },
                {  # Valid member
                    'id': 'valid_3',
                    'uuid': 'uuid_3',
                    'email': 'user3@example.com',
                    'name': 'User 3',
                    'status': 'free',
                    'subscribed': True,
                    'created_at': '2024-01-01T00:00:00.000Z',
                    'updated_at': '2024-01-01T00:00:00.000Z',
                }
            ]

            # Should save 2 out of 3 members
            saved_count = members_to_sqlite.save_members_to_database(members)

            assert saved_count == 2, "Should save valid members despite errors"

        finally:
            members_to_sqlite.DATABASE_FILE = original_db


# Pytest fixtures
@pytest.fixture
def temp_db(tmp_path):
    """Provide a temporary database for tests"""
    db_file = tmp_path / "test.db"
    original = members_to_sqlite.DATABASE_FILE
    members_to_sqlite.DATABASE_FILE = str(db_file)
    yield db_file
    members_to_sqlite.DATABASE_FILE = original


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
