#!/usr/bin/python3
import cherrypy
import os
import os.path

class FlowBoard():
  @cherrypy.expose
  def index(self):
    return open('index.html')

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

cherrypy.server.socket_host = '192.198.93.218'
cherrypy.quickstart(FlowBoard(), '/', conf)