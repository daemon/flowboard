#!/usr/bin/python3
from autobahn.twisted.websocket import WebSocketServerFactory, WebSocketServerProtocol, listenWS
import cgi
import cherrypy
import flowboard_auth
import json
import os
import os.path
import pymongo
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
    self.auth_service = flowboard_auth.AuthService(flowboard_auth.AuthDatabase(client))
    FlowBoard.instance = self

  """
  / endpoint
  """
  @cherrypy.expose
  def index(self):
    return open('index.html')

  """
  /register endpoint
    @param user the username to register. It MUST be at least 2 printable characters long, trailing and leading whitespace excepted.
    @param password the password to use. It MUST be at least 10 characters long with an alphabet of upper, lower, and numeric characters.
    @param email the email to use

  Accepted methods: GET, POST
  """
  @cherrypy.expose
  @cherrypy.tools.json_out()
  def register(self, user, password, email):
    form = flowboard_auth.AuthService.FormData(user, password, email)
    return self.auth_service.register(form)

class FlowBoardProtocol(WebSocketServerProtocol):
  def onMessage(self, payload, isBinary):
    json_request = json.loads(payload.decode("utf8"))
    json_response = FlowBoard.instance.register(json_request['user'], json_request['password'], json_request['email'])
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
      'tools.sessions.on': True,
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
