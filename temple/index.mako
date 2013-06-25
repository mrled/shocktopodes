<%inherit file="_base.mako" />

<%block name="title">
  Shocktopodes
</%block>

<%block name="underheader">
  <script>
  "use strict";

  function update_rf_list(sflist) {

    if (sflist === undefined) {
      alert("Failed to pass an argument to update_rf_list!")
      return false;
    }
    else if (sflist.constructor !== Array) {
      alert("Passed a bad value to update_rf_list!");
      return false;
    }

    $("#recent-file-list").remove();
    var rfl = '<ul id="recent-file-list"></ul>';
    $('#recent-file-container').append(rfl);

    if (sflist.length === 0) {
      var nofiles = '<li>No files have been uploaded to this server</li>';
      $("ul#recent-file-list").append(nofiles);
    } 
    else {
      var maxfiles = 10;
      if (maxfiles > sflist.length) {
        maxfiles = sflist.length;
      }
      for (var i=0; i<maxfiles; i++) {
        var recfile = sflist[i];
        var recli = "<li><a href=\"";
        recli+= recfile.metadataurl;
        recli+= "\">";
        recli+= recfile.filename;
        recli+= "</a></li>"; 
        $("ul#recent-file-list").append(recli);            
      }
    }

  }

  function get_rf() {
    var rfarray = [];
    function successfunc(data) {
      rfarray = data;
    }
    $.ajax({
      type: "GET",
      url: "/recentfiles",
      async: false,
      datatype: "json", 
      success:successfunc
    });
    update_rf_list(rfarray);
  }

  $(document).ready(function() {
    get_rf();
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

  </div>
  <div class="shock-column">
    <h2>Upload a file</h2>
    <script src="./static/dropzone/dropzone.js"></script>
    <script>
    function szinitfunc() {
      this.on("success", get_rf)
    }
    Dropzone.options.shockzone = {
      init: szinitfunc,
      paramName: "myFile"
    };
    </script>

    <form action="/shockup"
          class="dropzone"
          id="shockzone"></form>
  </div>
</div>
