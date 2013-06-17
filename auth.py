# Note: 
# Much of this originated with: 
# <http://tools.cherrypy.org/wiki/AuthenticationAndAccessRestrictions>
# Which I refer to as AAAR in comments below. 

# Python3 builtins
import base64
import re

# Manual installation
import cherrypy 

# zknsrv files
from genericmethods import debugprint
import Library
library = Library.Library()

SESSION_KEY = '_zkn_username'

def protect(*args, **kwargs):
    debugprint("Inside protect()...")

    authenticated = False
    conditions = cherrypy.request.config.get('auth.require', None)
    debugprint("conditions: {}".format(conditions))
    if conditions is not None:
        # A condition is just a callable that returns true or false
        try:
            # TODO: I'm not sure if this is actually checking for a valid session?
            # or if just any data here would work? 
            this_session = cherrypy.session[SESSION_KEY]
    
            # check if there is an active session
            # sessions are turned on so we just have to know if there is
            # something inside of cherrypy.session[SESSION_KEY]:
            cherrypy.session.regenerate()
            # I can't actually tell if I need to do this myself or what
            email = cherrypy.request.login = cherrypy.session[SESSION_KEY]
            authenticated = True
            debugprint("Authenticated with session: {}, for user: {}".format(
                    this_session, email))
    
        except KeyError:
            # If the session isn't set, it either wasn't present or wasn't valid. 
            # Now check if the request includes HTTPBA?
            # FFR The auth header looks like: "AUTHORIZATION: Basic <base64shit>"
            # TODO: cherrypy has got to handle this for me, right? 
    
            authheader = cherrypy.request.headers.get('AUTHORIZATION')
            debugprint("Authheader: {}".format(authheader))
            if authheader:
                #b64data = re.sub("Basic ", "", cherrypy.request.headers.get('AUTHORIZATION'))
                # TODO: what happens if you get an auth header that doesn't use basic auth?
                b64data = re.sub("Basic ", "", authheader)
    
                decodeddata = base64.b64decode(b64data.encode("ASCII"))
                # TODO: test how this handles ':' characters in username/passphrase.
                email,passphrase = decodeddata.decode().split(":", 1)
                
                if library.user_verify(email, passphrase):
        
                    cherrypy.session.regenerate()
            
                    # This line of code is discussed in doc/sessions-and-auth.markdown
                    cherrypy.session[SESSION_KEY] = cherrypy.request.login = email
                    authenticated = True
                else:
                    debugprint ("Attempted to log in with HTTBA username {} but failed.".format(
                            email))
            else:
                debugprint ("Auth header was not present.")
                
        except:
            debugprint ("Client has no valid session and did not provide HTTPBA credentials.")
            debugprint ("TODO: ensure that if I have a failure inside the 'except KeyError'"
                        + " section above, it doesn't get to this section... I'd want to"
                        + " show a different error message if that happened.")
    
        if authenticated:
            for condition in conditions:
                if not condition():
                    debugprint ("Authentication succeeded but authorization failed.")
                    raise cherrypy.HTTPError("403 Forbidden")
        else:
            raise cherrypy.HTTPError("401 Unauthorized")

cherrypy.tools.zkauth = cherrypy.Tool('before_handler', protect)

def require(*conditions):
    """A decorator that appends conditions to the auth.require config
    variable."""
    def decorate(f):
        if not hasattr(f, '_cp_config'):
            f._cp_config = dict()
        if 'auth.require' not in f._cp_config:
            f._cp_config['auth.require'] = []
        f._cp_config['auth.require'].extend(conditions)
        return f
    return decorate

#### CONDITIONS
#
# Conditions are callables that return True
# if the user fulfills the conditions they define, False otherwise
#
# They can access the current user as cherrypy.request.login

# TODO: test this function with cookies, I want to make sure that cherrypy.request.login is 
#       set properly so that this function can use it. 
def zkn_admin():
    return lambda: library.user_is_admin(cherrypy.request.login)

def user_is(reqd_email):
    return lambda: reqd_email == cherrypy.request.login

#### END CONDITIONS

def logout():
    email = cherrypy.session.get(SESSION_KEY, None)
    cherrypy.session[SESSION_KEY] = cherrypy.request.login = None
    return "Logout successful"

