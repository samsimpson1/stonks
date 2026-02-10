import logging
from sqlite3 import connect
from time import time
from requests import get
from prometheus_client import Counter, Gauge, Histogram

logger = logging.getLogger(__name__)

db_insert_duration = Histogram(
  "stonks_db_insert_duration_seconds",
  "Time to insert a sale row including commit",
)
db_commit_duration = Histogram(
  "stonks_db_commit_duration_seconds",
  "Time for SQLite commit calls",
)
db_item_lookup_duration = Histogram(
  "stonks_db_item_lookup_duration_seconds",
  "Time for item name DB lookups",
)
sales_inserted = Counter(
  "stonks_sales_inserted_total",
  "Sales successfully written to DB",
)
sales_skipped = Counter(
  "stonks_sales_skipped_total",
  "Sales skipped",
  ["reason"],
)
xivapi_request_duration = Histogram(
  "stonks_xivapi_request_duration_seconds",
  "Time for XIVAPI item name HTTP lookups",
)
xivapi_requests = Counter(
  "stonks_xivapi_requests_total",
  "XIVAPI requests made",
  ["status"],
)
item_cache_size = Gauge(
  "stonks_item_cache_size",
  "Number of entries in the item name cache",
)
item_cache_hits = Counter(
  "stonks_item_cache_hits_total",
  "Item cache hits that avoided a DB/API call",
)


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
    with db_item_lookup_duration.time():
      cur.execute("SELECT item_name FROM items WHERE item_id = ?", (item_id_int,))
      res = cur.fetchone()
    return res[0] if res else None

  def store_item_name(self, item_id):
    logger.debug("start store_item_name")
    item_id_int = int(item_id)

    if item_id_int in self.item_cache and self.item_cache[item_id_int] < (time() + 30):
      item_cache_hits.inc()
      return

    self.item_cache[item_id_int] = time()
    item_cache_size.set(len(self.item_cache))

    if self.get_item_name(item_id_int):
      return

    with xivapi_request_duration.time():
      xivapi_response = get(
        f"https://v2.xivapi.com/api/sheet/Item/{item_id_int}?fields=Name&language=en"
      ).json()

    item_name = None
    if "fields" not in xivapi_response:
      if xivapi_response["code"] == 404:
        logger.info("Item not found in XIVAPI data: %s", item_id)
        item_name = "Unknown Item %s" % item_id
        xivapi_requests.labels(status="not_found").inc()
      else:
        logger.error("fields not present in xivapi response for ID: %s", item_id)
        xivapi_requests.labels(status="error").inc()
        return
    else:
      item_name = xivapi_response["fields"]["Name"]
      xivapi_requests.labels(status="success").inc()

    cur = self.connection.cursor()
    cur.execute(
      "INSERT INTO items (item_id, item_name) VALUES (?, ?)",
      (item_id_int, item_name),
    )
    start = time()
    self.connection.commit()
    db_commit_duration.observe(time() - start)

  def insert_sale(self, timestamp, world_id, item_id, price, quantity, buyer):
    time_last_week = time() - (60 * 60 * 24 * 7)
    if timestamp < time_last_week:
      logger.debug(
        "item sale timestamp too old: item_id %s timestamp %s", item_id, timestamp
      )
      sales_skipped.labels(reason="too_old").inc()
      return False

    with db_insert_duration.time():
      cur = self.connection.cursor()
      cur.execute(
        "INSERT INTO sales (timestamp, world_id, item_id, price, quantity, buyer) VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT DO NOTHING",
        (timestamp, world_id, item_id, price, quantity, buyer),
      )
      start = time()
      self.connection.commit()
      db_commit_duration.observe(time() - start)

    if cur.rowcount > 0:
      sales_inserted.inc()
    else:
      sales_skipped.labels(reason="duplicate").inc()

    return cur.rowcount > 0

  def close(self):
    if self.connection:
      logger.info("Closing database connection...")
      self.connection.close()
