<%inherit file="_base.mako" />

<%block name="title">
  Shocktopodes
</%block>

<%block name="underheader">
  <script>

    function update_rf_list() {

      ##$("#no-recent-files").remove();
      $("#recent-file-list").remove();
      var rfl = '<ul id="recent-file-list"></ul>';
      $('#recent-file-container').append(rfl);

      if (update_rf_list.arguments.length !== 0) {
        maxfiles = 10;
        if (maxfiles > update_rf_list.arguments.length) {
          maxfiles = update_rf_list.arguments.length;
        }
        for (var i=0; i<maxfiles; i++) {
          var recfile = update_rf_list.arguments[i];
          var recli = "<li><a href=\"";
          recli+= recfile.metadataurl;
          recli+= "\">";
          recli+= recfile.filename;
          recli+= "</a></li>";
          $("ul#recent-file-list").append(recli);            
        }
      }
      else {
        var nofiles = '<li>No files have been uploaded to this server</li>';
        $("ul#recent-file-list").append(nofiles);
      }
    }


    $(document).ready(function() {
      update_rf_list();
    });
  </script>
</%block>

<div class="shock-column-set">
  <div class="shock-column">

    <h2>Recently uploaded files:</h2>
      <div id="recent-file-container">
        <ul id="recent-file-list">
          <li id="no-recent-files"><i>Fetching recent files...</i></li>
        </ul>
      </div>
      <script>


      </script>

    <%doc>
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
    </%doc>

  </div>
  <div class="shock-column">
    <h2>Upload a file</h2>
    <script src="./static/dropzone/dropzone.js"></script>
    <script>
      Dropzone.options.shockzone = {
        // init: function() { this.on("addedfile", function(file) { alert("Added file."); });
        paramName: "myFile",
      };
    </script>

    <form action="/shockup"
          class="dropzone"
          id="shockzone"></form>
  </div>
</div>
