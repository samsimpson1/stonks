#!/usr/bin/env python3
"""
Unit tests for the StonksDatabase class, specifically testing item name storage functionality.
Uses real API calls to test the complete functionality.
"""

import os
import tempfile
import pytest
from database import StonksDatabase


class TestItemNameStorage:
  """Unit tests for item name storage functionality in StonksDatabase."""

  @pytest.fixture
  def temp_db(self):
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as temp_db:
      temp_db_path = temp_db.name

    db = StonksDatabase(temp_db_path)
    yield db

    # Cleanup
    db.close()
    try:
      os.unlink(temp_db_path)
    except FileNotFoundError:
      pass

  def test_get_item_name_existing_item(self, temp_db):
    """Test retrieving an item name that exists in the database."""
    # Insert test data directly
    cur = temp_db.connection.cursor()
    cur.execute(
      "INSERT INTO items (item_id, item_name) VALUES (?, ?)", (46829, "Yan Horn")
    )
    temp_db.connection.commit()

    # Test retrieval
    result = temp_db.get_item_name(46829)
    assert result == "Yan Horn"

  def test_get_item_name_nonexistent_item(self, temp_db):
    """Test retrieving an item name that doesn't exist in the database."""
    result = temp_db.get_item_name(99999)
    assert result is None

  def test_get_item_name_string_id(self, temp_db):
    """Test that get_item_name works with string item IDs."""
    # Insert test data
    cur = temp_db.connection.cursor()
    cur.execute(
      "INSERT INTO items (item_id, item_name) VALUES (?, ?)",
      (46063, "Ceremonial Tunic of Casting"),
    )
    temp_db.connection.commit()

    # Test with string ID
    result = temp_db.get_item_name("46063")
    assert result == "Ceremonial Tunic of Casting"

  def test_store_item_name_yan_horn(self, temp_db):
    """Test storing Yan Horn (item ID 46829) using real API."""
    # Store the item using real API
    temp_db.store_item_name(46829)

    # Verify item was stored correctly
    result = temp_db.get_item_name(46829)
    assert result == "Yan Horn"

  def test_store_item_name_ceremonial_tunic(self, temp_db):
    """Test storing Ceremonial Tunic of Casting (item ID 46063) using real API."""
    # Store the item using real API
    temp_db.store_item_name(46063)

    # Verify item was stored correctly
    result = temp_db.get_item_name(46063)
    assert result == "Ceremonial Tunic of Casting"

  def test_store_item_name_ice_shard(self, temp_db):
    """Test storing Ice Shard (item ID 3) using real API."""
    # Store the item using real API
    temp_db.store_item_name(3)

    # Verify item was stored correctly
    result = temp_db.get_item_name(3)
    assert result == "Ice Shard"

  def test_store_item_name_invalid_item(self, temp_db):
    """Test storing an invalid item ID using real API."""
    # Use a very high item ID that likely doesn't exist
    invalid_item_id = 999999999

    # Store the item using real API
    temp_db.store_item_name(invalid_item_id)

    # Verify unknown item name was stored for 404 responses
    result = temp_db.get_item_name(invalid_item_id)
    expected_name = f"Unknown Item {invalid_item_id}"
    assert result == expected_name

  def test_store_item_name_skips_existing(self, temp_db):
    """Test that store_item_name skips items that already exist."""
    # Insert existing item
    cur = temp_db.connection.cursor()
    cur.execute(
      "INSERT INTO items (item_id, item_name) VALUES (?, ?)", (46829, "Yan Horn")
    )
    temp_db.connection.commit()

    # Try to store the same item (should skip API call)
    temp_db.store_item_name(46829)

    # Verify item name unchanged
    result = temp_db.get_item_name(46829)
    assert result == "Yan Horn"

  def test_store_item_name_caching_behavior(self, temp_db):
    """Test that store_item_name respects caching to avoid duplicate API calls."""
    # Clear any existing cache
    temp_db.item_cache.clear()

    # First call should make API request and cache the result
    temp_db.store_item_name(3)

    # Verify item is in cache
    assert 3 in temp_db.item_cache

    # Verify item was stored
    result = temp_db.get_item_name(3)
    assert result == "Ice Shard"

    # Second immediate call should use cache (we can't easily verify this without mocking,
    # but we can at least verify the result is still correct)
    temp_db.store_item_name(3)
    result = temp_db.get_item_name(3)
    assert result == "Ice Shard"

  def test_store_item_name_string_id(self, temp_db):
    """Test that store_item_name works with string item IDs."""
    # Store with string ID
    temp_db.store_item_name("46063")

    # Verify item stored correctly
    result = temp_db.get_item_name(46063)
    assert result == "Ceremonial Tunic of Casting"

  def test_all_test_data_items(self, temp_db):
    """Test all provided test data items using real API calls."""
    test_items = [
      (46829, "Yan Horn"),
      (46063, "Ceremonial Tunic of Casting"),
      (3, "Ice Shard"),
    ]

    # Store all items using real API
    for item_id, expected_name in test_items:
      temp_db.store_item_name(item_id)

    # Verify all items were stored correctly
    for item_id, expected_name in test_items:
      result = temp_db.get_item_name(item_id)
      assert result == expected_name, (
        f"Expected '{expected_name}' for item {item_id}, got '{result}'"
      )

  def test_database_persistence(self, temp_db):
    """Test that stored item names persist in the database."""
    # Store an item
    temp_db.store_item_name(3)

    # Verify it's stored
    result1 = temp_db.get_item_name(3)
    assert result1 == "Ice Shard"

    # Clear the cache to ensure we're reading from database
    temp_db.item_cache.clear()

    # Verify it's still there after cache clear
    result2 = temp_db.get_item_name(3)
    assert result2 == "Ice Shard"


if __name__ == "__main__":
  pytest.main([__file__, "-v"])
