import datetime
import json
import threading

clients = set()
post_queue = []
post_queue_not_empty = threading.Condition()
response_new_thread = 0

def subscribe_client(client):
  global clients
  clients.add(client)

def unsubscribe_client(client):
  global clients
  try:
    clients.remove(client)
  except KeyError:
    pass

def notify_new_post(post):
  global post_queue
  global post_queue_not_empty
  post_queue_not_empty.acquire()
  try:
    post_queue.append(post)
    post_queue_not_empty.notify()
  finally:
    post_queue_not_empty.release()

def main_loop():
  global post_queue_not_empty
  global clients
  global post_queue  
  post_queue_not_empty.acquire()
  try:
    while True:
      while not post_queue:
        post_queue_not_empty.wait()
      for post in post_queue:
        post["post_type"] = response_new_thread
        for client in clients:
          client.sendMessage(json.dumps(post).encode())
      post_queue = []
  finally:
    post_queue_not_empty.release()

def start_main_loop():
  threading.Thread(target=main_loop).start()

class PostDatabase:
  def __init__(self, client):
    self.posts = client.db.posts;
    try:
      self.posts.create_index("creation_date", expireAfterSeconds=2000000)
    except:
      raise Exception("Can't create indices")

  def create_post(self, title, message, author_id):
    return self.posts.insert_one({"author_id": author_id, "title": title, "message": message, 
      "creation_date": datetime.datetime.utcnow(), "replies": []}).inserted_id