<%inherit file="_base.mako" />

<%block name="title">
  Shocktopodes
</%block>

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

