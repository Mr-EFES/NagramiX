<!DOCTYPE html>
<html>
<head>
    <meta name="referrer" content="strict-origin-when-cross-origin">
    <style>
        body { margin: 0; width:100%%; height:100%%; background-color:#000; }
        html { width:100%%; height:100%%; background-color:#000; }
        .container iframe, .container object, .container embed { position: absolute; top: 0; left: 0; width: 100%% !important; height: 100%% !important; }
    </style>
</head>
<body>
    <div class="container">
        <div id="player"></div>
    </div>
    <script>
        var player;
        var iframe;
        
        function invoke(command) {
            iframe.contentWindow.postMessage(JSON.stringify({ "event": "inject", "command": command }), "*");
        }
    
        var playbackState = 0;
        var duration = 0.0;
        var position = 0.0;
        var downloadProgress = 0.0;
        var quality = "";
        var availableQualities = "";
        var failed = false;
        var providerErrorCode = null;
        var progressTimer;
        var storyboardSpec = ""

        function onYouTubeIframeAPIReady() {
            var options = %@;
            options.events = {
                onReady: onReady, onStateChange: onStateChange,
                onPlaybackQualityChange: onPlaybackQualityChange, onError: onPlayerError
            };
            player = new YT.Player("player", options);
        }

        function updatePosition() {
            downloadProgress = player.getVideoLoadedFraction();
            position = player.getCurrentTime();
            duration = player.getDuration();
            updateState();
            invoke("tick");
        }

        function play() {
            if (iframe) player.playVideo();
        }
    
        function pause() {
            if (iframe) player.pauseVideo();
        }
    
        function seek(timestamp) {
            if (iframe) player.seekTo(timestamp, true);
        }
        
        function setRate(rate) {
            if (iframe) player.setPlaybackRate(rate);
        }
        
        function updateState() {
            window.location.href = "embed://onState?failed=" + failed + (providerErrorCode === null ? "" : "&errorCode=" + providerErrorCode) + "&playback=" + playbackState + "&position=" + position + "&duration=" + duration + "&download=" + downloadProgress + '&quality=' + quality + '&availableQualities=' + availableQualities + '&storyboard=' + storyboardSpec;
        }

        function onReady(event) {
            if (iframe === event.target.getIframe()) return;
            player = event.target;
            iframe = player.getIframe();
            player.setSize(window.innerWidth, window.innerHeight);
            duration = player.getDuration();
            invoke("initialize");
            invoke("tick");
            if (progressTimer === undefined) progressTimer = window.setInterval(updatePosition, 500);
            window.location.href = "embed://onReady";
        }
    
        function onStateChange(event) {
            // Only an actual playing event confirms that the provider recovered.
            if (event.data === 1) {
                failed = false;
                providerErrorCode = null;
            }
            playbackState = event.data;
            updateState();
        }

        function onPlaybackQualityChange(event) {
            quality = event.data;
            updateState();
        }

        function onPlayerError(event) {
            failed = true;
            providerErrorCode = Number.isInteger(event.data) ? event.data : null;
            updateState();
        }

        window.onresize = function() {
            if (iframe) player.setSize(window.innerWidth, window.innerHeight);
        }
    </script>
    <script src="https://www.youtube.com/iframe_api"></script>
</body>
</html>
