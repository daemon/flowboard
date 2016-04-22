#!/usr/bin/python3
import cgi
import cherrypy
import flowboard_auth
import os
import os.path
import pymongo

"""
Router for all endpoints. All ReST API endpoints return JSON.
"""
class FlowBoard:
  def __init__(self):
    client = pymongo.MongoClient()
    self.auth_service = flowboard_auth.AuthService(flowboard_auth.AuthDatabase(client))

  """
  / endpoint
  """
  @cherrypy.expose
  def index(self):
    return open('index.html')

  """
  /register endpoint.
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

if __name__ == '__main__':
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
cherrypy.quickstart(FlowBoard(), '/', conf)