#!/usr/bin/env python3
# -*- mode: python -*-

# Python base modules
import datetime
import sqlite3

# Manual installation requried for these
import cherrypy 
from cherrypy.process import wspbus, plugins

#import psycopg2
#import psycopg2.extras

import sqlalchemy
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column
from sqlalchemy.types import String, Integer
Base = declarative_base()


sqlitedbpath = '/var/www/shocktopodes/shocktopodes.sqlite'
SESSION_KEY='_shock_key'

SHOCK_DEBUG=True
def debugprint(text):
    if SHOCK_DEBUG:
        print(text)

class SAEnginePlugin(plugins.SimplePlugin):
    def __init__(self, bus):
        """
        The plugin is registered to the CherryPy engine and therefore
        is part of the bus (the engine *is* a bus) registery.
 
        We use this plugin to create the SA engine. At the same time,
        when the plugin starts we create the tables into the database
        using the mapped class of the global metadata.
 
        Finally we create a new 'bind' channel that the SA tool
        will use to map a session to the SA engine at request time.
        """
        plugins.SimplePlugin.__init__(self, bus)
        self.sa_engine = None
        self.bus.subscribe("bind", self.bind)
 
    def start(self):
        self.sa_engine = create_engine('sqlite:///%s' % sqlitedbpath, echo=True)
        Base.metadata.create_all(self.sa_engine)
 
    def stop(self):
        if self.sa_engine:
            self.sa_engine.dispose()
            self.sa_engine = None
 
    def bind(self, session):
        session.configure(bind=self.sa_engine)
 
class SATool(cherrypy.Tool):
    def __init__(self):
        """
        The SA tool is responsible for associating a SA session
        to the SA engine and attaching it to the current request.
        Since we are running in a multithreaded application,
        we use the scoped_session that will create a session
        on a per thread basis so that you don't worry about
        concurrency on the session object itself.
 
        This tools binds a session to the engine each time
        a requests starts and commits/rollbacks whenever
        the request terminates.
        """
        cherrypy.Tool.__init__(self, 'on_start_resource',
                               self.bind_session,
                               priority=20)
 
        self.session = scoped_session(sessionmaker(autoflush=True,
                                                  autocommit=False))
 
    def _setup(self):
        cherrypy.Tool._setup(self)
        cherrypy.request.hooks.attach('on_end_resource',
                                      self.commit_transaction,
                                      priority=80)
 
    def bind_session(self):
        cherrypy.engine.publish('bind', self.session)
        cherrypy.request.db = self.session
 
    def commit_transaction(self):
        cherrypy.request.db = None
        try:
            self.session.commit()
        except:
            self.session.rollback()  
            raise
        finally:
            self.session.remove()

class Key(Base):
    __tablename__='keys'
    id = Column(Integer, primary_key=True)
    key = Column(String)

    def __init__(self, key):
        Base.__init__(self)
        self.key = key
    def __repr__(self):
        return "<Key({})>".format(self.key)

class ShockRoot:
    @cherrypy.expose
    def index(self, key=None):
        # First, check to see if there is a key passed via URL. If there is & 
        # it's valid, make a session out of it and continue to the protected
        # page. 
        # If there isn't, see if there was already a valid session from a 
        # previous login. If so, use it. 
        # If neither is true, return the login page. 

        authenticated=False
        if key:
            if self.valid_key(key, cherrypy.request.db):
                cherrypy.session.regenerate()
                cherrypy.session[SESSION_KEY] = key
                authenticated=True
        else:
            try:
                # now try to see if there was a valid session from before
                this_session = cherrypy.session[SESSION_KEY]
                cherrypy.session.regenerate()
                authenticated=True
            except KeyError:
                pass

        if authenticated:
            return """
            <html><body>
                <h2>Upload a file</h2>
                <script src="./static/dropzone/dropzone.js"></script>
                <script>
                Dropzone.options.shockzone = {
                    paramName: "myFile",
                };
                </script>
                <form action="/shockup"
                      class="dropzone"
                      id="shockzone"></form>
            </body></html>
            """
        else:
            return self.generate_loginform()

    @cherrypy.expose
    def bullshit(self):
        cherrypy.request.db.add(Key('yellowrock'))
        return "lol ok" 

    def valid_key(self, key, session):
        if session.query(Key).filter(Key.key.in_([key,])).all():
            return True
        else:
            return False

    def generate_loginform(self):
        return """<html><body><h2>Enter secret key</h2>
            <form method="post" action="/">
            Secret key: <input type="text" name="key" />
            <input type="submit" value="Submit" />
            </body></html>"""

    @cherrypy.expose
    def shockup(self, myFile):
        out = """<html>
        <body>
            myFile length: %s<br />
            myFile filename: %s<br />
            myFile mime-type: %s
        </body>
        </html>"""

        tmppath = '/tmp/tmpshock'
        tmpfile = open(tmppath, 'bw')
        tmpfile.write(myFile.file.read())
        tmpfile.close()

        # Although this just counts the file length, it demonstrates
        # how to read large files in chunks instead of all at once.
        # CherryPy reads the uploaded file into a temporary file;
        # myFile.file.read reads from that.
        size = 0
        while True:
            data = myFile.file.read(8192)
            if not data:
                break
            size += len(data)

        return out % (size, myFile.filename, myFile.content_type)


if __name__=='__main__':

    SAEnginePlugin(cherrypy.engine).subscribe()
    cherrypy.tools.db = SATool()

    cherrypy.config.update({'server.socket_port' : 7979,
                            'server.socket_host' : '0.0.0.0',
                            # TODO: this is for debugging databases with. fix for deployment!
                            'server.thread_pool' : 1}) 
    config_root = {
        '/' : {
            'tools.db.on': True, 
            'tools.sessions.on': True,
            'tools.sessions.name': 'shocktopodes',
            'tools.staticdir.root': '/var/www/shocktopodes',
            },
        '/static' : {
            'tools.staticdir.on': True,
            'tools.staticdir.dir': 'static',
            }
        }
    
    cherrypy.tree.mount(ShockRoot(), '/', config_root)

    #cherrypy.server.start()
    cherrypy.engine.start()
    cherrypy.engine.block()

    


