$(document).ready(function() {
    $('.play-button, .garden-play-button, .garage-alley-play-button, .lab-play-button, .all-play-button').click(function() {
        var selectedFile = $(this).data('file');
        var postUrl;
        
        if ($(this).hasClass('garden-play-button')) {
            postUrl = '/play_music_garden';
        } else if ($(this).hasClass('garage-alley-play-button')) {
            postUrl = '/play_music_garage_alley';
        } else if ($(this).hasClass('lab-play-button')) {
            postUrl = '/play_music_lab';
        } else if ($(this).hasClass('all-play-button')) {
            postUrl = '/play_music_all';
        } else {
            postUrl = '/play_music'; // The default play button sends to the original URL
        }

        // Send the POST request using Ajax
        $.ajax({
            type: 'POST',
            url: postUrl,
            data: {file: selectedFile},
            success: function(response) {
                console.log(response);
                window.close(); // Close the window after successful playback
            },
            error: function(error) {
                console.log(error);
            }
        });
    });
});

