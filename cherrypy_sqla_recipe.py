# -*- coding: utf-8 -*-
# from: http://www.defuze.org/archives/222-integrating-sqlalchemy-into-a-cherrypy-application.html
import os, os.path
 
import cherrypy
from cherrypy.process import wspbus, plugins
 
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column
from sqlalchemy.types import String, Integer
 
# Helper to map and register a Python class a db table
Base = declarative_base()
 
class Message(Base):
    __tablename__ = 'message'
    id = Column(Integer, primary_key=True)
    value =  Column(String)
 
    def __init__(self, message):
        Base.__init__(self)
        self.value = message
 
    def __str__(self):
        return self.value.encode('utf-8')
 
    def __unicode__(self):
        return self.value
 
    @staticmethod
    def list(session):
        return session.query(Message).all()
 
 
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
        db_path = os.path.abspath(os.path.join(os.curdir, 'my.db'))
        self.sa_engine = create_engine('sqlite:///%s' % db_path, echo=True)
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
 
 
 
 
class Root(object):
    @cherrypy.expose
    def index(self):
        # print all the recorded messages so far
        msgs = [str(msg) for msg in Message.list(cherrypy.request.db)]
        cherrypy.response.headers['content-type'] = 'text/plain'
        return "Here are your list of messages: %s" % '\n'.join(msgs)
 
    @cherrypy.expose
    def record(self, msg):
        # go to /record?msg=hello world to record a "hello world" message
        m = Message(msg)
        cherrypy.request.db.add(m)
        cherrypy.response.headers['content-type'] = 'text/plain'
        return "Recorded: %s" % m
 
if __name__ == '__main__':
    SAEnginePlugin(cherrypy.engine).subscribe()
    cherrypy.tools.db = SATool()
    cherrypy.tree.mount(Root(), '/', {'/': {'tools.db.on': True}})
    cherrypy.engine.start()
    cherrypy.engine.block()
