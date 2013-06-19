## -*- mode: html -*-

<html>
  <head>
    <link rel="stylesheet" href="static/swissshock.css" />
    <link rel="stylesheet" href="static/dropzone/css/basic.css" />
    <style type="text/css">
      .shock-column-set {
        float: left;
        padding: 10px;
        margin: 50px 10px 10px 10px;
      }
      .shock-column {
        float: left; 
        max-width:45%;
        min-width:250px;
        margin: 15px;
      }
    </style>
  </head>
  <body>
    <h1>SHOCKTOPODES</h1>
    <div class="shock-column-set">
      <div class="shock-column">
        <h2>Theoretically, a list</h2>
        <ul>
          <li>One of these or w/e</li>
          <li>Another one</li>
          <li>Another!?!?</li>
        </ul>
      </div>
      <div class="shock-column">
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
      </div>
  </body>
</html>
