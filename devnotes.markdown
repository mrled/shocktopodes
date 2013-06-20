# Devnotes

### Mako

Using Mako as a CherryPy tool: 
<http://tools.cherrypy.org/wiki/Mako>
    
### Data storage: sqlite + static filesystem data

CherryPy doesn't support byte-range requests except for static files. Seeking in jplayer, and playing at all in iOS, requires byte-range support, so I have to keep the files in a directory on the filesystem, and just the metadata in the database. 

I store the files using their sha1 hash as the filename, with a file extension (not necessarily the original one, but one associated with the mime type) at the end. This lets CherryPy send out a content-type based on the filename automatically, and enables the byte-range requests. 



