<%inherit file="_base.mako" />

<%block name="title">
  Shocktopodes: Secrets! 
</%block>

  <body><h2>Enter secret key</h2>
  <form method="post" action="/login?from_page=${from_page}">
    Secret key: 
    <input type="text" name="key" />
    <input type="submit" value="Submit" />
  </body>
