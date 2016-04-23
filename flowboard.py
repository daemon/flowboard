#!/usr/bin/python3
from autobahn.twisted.websocket import WebSocketServerFactory, WebSocketServerProtocol, listenWS
import cgi
import cherrypy
import flowboard_auth
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
    FlowBoard.instance = self
    self.secret = "6LekGR4TAAAAADn4OR-Gr8pYqdpIJiv79re8fy24"
    self.index_parsed = pystache.parse(''.join(open('index.html').readlines()))
    self.renderer = pystache.Renderer()
    self.original_index = self.renderer.render(self.index_parsed)

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
        return self.renderer.render(self.index_parsed, {"authorized": True, 
          "authorized_welcome": ''.join(["<span id='welcome-box'>Welcome, <strong>", cgi.escape(username), "</strong></span>"])})
      return self.original_index
    except KeyError:
      return self.original_index

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
  LOGIN_BY_SSID_REQUEST = 2
  def onConnect(self, request):
    self.ip = request.peer.split(":")[1]

  def onMessage(self, payload, isBinary):
    json_request = json.loads(payload.decode("utf8"))
    req_type = json_request['req_type']
    json_response = ""
    if req_type == FlowBoardProtocol.NEW_USER_REQUEST:
      json_response = FlowBoard.instance.register(json_request['user'], json_request['password'], json_request['email'], json_request['recaptcha_response'], self.ip)
    elif req_type == FlowBoardProtocol.LOGIN_BY_NAME_REQUEST:
      json_response = FlowBoard.instance.login(user=json_request['user'], password=json_request['password'])
    else:
      self.sendClose()
    self.sendMessage(json.dumps(json_response).encode())

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
  th.start()
  cherrypy.quickstart(FlowBoard(), '/', conf)
  th.join()
