#!/usr/bin/env python3
# -*- mode: python -*-

# Python base modules
import datetime
import sqlite3
import os 
import shutil
import urllib
import argparse
import configparser
import hashlib
import json

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
from mako.exceptions import RichTraceback

# Project files
#from globalshock import *
import timepacker

Base = declarative_base()
scriptdir = os.path.abspath(os.curdir)
sqlitedbpath = os.path.join(scriptdir, 'db.sqlite')
filedbpath = os.path.join(scriptdir, 'db.files')
sessionpath = os.path.join(scriptdir,'sessions.cherrypy')
SESSION_KEY='_shocktopodes_session'
templepath = os.path.join(scriptdir, 'temple')
#temple = TemplateLookup(directories=[templepath])

defaultconfigpath = os.path.join(scriptdir, 'config.default')
localconfigpath = os.path.join(scriptdir, 'config.local')
allconfig = configparser.ConfigParser()
allconfig.read([defaultconfigpath, localconfigpath])
config = allconfig['general']
config['rooturl'] = 'http://' + config['url_addr'] + ':' + config['port']

def debugprint(text):
    if config.getboolean('debug'):
        print("DEBUG: " + text)

if config.getboolean('debug'):
    from pdb import set_trace as strace
else:
    def strace(): 
        pass

def sha1hash(data):
    h = hashlib.sha1()
    h.update(data)
    sha1hash = h.hexdigest()
    return sha1hash


class ShockEnc(json.JSONEncoder):
    """JSONEncoder subclass for Shocktopodes data types"""
    def default(self, o):
        if isinstance(o, ShockFile):
            return o.jsonize()
        if isinstance(o, datetime.datetime):
            return timepacker.pack(o)
        else:
            return json.JSONEncoder.default(self, o)
jsonshock=ShockEnc()
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

        try:
            rendered = self.template.render(**env)
        except:
            if config.getboolean('debug'):
                traceback = RichTraceback()
                for (filename, lineno, function, line) in traceback.traceback:
                    print('File {} line #{} function {}'.format(filename, lineno, function))
                    print('    {}'.format(line))
                    #print('{}: {}'.format(traceback.error.__class__.__name__), traceback.error)
            else:
                raise

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
    ctime = Column(DateTime)

    def __init__(self, key):
        Base.__init__(self)
        self.key = key
        self.ctime = datetime.datetime.utcnow()
    def __repr__(self):
        return "<Key({} created {})>".format(self.key, 
                                             self.ctime.strftime(timepacker.fmt_offset))

class ShockFile(Base):
    __tablename__='files'
    id = Column(Integer, primary_key=True)
    filename = Column(String)
    original_filename = Column(String)
    ctime = Column(DateTime)
    content_type = Column(String)
    length = Column(Integer)
    sha1hash = Column(String)
    localpath = Column(String)
    fullurl = Column(String)
    metadataurl = Column(String)
    filext = Column(String)
    jplayertype = Column(String)
    def __init__(self, filename, content_type, length, sha1hash):
        self.filename = self.original_filename = filename
        self.ctime = datetime.datetime.utcnow()
        self.length = length
        # TODO: CherryPy guesses the mime-type based on the filename. Do I have
        #       access to that mapping?
        #       <http://docs.cherrypy.org/stable/progguide/files/static.html>
        #       "using the Python mimetypes module"
        # TODO: Since I'm storing the filext anyway, do I even need this? Probably not...
        self.content_type = content_type
        # TODO: This is kinda dumb. Use the original filename if it had one? 
        #       Is that a good idea? 
        if content_type == 'audio/mp4':
            self.jplayertype = 'm4a'
        elif content_type == 'audio/mp3': # TODO: is this the right mimetype?
            self.jplayertype = 'mp3'
        # elif content_type == 'image/jpeg': 
        #     self.filext = 'jpeg'
        else:
            self.jplayertype = False
        self.sha1hash = sha1hash
        # TODO: do this check first so that instead of uploading the new file it 
        # doesn't accept it
        try:
            os.makedirs(os.path.join(filedbpath, self.sha1hash), mode=0o700, exist_ok=False)
        except FileExistsError:
            pass
        #self.localpath = os.path.join(filedbpath, self.sha1hash+self.filext)
        self.localpath = os.path.join(filedbpath, self.sha1hash, self.filename)
        #self.fullurl = '{}/filedb/{}'.format(config['rooturl'], self.sha1hash+self.filext)
        self.fullurl = '{}/filedb/{}/{}'.format(config['rooturl'], self.sha1hash, self.filename)
        self.metadataurl = '{}/file/{}'.format(config['rooturl'], self.sha1hash)
    def __repr__(self):
        return "<ShockFile({}, a {} of size {})>".format(self.filename, 
                                                         self.content_type,
                                                         self.length)
    def jsonize(self):
        '''Return a dictionary that can be encoded to json'''
        sf = {'sha1hash': self.sha1hash,
              'filename': self.filename,
              'fullurl': self.fullurl,
              'metadataurl': self.metadataurl,
              'ctime': self.ctime,
              'objtype': "ShockFile"}
        return sf

    @classmethod 
    def fromdata(self, filename, content_type, data):
        """
        Create an instance of the ShockFile class from data.

        Pass data directly to this function, and it will create an ORM object
        and also save the data to the filesystem.

        This instantiator also handles computing the hash and the content length.

        Useful because at upload time you have a filename and data but you'd have 
        compute the length and hash every time and I'm lazy so. 
        """
        # TODO: hash the data and don't accept the upload if the data already exists
        h = hashlib.sha1()
        h.update(data)
        sha1hash = h.hexdigest()
        length = len(data)
        sf = ShockFile(filename, content_type, length, sha1hash)

        f = open(sf.localpath, 'bw')
        f.write(data)
        f.close()

        return sf

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
        recentfiles = []
        for sf in cherrypy.request.db.query(ShockFile).order_by(ShockFile.ctime)[0:10]:
            recentfiles += [sf,]
        return {'recentfiles': recentfiles}

    def valid_key(self, key, sessiondb):
        # TODO: honestly is this the best way to search for a key, come on dude
        if sessiondb.query(Key).filter(Key.key.in_([key,])).all():
            return True
        else:
            return False

    @cherrypy.tools.mako(filename='login.mako')
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
        cherrypy.session[SESSION_KEY] = ""
        return "Logout successful"

    @protect()
    @cherrypy.expose
    def shockup(self, myFile=None):
        if not myFile:
            raise cherrypy.HTTPRedirect('/')

        data = myFile.file.read()

        newfile = ShockFile.fromdata(myFile.filename, myFile.content_type.value, data)
        cherrypy.request.db.add(newfile)

        debugprint('Upload complete! {}'.format(newfile))
        return

    @protect()
    @cherrypy.expose
    def rawfile(self, fileid):
        shockfile = cherrypy.request.db.query(ShockFile).filter_by(id=fileid)[0]
        cherrypy.response.headers['content-type'] = shockfile.content_type
        debugprint("Returning raw file #{} named {} of type {}".format(shockfile.id, 
                                                                       shockfile.filename, 
                                                                       shockfile.content_type))
        raise cherrypy.HTTPRedirect('/filedb'+shockfile.sha1hash)

    @protect()
    @cherrypy.tools.mako(filename='file.mako')
    @cherrypy.expose 
    def fileid(self, fileid):
        shockfile = cherrypy.request.db.query(ShockFile).filter_by(id=fileid)[0]
        debugprint(shockfile.__repr__())
        return {'shockfile':shockfile}

    @protect()
    @cherrypy.tools.mako(filename='file.mako')
    @cherrypy.expose 
    def file(self, sha1hash):
        shockfile = cherrypy.request.db.query(ShockFile).filter_by(sha1hash=sha1hash)[0]
        debugprint(shockfile.__repr__())
        return {'shockfile':shockfile}

    @protect()
    @cherrypy.expose
    def recentfiles(self, sincefile=None):
        rf = cherrypy.request.db.query(ShockFile).order_by(ShockFile.ctime)[0:10]
        return jsonshock.encode(rf)
        

        
def reinit():

    try:
        shutil.rmtree(sessionpath)
    except OSError:
        pass # in case it doesn't exist
    os.makedirs(sessionpath, mode=0o700, exist_ok=True)
    try:
        os.remove(sqlitedbpath)
    except OSError:
        pass # in case it doesn't exist
    try:
        shutil.rmtree(filedbpath)
    except OSError:
        pass
    os.makedirs(filedbpath, mode=0o700, exist_ok=True)

    engine = create_engine('sqlite:///%s' % sqlitedbpath, echo=True)
    Base.metadata.create_all(engine)

    S = sessionmaker(bind=engine)
    sess = S()
    sess.add(Key('yellowrock'))

    rf = open(os.path.join(scriptdir, 'static', 'frogsmile.jpg'), 'br')
    data = rf.read()
    rf.close()
    sha1 = sha1hash(data)
    eximage = ShockFile('frogsmile.jpg', 'image/jpeg', len(data), sha1)
    wf = open(eximage.localpath, 'bw')
    wf.write(data)
    wf.close()

    rf = open(os.path.join(scriptdir, 'static', 'predclick.m4a'), 'br')
    data = rf.read()
    rf.close()
    sha1 = sha1hash(data)
    exaudio = ShockFile('predclick.m4a', 'audio/mp4', len(data), sha1)
    wf = open(exaudio.localpath, 'bw')
    wf.write(data)
    wf.close()
    
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


    cherrypy.config.update({'server.socket_port' : int(config['port']),
                            'server.socket_host' : config['bind_addr'],
                            }) 
    cherrypy_root_config = {
        '/' : {
            'tools.db.on': True, 
            'tools.shockauth.on': True,

            'tools.sessions.on': True,
            'tools.sessions.name': 'shocktopodes',
            'tools.sessions.storage_type': 'file',
            'tools.sessions.storage_path': sessionpath, 
            'tools.sessions.timeout': 525600, # ~1 year in minutes
            
            'tools.staticdir.root': scriptdir, 

            # TODO: no idea what collection_size is for
            'tools.mako.collection_size': 500,
            'tools.mako.directories': templepath,

            },
        '/static' : {
            'tools.staticdir.on': True,
            'tools.staticdir.dir': 'static',
            },
        # TODO: this means the directory isn't password protected oops
        '/filedb' : {
            'tools.staticdir.on': True,
            'tools.staticdir.dir': 'db.files',
            'tools.staticdir.content_types': {'m4a': 'audio/mp4'},
            },
        }
    
    cherrypy.tree.mount(ShockRoot(), '/', cherrypy_root_config)

    #cherrypy.server.start()
    cherrypy.engine.start()
    cherrypy.engine.block()

    
