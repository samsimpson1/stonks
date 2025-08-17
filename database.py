import logging
from sqlite3 import connect
from time import time
from requests import get

logger = logging.getLogger(__name__)


class StonksDatabase:
  def __init__(self, db_path="/data/stonks.db"):
    self.db_path = db_path
    self.connection = connect(db_path)
    self.item_cache = {}
    self.setup_tables()

  def setup_tables(self):
    cur = self.connection.cursor()
    cur.execute(
      "CREATE TABLE IF NOT EXISTS items (item_id INT PRIMARY KEY, item_name TEXT)"
    )
    cur.execute(
      "CREATE TABLE IF NOT EXISTS worlds (world_id INT PRIMARY KEY, world_name TEXT)"
    )
    cur.execute(
      "CREATE TABLE IF NOT EXISTS sales (timestamp INT, world_id INT, item_id INT, price INT, quantity INT, buyer TEXT, PRIMARY KEY (timestamp, item_id, price))"
    )
    cur.execute("CREATE INDEX IF NOT EXISTS idx_sales_timestamp ON sales (timestamp)")
    cur.execute(
      "CREATE INDEX IF NOT EXISTS idx_sales_buyer_timestamp ON sales (buyer, timestamp)"
    )
    self.connection.commit()

  def insert_world(self, world_id, world_name):
    cur = self.connection.cursor()
    cur.execute(
      "INSERT INTO worlds (world_id, world_name) VALUES (?, ?) ON CONFLICT DO NOTHING",
      (world_id, world_name),
    )
    self.connection.commit()

  def get_item_name(self, item_id):
    item_id_int = int(item_id)
    cur = self.connection.cursor()
    cur.execute("SELECT item_name FROM items WHERE item_id = ?", (item_id_int,))
    res = cur.fetchone()
    return res[0] if res else None

  def store_item_name(self, item_id):
    logger.debug("start store_item_name")
    item_id_int = int(item_id)

    if item_id_int in self.item_cache and self.item_cache[item_id_int] < (time() + 30):
      return

    self.item_cache[item_id_int] = time()

    if self.get_item_name(item_id_int):
      return

    xivapi_response = get(
      f"https://v2.xivapi.com/api/sheet/Item/{item_id_int}?fields=Name&language=en"
    ).json()

    item_name = None
    if "fields" not in xivapi_response:
      if xivapi_response["code"] == 404:
        logger.info("Item not found in XIVAPI data: %s", item_id)
        item_name = "Unknown Item %s" % item_id
      else:
        logger.error("fields not present in xivapi response for ID: %s", item_id)
        return
    else:
      item_name = xivapi_response["fields"]["Name"]

    cur = self.connection.cursor()
    cur.execute(
      "INSERT INTO items (item_id, item_name) VALUES (?, ?)",
      (item_id_int, item_name),
    )
    self.connection.commit()

  def insert_sale(self, timestamp, world_id, item_id, price, quantity, buyer):
    time_last_week = time() - (60 * 60 * 24 * 7)
    if timestamp < time_last_week:
      logger.debug(
        "item sale timestamp too old: item_id %s timestamp %s", item_id, timestamp
      )
      return False

    cur = self.connection.cursor()
    cur.execute(
      "INSERT INTO sales (timestamp, world_id, item_id, price, quantity, buyer) VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT DO NOTHING",
      (timestamp, world_id, item_id, price, quantity, buyer),
    )
    self.connection.commit()
    return True

  def close(self):
    if self.connection:
      logger.info("Closing database connection...")
      self.connection.close()
