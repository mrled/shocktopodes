<%inherit file="_base.mako" />

<%block name="title">
  Shocktopodes
</%block>

<%block name="underheader">

  <link rel="stylesheet" href="./static/dropzone/css/dropzone.css" />
  <script src="./static/dropzone/dropzone.js"></script>


  <script>
  "use strict";

  var dz;

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

    if (rfarray.constructor !== Array) {
      console.log("Got a bad value as rfarray! What is it though? [" + rfarray.constructor.name + "]" );
      console.log(rfarray);
      return false;
    }

    $("#recent-file-list").remove();
    var rflisttype = "ul" 
    var rfl = '<'+rflisttype+' id="recent-file-list"></ul>'
    $('#recent-file-container').append(rfl);

    if (rfarray.length === 0) {
      var nofiles = '<li>No files have been uploaded to this server</li>';
      $("ul#recent-file-list").append(nofiles);
    } 
    else {
      var maxfiles = 10;
      if (maxfiles > rfarray.length) {
        maxfiles = rfarray.length;
      }
      for (var i=maxfiles-1; i>=0; i--) {
        var recfile = rfarray[i];
        var recli = "<li><a href=\"";
        recli+= recfile.metadataurl;
        recli+= "\">";
        recli+= recfile.filename;
        recli+= "</a></li>"; 
        $(rflisttype+'#recent-file-list').append(recli);

/*
        if (recfile) {
          var mockFile = {
            name: recfile.filename, 
            size: recfile.length,
            url: recfile.metadataurl
          };
          dz.emit("addedfile", mockFile);
        }
*/
      }
    }
  }

  $(document).ready(function() {
    dz = new Dropzone(document.body, { 
      paramName: "myFile",
      url: "/shockup", 
      previewsContainer: "#previews", 
      clickable: "#uploadbutt",
      uploadprogress: function(file, progress) {
        console.log("uploadprogress");
      },
      thumbnail: function(file, dataUrl) {
        console.log("thumbnail")
      }
    });
    var tid;
    dz.on("drop", function(event) {
      event.stopPropagation();
      event.preventDefault();
      $('.overlay').hide();
    });
    dz.on("dragover", function(event) {
      clearTimeout(tid);
      event.stopPropagation();
      event.preventDefault();
      $('.overlay').show();
    });
    dz.on("dragleave", function(event) {
      tid = setTimeout(function() {
        event.stopPropagation();
        $('.overlay').hide();
      }, 0);
    });
    dz.on("complete", function(event) {
      get_rf();
    });
    /*
    dz.on("addedfile", function(file) {
      file.previewElement.addEventListener("click", function() { 
        dz.removeFile(file); 
      });
    });
    */

    get_rf();
  });

  </script>

</%block>

  <div class="overlay">
    <div class="overlaytext">
      <p>Drop your file to upload</p>
    </div>
  </div>

    <h2>Recently uploaded files:</h2>
      <div id="recent-file-container">
        <ul id="recent-file-list">
          <li id="no-recent-files"><i>Fetching recent files...</i></li>
        </ul>
      </div>
    <div id="previews" class="dropzone-previews"></div>
    <button id="uploadbutt">Click me to select files</button>

