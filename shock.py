#!/usr/bin/env python3
# -*- mode: python -*-

# Python base modules
import datetime
import sqlite3
import os 
import shutil
import urllib
import argparse

# Manual installation requried for these
import cherrypy 
from cherrypy.process import wspbus, plugins

import sqlalchemy
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column
from sqlalchemy.types import String, Integer, LargeBinary, DateTime

from mako.template import Template
from mako.runtime import Context
from mako.lookup import TemplateLookup

# Project files
from globalshock import *

Base = declarative_base()
scriptdir = os.path.abspath(os.curdir)
sqlitedbpath = os.path.join(scriptdir, 'db.shocktopodes.sqlite')
sessionpath = os.path.join(scriptdir,'sessions.cherrypy')
SESSION_KEY='_shocktopodes_session'
templepath = os.path.join(scriptdir, 'temple')
#temple = TemplateLookup(directories=[templepath])

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

class MakoHandler(cherrypy.dispatch.LateParamPageHandler):
    """Callable which sets response.body."""
    def __init__(self, template, next_handler):
        self.template = template
        self.next_handler = next_handler
    def __call__(self):
        env = globals().copy()
        env.update(self.next_handler())
        return self.template.render(**env)


class MakoLoader(object):
    def __init__(self):
        self.lookups = {}
    def __call__(self, filename, directories, module_directory=None,
                 collection_size=-1):
        # Find the appropriate template lookup.
        key = (tuple(directories), module_directory)
        try:
            lookup = self.lookups[key]
        except KeyError:
            lookup = TemplateLookup(directories=directories,
                                    module_directory=module_directory,
                                    collection_size=collection_size)
            self.lookups[key] = lookup
        cherrypy.request.lookup = lookup
        
        # Replace the current handler.
        cherrypy.request.template = t = lookup.get_template(filename)
        cherrypy.request.handler = MakoHandler(t, cherrypy.request.handler)

mloader = MakoLoader()
cherrypy.tools.mako = cherrypy.Tool('on_start_resource', mloader)

class Key(Base):
    __tablename__='keys'
    id = Column(Integer, primary_key=True)
    key = Column(String)
    atime = Column(DateTime)

    def __init__(self, key):
        Base.__init__(self)
        self.key = key
        self.atime = datetime.datetime.utcnow()
    def __repr__(self):
        return "<Key({} created {})>".format(self.key, 
                                             self.atime.strftime(iso8601))

class ShockFile(Base):
    __tablename__='files'
    id = Column(Integer, primary_key=True)
    filename = Column(String)
    original_filename = Column(String)
    data = Column(LargeBinary)
    atime = Column(DateTime)
    content_type = Column(String) # TODO
    length = Column(Integer)
    def __init__(self, filename, data, content_type):
        self.filename = self.original_filename = filename
        self.data = data
        self.atime = datetime.datetime.utcnow()
        self.length = len(data)
        self.content_type = content_type
    def __repr__(self):
        return "<ShockFile({}, a {} of size {})>".format(self.filename, 
                                                         self.content_type,
                                                         self.length)

def protect_handler(*args, **kwargs):
    conditions = cherrypy.request.config.get('auth.require', None)
    if conditions is not None:
        debugprint("Accessing protected URL...")        
        # this is the page the user requested. if they have to log in first, 
        # they'll be redirected there after they do so
        requested_page = urllib.parse.quote(cherrypy.request.request_line.split()[1])
        try:
            # now try to see if there was a valid session from before
            this_session = cherrypy.session[SESSION_KEY]
            cherrypy.session.regenerate()
        except KeyError:
            debugprint("Redirecting to login page...")
            raise cherrypy.HTTPRedirect("/login?from_page={}".format(requested_page))

def protect(*conditions):
    def decorate(f):
        if not hasattr(f, '_cp_config'):
            f._cp_config = dict()
        if 'auth.require' not in f._cp_config:
            f._cp_config['auth.require'] = []
        f._cp_config['auth.require'].extend(conditions)
        return f
    return decorate

class ShockRoot:
    @cherrypy.expose
    @cherrypy.tools.mako(filename='index.mako')
    @protect()
    def index(self):
        return ''

    def valid_key(self, key, session):
        # TODO: honestly is this the best way to search for a key, come on dude
        if session.query(Key).filter(Key.key.in_([key,])).all():
            return True
        else:
            return False

    @cherrypy.tools.mako(filename='file.mako')
    @cherrypy.expose
    def login(self, key=None, from_page='/'):
        debugprint("From page: {}".format(from_page))
        if from_page.startswith("/login") or from_page.startswith("/logout"):
            from_page="/"
        if self.valid_key(key, cherrypy.request.db):
            cherrypy.session[SESSION_KEY] = key
            raise cherrypy.HTTPRedirect(from_page)
        else:
            return {'from_page': from_page}
            
    @protect()
    @cherrypy.expose
    def logout(self):
        # TODO: this only works sometimes for me? 
        this_session = cherrypy.session.get(SESSION_KEY, None)
        cherrypy.session[SESSION_KEY] = None
        return "Logout successful"

    @protect()
    @cherrypy.expose
    def shockup(self, myFile=None):
        if not myFile:
            raise cherrypy.HTTPRedirect('/')

        newfile = ShockFile(myFile.filename, myFile.file.read(), myFile.content_type.value)
        cherrypy.request.db.add(newfile)
        debugprint('Upload complete! {}'.format(newfile))

        return

    @protect()
    @cherrypy.expose
    def rawfile(self, fileid):
        f = cherrypy.request.db.query(ShockFile).filter_by(id=fileid)[0]
        cherrypy.response.headers['content-type'] = f.content_type
        debugprint("Returning raw file #{} named {} of type {}".format(f.id, f.filename, f.content_type))
        return f.data

    @protect()
    @cherrypy.tools.mako(filename='file.mako')
    @cherrypy.expose 
    def file(self, fileid):
        f = cherrypy.request.db.query(ShockFile).filter_by(id=fileid)[0]
        debugprint(f.__repr__())
        return {'file':f}
        
        
def reinit():

    shutil.rmtree(sessionpath)
    os.makedirs(sessionpath, mode=0o700, exist_ok=True)

    os.remove(sqlitedbpath)

    engine = create_engine('sqlite:///%s' % sqlitedbpath, echo=True)
    Base.metadata.create_all(engine)

    S = sessionmaker(bind=engine)
    sess = S()
    sess.add(Key('yellowrock'))

    f = open(os.path.join(scriptdir, 'static', 'frogsmile.jpg'), 'br')
    eximage = ShockFile('frogsmile.jpg', f.read(), 'image/jpeg')
    f.close()

    f = open(os.path.join(scriptdir, 'static', 'predclick.m4a'), 'br')
    exaudio = ShockFile('predclick.m4a', f.read(), 'audio/mp4')
    f.close()

    sess.add(eximage)
    sess.add(exaudio)

    sess.commit()

if __name__=='__main__':

    d = "Run the shocktopodes service."
    argparser = argparse.ArgumentParser(description=d)
    argparser.add_argument("--init", "-i", action='store_true',
                           help="Reinitialize everything. WARNING: DESTROYS ANY EXISTING DATA.")

    args_namespace = argparser.parse_args()
    if args_namespace.init:
        reinit()

    SAEnginePlugin(cherrypy.engine).subscribe()
    cherrypy.tools.db = SATool()

    cherrypy.tools.shockauth = cherrypy.Tool('before_handler', protect_handler)


    cherrypy.config.update({'server.socket_port' : 7979,
                            'server.socket_host' : '0.0.0.0',
                            }) 
    config_root = {
        '/' : {
            'tools.db.on': True, 
            'tools.shockauth.on': True,
            'tools.sessions.on': True,
            'tools.sessions.name': 'shocktopodes',
            'tools.sessions.storage_type': 'file',
            'tools.sessions.storage_path': sessionpath, 
            'tools.sessions.timeout': 525600, # ~1 year in minutes
            
            'tools.staticdir.root': scriptdir, 

            'tools.mako.collection_size': 500,
            'tools.mako.directories': templepath,
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

    
