<%
    needjplayer = False
    if file.content_type.startswith('image'):
        type='image'
    elif file.content_type.startswith('audio'):
        type='audio'
        needjplayer = True
%>

<html>
  <head>
    <title>${file.filename}</title>
    %if needjplayer: 
    <script type="text/javascript" 
            src="http://ajax.googleapis.com/ajax/libs/jquery/1.6/jquery.min.js"></script>'
      <link type="text/css" href="/static/jplayer-skin/jplayer.blue.monday.css" rel="stylesheet" />'
      <script type="text/javascript" src="/static/jplayer/jquery.jplayer.min.js"></script>'
      <script type="text/javascript">
        $(document).ready(function(){
          $("#jquery_jplayer_1").jPlayer({
            ready: function () {
              $(this).jPlayer("setMedia", {
                m4a: "http://localhost:7979/rawfile?fileid=${file.id}",
              });
            },
            swfPath: "/static/jplayer",
            supplied: "m4a"
          });
        });
      </script>
    %endif
  </head>
  <body>
    <h2>File ID: ${file.id}; Name: ${file.filename}</h2>
    <p>Type: ${file.content_type}; Length: ${file.length}</p>
    %if type == 'image':
      <p><img src=/rawfile?fileid=${file.id} /></p>
    %elif type == 'audio':
      <div id="jquery_jplayer_1" class="jp-jplayer"></div>
      <div id="jp_container_1" class="jp-audio">
        <div class="jp-type-single">
          <div class="jp-gui jp-interface">
            <ul class="jp-controls">
              <li><a href="javascript:;" class="jp-play" tabindex="1">play</a></li>
              <li><a href="javascript:;" class="jp-pause" tabindex="1">pause</a></li>
              <li><a href="javascript:;" class="jp-stop" tabindex="1">stop</a></li>
              <li><a href="javascript:;" class="jp-mute" tabindex="1" title="mute">mute</a></li>
              <li><a href="javascript:;" class="jp-unmute" tabindex="1" title="unmute">unmute</a></li>
              <li><a href="javascript:;" 
                     class="jp-volume-max" tabindex="1" title="max volume">max volume</a></li>
            </ul>
            <div class="jp-progress">
              <div class="jp-seek-bar">
                <div class="jp-play-bar"></div>
              </div>
            </div>
            <div class="jp-volume-bar">
              <div class="jp-volume-bar-value"></div>
            </div>
            <div class="jp-time-holder">
              <div class="jp-current-time"></div>
              <div class="jp-duration"></div>
              <ul class="jp-toggles">
                <li><a href="javascript:;" class="jp-repeat" 
                       tabindex="1" title="repeat">repeat</a></li>
                <li><a href="javascript:;" class="jp-repeat-off" 
                       tabindex="1" title="repeat off">repeat off</a></li>
              </ul>
            </div>
          </div>
          <div class="jp-title">
            <ul>
              <li>Bubble</li>
            </ul>
          </div>
          <div class="jp-no-solution">
            <span>Update Required</span>
            To play the media you will need to either update your browser to a 
            recent version or update your 
            <a href="http://get.adobe.com/flashplayer/" target="_blank">Flash plugin</a>.
          </div>
        </div>
      </div>
    % endif
  </body>
</html>