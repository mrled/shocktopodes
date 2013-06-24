<html>
  <head>
    <title><%block name="title" /></title>
    <script type="text/javascript" 
            src="http://ajax.googleapis.com/ajax/libs/jquery/1.6/jquery.min.js"></script>
    <link rel="stylesheet" href="/static/shock.css" />
    <link rel="stylesheet" href="/static/dropzone/css/basic.css" />
    <%block name="underheader" />
  </head>
  <body>
    <h1><a href="/">SHOCKTOPODES</a></h1>
    ${self.body()}
  </body>
</html>
