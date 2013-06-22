<%inherit file="_base.mako" />

<%block name="title">
  Shocktopodes
</%block>

<h1>SHOCKTOPODES</h1>
<div class="shock-column-set">
  <div class="shock-column">
    %if len(recentfiles) > 0:
      <h2>Recently uploaded files:</h2>
      <ul>
        %for rf in recentfiles:
          <li><a href="${rf.metadataurl}">${rf.filename}</a>
        %endfor
      </ul>
    %else:
      <h2>No recently uploaded files...</h2>
    %endif
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
</div>
