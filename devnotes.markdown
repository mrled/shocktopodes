# Devnotes

### Mako

Using Mako as a CherryPy tool: 
<http://tools.cherrypy.org/wiki/Mako>
    
### Data storage: sqlite + static filesystem data

<http://www.aminus.org/blogs/index.php/2005/08/24/cherrypy_now_handles_partial_gets?blog=2>
<http://docs.cherrypy.org/stable/progguide/files/static.html>

CherryPy doesn't support byte-range requests except for static files. Seeking in jplayer, and playing at all in iOS, requires byte-range support, so I have to keep the files in a directory on the filesystem, and just the metadata in the database. 

I store the files using their sha1 hash as the filename, with a file extension (not necessarily the original one, but one associated with the mime type) at the end. This lets CherryPy send out a content-type based on the filename automatically, and enables the byte-range requests. 

### Other projects & docs to look at

- sabnzbd+ uses CherryPy on Python 2.x with Cheetah as a template engine. 
- CherryMusic uses CherryPy and jplayer and works on Python 3.x.

- [blog post on sqlalchemy + cherrypy](http://www.defuze.org/archives/222-integrating-sqlalchemy-into-a-cherrypy-application.html)
- [AuthenticationAndAccessRestrictions](http://tools.cherrypy.org/wiki/AuthenticationAndAccessRestrictions)
- [My auth stuff based on the above](http://stackoverflow.com/questions/12595394/how-do-you-use-cookies-and-http-basic-authentication-in-cherrypy)

