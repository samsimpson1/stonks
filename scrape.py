import logging
import signal
import sys
import os
from requests import get
import websocket
from bson import encode, decode
from database import StonksDatabase

logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

DC = "Light"
db = None
WORLDS = {}
ws = None


def find_world_in_list(worlds, id):
  for world in worlds:
    if world["id"] == id:
      return world["name"]


def get_worlds():
  dc_worlds = []
  dc_list = get("https://universalis.app/api/v2/data-centers").json()

  for dc in dc_list:
    if dc["name"] == DC:
      dc_worlds = dc["worlds"]

  if len(dc_worlds) < 1:
    logger.error("No worlds found in DC '%s'", DC)
    exit(1)

  logger.info("Got %i worlds in %s DC", len(dc_worlds), DC)

  world_list = get("https://universalis.app/api/v2/worlds").json()

  worlds = {}

  for world in dc_worlds:
    worlds[world] = find_world_in_list(world_list, world)
    db.insert_world(world, worlds[world])

  return worlds


def process_sale(item_id, world_id, sale):
  timestamp = sale["timestamp"]
  price = sale["pricePerUnit"]
  quantity = sale["quantity"]
  buyer = sale["buyerName"]
  logger.debug("process_sale world_id %i item_id %i", world_id, item_id)
  world_name = WORLDS[world_id]
  db.store_item_name(item_id)

  if db.insert_sale(timestamp, world_id, item_id, price, quantity, buyer):
    logger.info("world id %i world name %s", world_id, world_name)


def subscribe_to_worlds(ws):
  for world in WORLDS:
    logger.debug("subscribing to %i", world)
    ws.send(encode({"event": "subscribe", "channel": f"sales/add{{world={world}}}"}))


def on_message(ws, message):
  sales = decode(message)
  item_id = sales["item"]
  world_id = sales["world"]
  for sale in sales["sales"]:
    process_sale(item_id, world_id, sale)


def on_error(ws, error):
  logger.error(error)


def start_websocket_connection():
  ws = websocket.WebSocketApp(
    "wss://universalis.app/api/ws",
    on_open=subscribe_to_worlds,
    on_message=on_message,
    on_error=on_error,
  )
  return ws


def graceful_shutdown(signum, frame):
  logger.info("Received signal %d, shutting down gracefully...", signum)

  if ws:
    logger.info("Closing WebSocket connection...")
    ws.close()

  if db:
    db.close()

  logger.info("Shutdown complete")
  sys.exit(0)


def main(db_path=None):
  global db, WORLDS, ws
  
  if db_path is None:
    db_path = os.getenv("DB_PATH", "/data/stonks.db")
  
  db = StonksDatabase(db_path)
  
  signal.signal(signal.SIGINT, graceful_shutdown)
  signal.signal(signal.SIGTERM, graceful_shutdown)

  WORLDS = get_worlds()

  ws = start_websocket_connection()

  try:
    ws.run_forever()
  except KeyboardInterrupt:
    graceful_shutdown(signal.SIGINT, None)


if __name__ == "__main__":
  main()
