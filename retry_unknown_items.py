from sqlite3 import connect
from scrape import store_item_name

files = open("/data/item_ids.txt", "r").readlines()

if __name__ == "__main__":
  db = connect("stonks.db")
  for line in files:
    item_id = line.strip()
    store_item_name(item_id)
