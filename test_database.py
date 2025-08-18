#!/usr/bin/env python3
"""
Unit tests for the StonksDatabase class, specifically testing item name storage functionality.
Uses real API calls to test the complete functionality.
"""

import os
import tempfile
import time
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


class TestSaleRecording:
  """Unit tests for sale recording functionality in StonksDatabase."""

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

  def test_insert_valid_sale(self, temp_db):
    """Test recording a valid sale with provided test data."""
    current_time = int(time.time())

    # World ID: 402, Buyer: Wyra Mhakaraca, Item ID: 46829, Quantity: 1, Price: 4,592,000
    result = temp_db.insert_sale(
      timestamp=current_time,
      world_id=402,
      item_id=46829,
      price=4592000,
      quantity=1,
      buyer="Wyra Mhakaraca",
    )

    # Should return True for successful insertion
    assert result is True

    # Verify the sale was stored in database
    cur = temp_db.connection.cursor()
    cur.execute(
      "SELECT timestamp, world_id, item_id, price, quantity, buyer FROM sales WHERE timestamp = ? AND item_id = ? AND price = ?",
      (current_time, 46829, 4592000),
    )
    sale = cur.fetchone()

    assert sale is not None
    assert sale[0] == current_time  # timestamp
    assert sale[1] == 402  # world_id
    assert sale[2] == 46829  # item_id
    assert sale[3] == 4592000  # price
    assert sale[4] == 1  # quantity
    assert sale[5] == "Wyra Mhakaraca"  # buyer

  def test_insert_sale_invalid_world_id(self, temp_db):
    """Test recording a sale with invalid world ID."""
    current_time = int(time.time())

    # World ID: 99999, Buyer: Doesnt Exist, Item ID: 46829, Quantity: 1, Price: 4,592,000
    result = temp_db.insert_sale(
      timestamp=current_time,
      world_id=99999,
      item_id=46829,
      price=4592000,
      quantity=1,
      buyer="Doesnt Exist",
    )

    # Should still return True (database doesn't validate world existence)
    assert result is True

    # Verify the sale was stored (invalid world IDs are allowed in the sales table)
    cur = temp_db.connection.cursor()
    cur.execute(
      "SELECT world_id, buyer FROM sales WHERE timestamp = ? AND item_id = ? AND price = ?",
      (current_time, 46829, 4592000),
    )
    sale = cur.fetchone()

    assert sale is not None
    assert sale[0] == 99999  # world_id
    assert sale[1] == "Doesnt Exist"  # buyer

  def test_insert_sale_invalid_item_id(self, temp_db):
    """Test recording a sale with invalid item ID."""
    current_time = int(time.time())

    # World ID: 402, Buyer: Wyra Mhakaraca, Item ID: 99999999, Quantity: 1, Price: 500
    result = temp_db.insert_sale(
      timestamp=current_time,
      world_id=402,
      item_id=99999999,
      price=500,
      quantity=1,
      buyer="Wyra Mhakaraca",
    )

    # Should still return True (database doesn't validate item existence)
    assert result is True

    # Verify the sale was stored (invalid item IDs are allowed in the sales table)
    cur = temp_db.connection.cursor()
    cur.execute(
      "SELECT item_id, price FROM sales WHERE timestamp = ? AND world_id = ? AND buyer = ?",
      (current_time, 402, "Wyra Mhakaraca"),
    )
    sale = cur.fetchone()

    assert sale is not None
    assert sale[0] == 99999999  # item_id
    assert sale[1] == 500  # price

  def test_insert_sale_old_timestamp(self, temp_db):
    """Test that sales older than 7 days are rejected."""
    # Create timestamp older than 7 days
    old_timestamp = int(time.time()) - (60 * 60 * 24 * 8)  # 8 days ago

    result = temp_db.insert_sale(
      timestamp=old_timestamp,
      world_id=402,
      item_id=46829,
      price=1000000,
      quantity=1,
      buyer="Test Buyer",
    )

    # Should return False for old timestamp
    assert result is False

    # Verify the sale was NOT stored
    cur = temp_db.connection.cursor()
    cur.execute("SELECT COUNT(*) FROM sales WHERE timestamp = ?", (old_timestamp,))
    count = cur.fetchone()[0]
    assert count == 0

  def test_insert_sale_recent_timestamp(self, temp_db):
    """Test that sales within 7 days are accepted."""
    # Create timestamp within 7 days
    recent_timestamp = int(time.time()) - (60 * 60 * 24 * 6)  # 6 days ago

    result = temp_db.insert_sale(
      timestamp=recent_timestamp,
      world_id=402,
      item_id=46829,
      price=1000000,
      quantity=1,
      buyer="Test Buyer",
    )

    # Should return True for recent timestamp
    assert result is True

    # Verify the sale was stored
    cur = temp_db.connection.cursor()
    cur.execute("SELECT COUNT(*) FROM sales WHERE timestamp = ?", (recent_timestamp,))
    count = cur.fetchone()[0]
    assert count == 1

  def test_insert_duplicate_sale(self, temp_db):
    """Test that duplicate sales are handled correctly (ON CONFLICT DO NOTHING)."""
    current_time = int(time.time())

    # Insert the same sale twice
    result1 = temp_db.insert_sale(
      timestamp=current_time,
      world_id=402,
      item_id=46829,
      price=4592000,
      quantity=1,
      buyer="Wyra Mhakaraca",
    )

    result2 = temp_db.insert_sale(
      timestamp=current_time,
      world_id=402,
      item_id=46829,
      price=4592000,
      quantity=1,
      buyer="Wyra Mhakaraca",
    )

    # Both should return True
    assert result1 is True
    assert result2 is True

    # But only one record should exist (due to PRIMARY KEY constraint)
    cur = temp_db.connection.cursor()
    cur.execute(
      "SELECT COUNT(*) FROM sales WHERE timestamp = ? AND item_id = ? AND price = ?",
      (current_time, 46829, 4592000),
    )
    count = cur.fetchone()[0]
    assert count == 1

  def test_multiple_sales_same_timestamp_different_items(self, temp_db):
    """Test multiple sales with same timestamp but different items."""
    current_time = int(time.time())

    # Insert multiple sales with same timestamp
    sales_data = [
      (402, 46829, 4592000, 1, "Wyra Mhakaraca"),
      (402, 46063, 1500000, 2, "Another Buyer"),
      (402, 3, 100, 5, "Third Buyer"),
    ]

    for world_id, item_id, price, quantity, buyer in sales_data:
      result = temp_db.insert_sale(
        timestamp=current_time,
        world_id=world_id,
        item_id=item_id,
        price=price,
        quantity=quantity,
        buyer=buyer,
      )
      assert result is True

    # Verify all sales were stored
    cur = temp_db.connection.cursor()
    cur.execute("SELECT COUNT(*) FROM sales WHERE timestamp = ?", (current_time,))
    count = cur.fetchone()[0]
    assert count == 3

  def test_all_test_case_sales(self, temp_db):
    """Test all provided test case sales together."""
    current_time = int(time.time())

    test_sales = [
      # Valid sale
      (402, 46829, 4592000, 1, "Wyra Mhakaraca"),
      # Invalid world ID
      (99999, 46829, 4592000, 1, "Doesnt Exist"),
      # Invalid item ID
      (402, 99999999, 500, 1, "Wyra Mhakaraca"),
    ]

    # Insert all test sales
    for world_id, item_id, price, quantity, buyer in test_sales:
      result = temp_db.insert_sale(
        timestamp=current_time + len(test_sales),  # Slightly different timestamps
        world_id=world_id,
        item_id=item_id,
        price=price,
        quantity=quantity,
        buyer=buyer,
      )
      assert result is True
      current_time += 1  # Increment to avoid duplicate primary keys

    # Verify all sales were stored
    cur = temp_db.connection.cursor()
    cur.execute("SELECT COUNT(*) FROM sales")
    count = cur.fetchone()[0]
    assert count == 3


if __name__ == "__main__":
  pytest.main([__file__, "-v"])
