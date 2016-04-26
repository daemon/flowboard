import datetime
import json
import threading

clients = set()
topic_to_clients = {}
client_to_topics = {}
reply_queue = []
post_queue = []
queues_not_empty = threading.Condition()
response_new_thread = 0
response_new_reply = 1

def subscribe_reply_client(client, topic_id):
  try:
    client_to_topics[client].add(topic_id)
  except KeyError:
    client_to_topics[client] = set([topic_id])
  try:
    topic_to_clients[topic_id].add(client)
  except KeyError:
    topic_to_clients[topic_id] = set([client])

def unsubscribe_reply_client(client, topic_id):
  try:
    client_to_topics[client].remove(topic_id)
  except:
    pass
  try:
    topic_to_clients[topic_id].remove(client)
  except:
    pass

def unsubscribe_reply_client_all(client):
  try:
    for topic in client_to_topics[client]:
      try:
        topic_to_clients[topic].remove(client)
      except:
        pass
  except KeyError:
    return
  del client_to_topics[client]

def subscribe_client(client):
  global clients
  clients.add(client)

def unsubscribe_client(client):
  global clients
  try:
    clients.remove(client)
  except KeyError:
    pass

def notify_new_post(post, reply=False):
  global post_queue
  global queues_not_empty
  global reply_queue
  queues_not_empty.acquire()
  try:
    reply_queue.append(post) if reply else post_queue.append(post)
    queues_not_empty.notify()
  finally:
    queues_not_empty.release()

def main_loop():
  global queues_not_empty
  global clients
  global post_queue
  global reply_queue
  queues_not_empty.acquire()
  try:
    while True:
      while not post_queue and not reply_queue:
        queues_not_empty.wait()
      for post in post_queue:
        post["post_type"] = response_new_thread
        for client in clients:
          client.sendMessage(json.dumps(post).encode())
      for reply in reply_queue:
        reply["post_type"] = response_new_reply
        try:
          clients = topic_to_clients[reply["post_id"]]
          for client in clients:
            client.sendMessage(json.dumps(reply).encode())
        except KeyError:
          pass
      post_queue = []
      reply_queue = []
  finally:
    queues_not_empty.release()

def start_main_loop():
  threading.Thread(target=main_loop).start()

class PostDatabase:
  def __init__(self, client):
    self.posts = client.db.posts;
    try:
      self.posts.create_index("creation_date", expireAfterSeconds=2000000)
    except:
      raise Exception("Can't create indices")

  def find_post(self, post_id):
    return self.posts.find_one({"_id": post_id})

  def create_reply(self, post_id, author_id, message):
    return self.posts.update({"_id": post_id}, {"$push": {"replies": {"author_id": author_id, "message": message}}})['nModified']

  def recent_posts(self, limit, start=0):
    return self.posts.find().sort([("creation_date", -1)]).limit(limit)

  def create_post(self, title, message, author_id):
    if len(title.strip()) > 0 and len(message.strip()) > 0:
      return self.posts.insert_one({"author_id": author_id, "title": title.strip(), "message": message.strip(),
        "creation_date": datetime.datetime.utcnow(), "replies": []}).inserted_id
    else:
      return None

  #def reply_to_post(self, post_id, reply_message, reply_author_id)