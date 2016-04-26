#!/usr/bin/python3
from autobahn.twisted.websocket import WebSocketServerFactory, WebSocketServerProtocol, listenWS
import bson
import cgi
import cherrypy
import flowboard_auth
import flowboard_posts
import json
import os
import os.path
import pymongo
import pystache
import sys
import threading
from twisted.internet import reactor, ssl
from twisted.python import log

"""
Router for all endpoints. All ReST API endpoints return JSON.
"""
class FlowBoard:
  def __init__(self):
    client = pymongo.MongoClient()
    self.auth_db = flowboard_auth.AuthDatabase(client)
    self.auth_service = flowboard_auth.AuthService(self.auth_db)
    self.posts_db = flowboard_posts.PostDatabase(client)
    FlowBoard.instance = self
    self.secret = "6LekGR4TAAAAADn4OR-Gr8pYqdpIJiv79re8fy24"
    self.index_parsed = pystache.parse(''.join(open('index.html').readlines()))
    self.renderer = pystache.Renderer()
    self.recent_posts_html = self.most_recent_posts_html(10)
    self.notify_update()

  @staticmethod
  def create_post_html(post_id, title, author, message, n_replies):
    replies_str = "reply" if not n_replies else "%s replies" % n_replies
    return """<article id='%s'>
    <div class='top-bar'>
      <span class='title' title=''>%s</span><span class='author'>%s</span>
    </div>
      <p><span>%s</span></p>
    <div class='bottom-bar'><a class="reply" href='javascript:void(0)' data-reply-id='%s'>%s</a></div>
  </article>""" % (post_id, title, author, message, post_id, replies_str)

  def most_recent_posts_html(self, limit):
    posts = self.posts_db.recent_posts(limit)
    posts_html = ''.join([FlowBoard.create_post_html(post["_id"], post["title"], 
      self.auth_db.find_user_by_id(post["author_id"])["name"],
      post["message"], len(post["replies"])) for post in posts])
    return posts_html

  def notify_update(self):
    self.recent_posts_html = self.most_recent_posts_html(10)
    self.original_index = self.renderer.render(self.index_parsed, {"posts": self.recent_posts_html})

  """
  / endpoint
  """
  @cherrypy.expose
  def index(self):
    try:
      print(cherrypy.request.cookie.keys())
      ssid = cherrypy.request.cookie['ssid'].value
      response = self.login(session_id=ssid)
      if response['success']:
        username = self.auth_db.find_user_by_ssid(ssid)["name"]
        return self.renderer.render(self.index_parsed, {"authorized": True, "posts": self.recent_posts_html,
          "authorized_welcome": ''.join(["<span id='welcome-box'>Welcome, <strong>", cgi.escape(username), "</strong></span>"])})
      return self.original_index
    except KeyError:
      return self.original_index

  """
  /post endpoint
  """
  @cherrypy.expose
  @cherrypy.tools.json_out()
  def post(self, title, message, session_id=None):
    if not session_id:
      try:
        ssid_cookie = cherrypy.request.cookie['ssid']
      except KeyError:
        return {"success": False}
      session_id = ssid_cookie.value
    user = self.auth_db.find_user_by_ssid(session_id)
    if not user:
      return {"success": False}
    post_id = self.posts_db.create_post(title, message, user["_id"])
    if not post_id:
      return {"success": False}
    flowboard_posts.notify_new_post({"title": cgi.escape(title.strip()), "message": cgi.escape(message.strip()), "author": cgi.escape(user["name"]), "post_id": str(post_id), "n_replies": 0})
    self.notify_update()
    return {"success": True}

  """
  /reply endpoint
  """
  @cherrypy.expose
  @cherrypy.tools.json_out()
  def reply(self, post_id, message, session_id):
    user = self.auth_db.find_user_by_ssid(session_id)
    if not user:
      return {"success": False}
    if not self.posts_db.create_reply(bson.ObjectId(post_id), user["_id"], message):
      return {"success": False}
    flowboard_posts.notify_new_post({"post_id": post_id, "author": cgi.escape(user["name"]), "message": cgi.escape(message)}, reply=True)
    return {"success": True}

  """
  /register endpoint
    @param user the username to register. It MUST be at least 2 printable characters long, trailing and leading whitespace excepted.
    @param password the password to use. It MUST be at least 10 characters long with an alphabet of upper, lower, and numeric characters.
    @param email the email to use

  Accepted methods: GET, POST
  """
  @cherrypy.expose
  @cherrypy.tools.json_out()
  def register(self, user, password, email, recaptcha_response, ip="127.0.0.1"):
    if not flowboard_auth.recaptcha_valid(self.secret, recaptcha_response, ip):
      return {'success': False, 'captcha_valid': 0}
    form = flowboard_auth.AuthService.FormData(user, password, email)
    return self.auth_service.register(form)

  @cherrypy.expose
  @cherrypy.tools.json_out()
  def login(self, user=None, password=None, session_id=None):
    response = self.auth_service.login(user, password, session_id)
    if response['success'] and not session_id:
      cherrypy.response.cookie['ssid'] = response['session_id']
      cherrypy.response.cookie['ssid']['path'] = "/"
      cherrypy.response.cookie['ssid']['max-age'] = 600000
      cherrypy.response.cookie['ssid']['version'] = 1
    elif response['success'] and session_id:
      cherrypy.response.cookie['ssid'] = session_id
      cherrypy.response.cookie['ssid']['max-age'] = 600000
    return response

class FlowBoardProtocol(WebSocketServerProtocol):
  NEW_USER_REQUEST = 0
  LOGIN_BY_NAME_REQUEST = 1
  SUBSCRIBE_REQUEST = 2
  NEW_POST_REQUEST = 3
  NEW_REPLY_REQUEST = 4
  SUBSCRIBE_REPLY_REQUEST = 5
  def onConnect(self, request):
    self.subscribed = False
    self.ip = request.peer.split(":")[1]

  def onMessage(self, payload, isBinary):
    json_request = json.loads(payload.decode("utf8"))
    req_type = json_request['req_type']
    json_response = ""
    if req_type == FlowBoardProtocol.NEW_USER_REQUEST:
      json_response = FlowBoard.instance.register(json_request['user'], json_request['password'], json_request['email'], json_request['recaptcha_response'], self.ip)
    elif req_type == FlowBoardProtocol.LOGIN_BY_NAME_REQUEST:
      json_response = FlowBoard.instance.login(user=json_request['user'], password=json_request['password'])
    elif req_type == FlowBoardProtocol.SUBSCRIBE_REQUEST:
      flowboard_posts.subscribe_client(self)
      self.subscribed = True
    elif req_type == FlowBoardProtocol.SUBSCRIBE_REPLY_REQUEST:
      flowboard_posts.subscribe_reply_client(self, json_request['post_id'])
      self.subscribed = True
    elif req_type == FlowBoardProtocol.NEW_POST_REQUEST:
      json_response = FlowBoard.instance.post(json_request['title'], json_request['message'], json_request['ssid'])
    elif req_type == FlowBoardProtocol.NEW_REPLY_REQUEST:
      json_response = FlowBoard.instance.reply(json_request['post_id'], json_request['message'], json_request['ssid'])
    else:
      self.sendClose()
    self.sendMessage(json.dumps(json_response).encode())

  def onClose(self, wasClean, code, reason):
    if self.subscribed:
      flowboard_posts.unsubscribe_client(self)
      flowboard_posts.unsubscribe_reply_client_all(self)

if __name__ == '__main__':
  '''Websocket server'''
  log.startLogging(sys.stdout)
  ctxt_factory = ssl.DefaultOpenSSLContextFactory('tls/privkey.pem', 'tls/fullchain.pem')
  #ctxt_factory._context.use_certificate_chain_file('tls/fullchain.pem')
  factory = WebSocketServerFactory("wss://192.198.93.218:9001")
  factory.protocol = FlowBoardProtocol
  listenWS(factory, ctxt_factory)

  '''CherryPy server'''
  conf = {
    '/': {
      'tools.staticdir.root': os.path.abspath(os.getcwd())
    },
    '/static': {
      'tools.staticdir.on': True,
      'tools.staticdir.dir': './public'
    }
  }

  cherrypy.server.socket_host = '127.0.0.1'
  th = threading.Thread(target=reactor.run, kwargs={"installSignalHandlers": 0})
  flowboard_posts.start_main_loop()
  th.start()
  cherrypy.quickstart(FlowBoard(), '/', conf)
  th.join()
