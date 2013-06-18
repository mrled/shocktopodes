# Note: 
# Much of this originated with: 
# <http://tools.cherrypy.org/wiki/AuthenticationAndAccessRestrictions>
# And then was modified in my zk/auth.py implementation
# And then heavily cut down for use here

# Python3 builtins

# Manual installation
import cherrypy 

# Project files
from globalshock import *

SESSION_KEY='_shocktopodes_session'

def protect_handler(*args, **kwargs):
    conditions = cherrypy.request.config.get('auth.require', None)
    if conditions is not None:
        debugprint("Accessing protected URL...")
        try:
            # now try to see if there was a valid session from before
            this_session = cherrypy.session[SESSION_KEY]
            debugprint("This session: " + this_session)
            dtext = "Session: {} ".format(this_session)
            cherrypy.session.regenerate()
            dtext+= "has been regenerated to: {}".format(cherrypy.session[SESSION_KEY])
            debugprint(dtext)
        except KeyError:
            debugprint("Redirecting to login page...")
            raise cherrypy.HTTPRedirect("/login")

def protect(*conditions):
    def decorate(f):
        if not hasattr(f, '_cp_config'):
            f._cp_config = dict()
        if 'auth.require' not in f._cp_config:
            f._cp_config['auth.require'] = []
        f._cp_config['auth.require'].extend(conditions)
        return f
    return decorate
    
def logout():
    this_session = cherrypy.session.get(SESSION_KEY, None)
    cherrypy.session[SESSION_KEY] = None
    return "Logout successful"

