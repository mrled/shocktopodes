#!/usr/bin/env python3
# -*- mode: python -*-

# Python base modules
import datetime
import sqlite3
import os 
import urllib

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
from sqlalchemy.types import String, Integer, LargeBinary, DateTime
Base = declarative_base()

# Project files
from globalshock import *
#from auth import SESSION_KEY, protect, protect_handler, logout

scriptdir = os.path.abspath(os.curdir)
sqlitedbpath = os.path.join(scriptdir, 'db.shocktopodes.sqlite')
SESSION_KEY='_shocktopodes_session'

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
            #raise cherrypy.HTTPRedirect("/login".format(requested_page))

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
    @protect()
    def index(self):
        return self.generate_uploadform()

    @cherrypy.expose
    def initbullshit(self):
        # TODO: yeah obviously this shouldn't be here
        # I just haven't figured out how to do this with sessions properly yet
        cherrypy.request.db.add(Key('yellowrock'))

        f = open(os.path.join(scriptdir, 'static', 'frogsmile.jpg'), 'br')
        eximage = ShockFile('frogsmile.jpg', f.read(), 'image/jpeg')
        f.close()

        f = open(os.path.join(scriptdir, 'static', 'predclick.m4a'), 'br')
        exaudio = ShockFile('predclick.m4a', f.read(), 'audio/mp4')
        f.close()

        cherrypy.request.db.add(eximage)
        cherrypy.request.db.add(exaudio)

        raise cherrypy.HTTPRedirect('/')

    def valid_key(self, key, session):
        # TODO: honestly is this the best way to search for a key, come on dude
        if session.query(Key).filter(Key.key.in_([key,])).all():
            return True
        else:
            return False

    def generate_uploadform(self):
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

    #def generate_loginform(self, from_page='/'):
        # return """<html><body><h2>Enter secret key</h2>
        #     <form method="post" action="/login/from_page={}">
        #     Secret key: <input type="text" name="key" />
        #     <input type="submit" value="Submit" />
        #     </body></html>""".format(from_page)
    def generate_loginform(self):
        return """<html><body><h2>Enter secret key</h2>
            <form method="post" action="/login">
            Secret key: <input type="text" name="key" />
            <input type="submit" value="Submit" />
            </body></html>"""

    @cherrypy.expose
    def login(self, key=None, from_page='/'):
        debugprint("From page: {}".format(from_page))
        if from_page.startswith("/login"):
            from_page="/"
        if self.valid_key(key, cherrypy.request.db):
            cherrypy.session[SESSION_KEY] = key
            raise cherrypy.HTTPRedirect(from_page)
        else:
            #return self.generate_loginform(from_page=from_page)
            return """<html><body><h2>Enter secret key</h2>
                <form method="post" action="/login?from_page={}">
                Secret key: <input type="text" name="key" />
                <input type="submit" value="Submit" />
                </body></html>""".format(from_page)


    @protect()
    @cherrypy.expose
    def logout():
        this_session = cherrypy.session.get(SESSION_KEY, None)
        cherrypy.session[SESSION_KEY] = None
        return "Logout successful"

    @protect()
    @cherrypy.expose
    def shockup(self, myFile):
        out = """<html>
        <body>
            myFile length: %s<br />
            myFile filename: %s<br />
            myFile mime-type: %s
        </body>
        </html>"""

        #re_images = re.compile('\.(jpg|jpeg|png|tif|tiff|raw|gif|bmp|svg)$')
        #re_audio = re.compile('\.(mp3|m4a)$')

        #if re_images.match(myFile.filename.lower()):

        #if myFile.filename.lower().endswith('.jpg')

        newfile = ShockFile(myFile.filename, myFile.file.read(), myFile.content_type.value)
        cherrypy.request.db.add(newfile)
        debugprint('Upload complete! {}'.format(newfile))

        return out % (newfile.length, myFile.filename, myFile.content_type)

    @protect()
    @cherrypy.expose
    def rawfile(self, fileid):
        f = cherrypy.request.db.query(ShockFile).filter_by(id=fileid)[0]
        cherrypy.response.headers['content-type'] = f.content_type
        debugprint("Returning raw file #{} named {} of type {}".format(f.id, f.filename, f.content_type))
        return f.data

    @protect()
    @cherrypy.expose 
    def file(self, fileid):
        f = cherrypy.request.db.query(ShockFile).filter_by(id=fileid)[0]
        debugprint(f.__repr__())
        html = '<html><head><title>{}</title>'.format(f.filename)
        html+= '<script type="text/javascript" src="http://ajax.googleapis.com/ajax/libs/jquery/1.6/jquery.min.js"></script>'
        html+= '<link type="text/css" href="/static/jplayer-skin/jplayer.blue.monday.css" rel="stylesheet" />'
        html+= '<script type="text/javascript" src="/static/jplayer/jquery.jplayer.min.js"></script>'
        html+= '''
            <script type="text/javascript">
              $(document).ready(function(){
                $("#jquery_jplayer_1").jPlayer({
                  ready: function () {
                    $(this).jPlayer("setMedia", {
            '''
        html+= '''
                      m4a: "http://localhost:7979/rawfile?fileid=%s",
                    });
                  },
                  swfPath: "/static/jplayer",
                  supplied: "m4a"
                });
              });
            </script>
            ''' %fileid
        html+= '<body><h2>File ID: {}; Name: {}</h2>'.format(f.id, f.filename)
        html+= '<p>Type: {}; Length: {}</p>'.format(f.content_type, f.length)
        if f.content_type.startswith('image'):
            html += '<p><img src=/rawfile?fileid={} /></p>'.format(fileid)
        if f.content_type.startswith('audio'):
            html += '''
                <div id="jquery_jplayer_1" class="jp-jplayer"></div>
                <div id="jp_container_1" class="jp-audio">
                  <div class="jp-type-single">
                    <div class="jp-gui jp-interface">
                      <ul class="jp-controls">
                        <li><a href="javascript:;" class="jp-play" tabindex="1">play</a></li>
                        <li><a href="javascript:;" class="jp-pause" tabindex="1">pause</a></li>
                        <li><a href="javascript:;" class="jp-stop" tabindex="1">stop</a></li>
                        <li><a href="javascript:;" class="jp-mute" tabindex="1" title="mute">mute</a></li>
                        <li><a href="javascript:;" class="jp-unmute" tabindex="1" title="unmute">unmute</a></li>
                        <li><a href="javascript:;" class="jp-volume-max" tabindex="1" title="max volume">max volume</a></li>
                      </ul>
                      <div class="jp-progress">
                        <div class="jp-seek-bar">
                          <div class="jp-play-bar"></div>
                        </div>
                      </div>
                      <div class="jp-volume-bar">
                        <div class="jp-volume-bar-value"></div>
                      </div>
                      <div class="jp-time-holder">
                        <div class="jp-current-time"></div>
                        <div class="jp-duration"></div>
                        <ul class="jp-toggles">
                          <li><a href="javascript:;" class="jp-repeat" tabindex="1" title="repeat">repeat</a></li>
                          <li><a href="javascript:;" class="jp-repeat-off" tabindex="1" title="repeat off">repeat off</a></li>
                        </ul>
                      </div>
                    </div>
                    <div class="jp-title">
                      <ul>
                        <li>Bubble</li>
                      </ul>
                    </div>
                    <div class="jp-no-solution">
                      <span>Update Required</span>
                      To play the media you will need to either update your browser to a recent version or update your <a href="http://get.adobe.com/flashplayer/" target="_blank">Flash plugin</a>.
                    </div>
                  </div>
                </div>
              '''

        html+= '</body></html>'
        return html
        
        

if __name__=='__main__':

    SAEnginePlugin(cherrypy.engine).subscribe()
    cherrypy.tools.db = SATool()

    cherrypy.tools.shockauth = cherrypy.Tool('before_handler', protect_handler)

    cherrypy.config.update({'server.socket_port' : 7979,
                            'server.socket_host' : '0.0.0.0',
                            # TODO: this is for debugging databases with. fix for deployment!
                            'server.thread_pool' : 1}) 
    config_root = {
        '/' : {
            'tools.db.on': True, 
            'tools.shockauth.on': True,
            'tools.sessions.on': True,
            'tools.sessions.name': 'shocktopodes',
            'tools.staticdir.root': scriptdir, 
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

    
