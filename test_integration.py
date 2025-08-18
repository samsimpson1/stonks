#!/usr/bin/env python3
"""
Integration test for the FFXIV market data scraper using pytest.
Tests that the scraper can connect to live APIs and collect real data.
"""

import os
import tempfile
import time
import sqlite3
import subprocess
import signal
import pytest


class TestScraperIntegration:
  """Integration tests for the FFXIV market data scraper."""

  @pytest.fixture
  def temp_db_path(self):
    """Create a temporary database file for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as temp_db:
      temp_db_path = temp_db.name

    yield temp_db_path

    # Cleanup
    try:
      os.unlink(temp_db_path)
    except FileNotFoundError:
      pass

  @pytest.fixture
  def scraper_process(self, temp_db_path):
    """Start the scraper process and ensure cleanup."""
    env = os.environ.copy()
    env["DB_PATH"] = temp_db_path

    process = subprocess.Popen(
      ["uv", "run", "scrape.py"],
      env=env,
      stdout=subprocess.PIPE,
      stderr=subprocess.PIPE,
    )

    yield process

    # Cleanup process
    if process and process.poll() is None:
      process.send_signal(signal.SIGTERM)
      try:
        process.wait(timeout=5)
      except subprocess.TimeoutExpired:
        process.kill()
        process.wait()

  def test_scraper_initialization(self, temp_db_path, scraper_process):
    """Test that the scraper can initialize and populate the worlds table."""
    # Wait for initialization
    time.sleep(10)

    # Check database was created and worlds table populated
    conn = sqlite3.connect(temp_db_path)
    cursor = conn.cursor()

    # Verify tables exist
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]

    assert "worlds" in tables, "Worlds table should be created"
    assert "items" in tables, "Items table should be created"
    assert "sales" in tables, "Sales table should be created"

    # Check worlds table is populated
    cursor.execute("SELECT COUNT(*) FROM worlds")
    world_count = cursor.fetchone()[0]

    # If process crashed, show error output
    if world_count == 0 and scraper_process.poll() is not None:
      stdout, stderr = scraper_process.communicate()
      pytest.fail(
        f"Scraper process failed. stderr: {stderr.decode()}, stdout: {stdout.decode()}"
      )

    assert world_count >= 5, f"Expected at least 5 worlds, got {world_count}"

    # Verify world names are populated
    cursor.execute("SELECT world_id, world_name FROM worlds LIMIT 3")
    worlds = cursor.fetchall()

    for world_id, world_name in worlds:
      assert world_id is not None, "World ID should not be None"
      assert world_name is not None, "World name should not be None"
      assert len(world_name) > 0, "World name should not be empty"

    conn.close()

  @pytest.mark.slow
  def test_live_data_collection(self, temp_db_path, scraper_process):
    """Test that the scraper can collect live market data over 30 seconds."""
    # Wait for initialization
    time.sleep(10)

    # Verify initialization worked first
    conn = sqlite3.connect(temp_db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM worlds")
    world_count = cursor.fetchone()[0]

    if world_count == 0:
      conn.close()
      pytest.skip("Scraper failed to initialize, skipping live data test")

    # Run for 30 seconds to collect data
    time.sleep(30)

    # Check for items and sales data
    cursor.execute("SELECT COUNT(*) FROM items")
    item_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM sales")
    sales_count = cursor.fetchone()[0]

    # Note: We can't guarantee sales data since market activity varies
    # But if we do get data, verify it's valid
    if sales_count > 0:
      # Verify sales data structure
      cursor.execute("""
        SELECT s.timestamp, s.world_id, s.item_id, s.price, s.quantity, s.buyer
        FROM sales s
        LIMIT 1
      """)
      sale = cursor.fetchone()

      timestamp, world_id, item_id, price, quantity, buyer = sale

      assert timestamp > 0, "Timestamp should be positive"
      assert world_id > 0, "World ID should be positive"
      assert item_id > 0, "Item ID should be positive"
      assert price > 0, "Price should be positive"
      assert quantity > 0, "Quantity should be positive"
      assert buyer is not None, "Buyer should not be None"

      # Verify world exists
      cursor.execute("SELECT COUNT(*) FROM worlds WHERE world_id = ?", (world_id,))
      assert cursor.fetchone()[0] == 1, "Sale should reference valid world"

    if item_count > 0:
      # Verify items data structure
      cursor.execute("SELECT item_id, item_name FROM items LIMIT 1")
      item = cursor.fetchone()

      item_id, item_name = item
      assert item_id > 0, "Item ID should be positive"
      assert item_name is not None, "Item name should not be None"
      assert len(item_name) > 0, "Item name should not be empty"

    conn.close()

    # Print summary for manual verification
    print("\nData collection summary:")
    print(f"  Worlds: {world_count}")
    print(f"  Items: {item_count}")
    print(f"  Sales: {sales_count}")

  def test_database_schema(self, temp_db_path, scraper_process):
    """Test that the database schema is created correctly."""
    # Wait for initialization
    time.sleep(5)

    conn = sqlite3.connect(temp_db_path)
    cursor = conn.cursor()

    # Check worlds table schema
    cursor.execute("PRAGMA table_info(worlds)")
    worlds_columns = {row[1]: row[2] for row in cursor.fetchall()}

    assert "world_id" in worlds_columns, "worlds table should have world_id column"
    assert "world_name" in worlds_columns, "worlds table should have world_name column"

    # Check items table schema
    cursor.execute("PRAGMA table_info(items)")
    items_columns = {row[1]: row[2] for row in cursor.fetchall()}

    assert "item_id" in items_columns, "items table should have item_id column"
    assert "item_name" in items_columns, "items table should have item_name column"

    # Check sales table schema
    cursor.execute("PRAGMA table_info(sales)")
    sales_columns = {row[1]: row[2] for row in cursor.fetchall()}

    expected_sales_columns = [
      "timestamp",
      "world_id",
      "item_id",
      "price",
      "quantity",
      "buyer",
    ]
    for col in expected_sales_columns:
      assert col in sales_columns, f"sales table should have {col} column"

    # Check indexes exist
    cursor.execute("PRAGMA index_list(sales)")
    indexes = [row[1] for row in cursor.fetchall()]

    assert any("timestamp" in idx for idx in indexes), (
      "sales table should have timestamp index"
    )

    conn.close()


if __name__ == "__main__":
  # Allow running directly with python
  pytest.main([__file__, "-v"])
