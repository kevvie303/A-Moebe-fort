import os
import json
def create_html_file(name):
    html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{name}</title>
    <link rel="stylesheet" type="text/css" href="{{{{ url_for('static', filename='css/styles.css') }}}}">
    <link rel="stylesheet" type="text/css" href="{{{{ url_for('static', filename='fonts/fonts.css')}}}}">
    <link rel="icon" href="/static/img/logo.png" type="image/png">
    <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>    
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.7.4/socket.io.js"></script>
</head>
<body>

    <!-- header -->
    <header class="retriever-logo header-logo">
        <figure class="logo-container">
            <img src="/static/img/retrieverlogo.svg" alt="Retriever Logo">
        </figure>
    </header>

    <!-- nav -->
    <nav class="important-controls">
        <div class="time-elapsed">
            <p>Elapsed</p>
            <p id="time-played">00:00</p>
        </div>

        <div class="game-controls">
            <button id="media-popup" class="icon"><img src="/static/img/media.svg" alt="Button to the media controls"></button>
            <button id="time-popup" class="icon"><img src="/static/img/time.svg" alt="Button to time settings"></button>
            <button id="pi-popup" class="icon"><img src="/static/img/pi.svg" alt="Button to Pi settings"></button>
            <button id="abort-button" class="icon"><img src="/static/img/game.svg" alt="Button to abort the room"></button>
        </div>

        <div class="time-remaining">
            <p>Remaining</p>
            <p id="time-left">60:00</p>
        </div>
    </nav>
    <div id="myModal" class="modal">
        <div class="modal-content">
          <span class="close">&times;</span>
          <h2>My Account</h2>
          <p>Your current name:</p>
          <p id="currentName"></p>
          <input type="text" id="newUsernameInput" placeholder="Enter new name" required>
          <button id="updateNameButton" class="button-style">Update Name</button>
        </div>
      </div>
    <!-- media section -->
    <section class="media-hidden hidden-popup hidden">
        <article class="media popup">
            <button class="close-media close"><img src="/static/img/abort.svg" alt="Close button"></button>

            <h2>Media</h2>
            <div>
                <a href="/media_control" class="button-style">Go to media control</a>
                <button id="stop-music-button" class="button-style">Force stop music</button>
                <button id="fade-out-music-button" class="button-style">Fade out background before hint</button>
                <button id="fade-in-music-button" class="button-style">Fade in background after hint</button>
                <p id="music-list">
                    Music files will be dynamically added here
                </p>
            </div>

            <div id="status-display"></div>
        </article>
    </section>

    <!-- time section -->
    <section class="time-hidden hidden-popup hidden">
        <article class="time popup">
            <button class="close-time close"><img src="/static/img/abort.svg" alt="Close button"></button>

            <h2>Time controls</h2>

            <div class="time-display">

                <div class="timer">
                    <p>Played<strong id="time-played">00:00</strong></p>
                    <p>Left: <strong id="time-left">60:00</strong></p>
                </div>
                
                <div class="speed-display">
                    <p id="speed-display">Speed: 1x</p>
                </div>
            </div>

            <div class="time-controls">
                <div class="speed-up-slow-down">
                    <button id="speed-up-button" class="button-style main-button">Speed Up</button>
                    <button id="slow-down-button" class="button-style main-button">Slow Down</button>
                </div>
                <div class="reset-speed">
                    <button id="reset-button" class="button-style main-button">Reset Speed</button>
                </div>
                <button id="add-minute-button" class="button-style main-button">+1 min</a>
                <button id="remove-minute-button" class="button-style main-button">-1 min</a>
            </div>
        </article>
    </section>

    <!-- pi controls -->
    <section class="pi-hidden hidden-popup hidden">
        <article class="pi popup">
            <button class="close-pi close"><img src="/static/img/abort.svg" alt="Close button"></button>
            <div id="loader" class="loader" hidden></div>
            <h2>Pi controls</h2>
            <div class="pi-list">
                <h3>Raspberry Pi Devices</h3>
            </div>
            <article class="pi-buttons">
                <div class="pi-controls">
                    <div class="reboot">
                        <h3>Reboot</h3>
                    </div>
                <a href="/list_raspberrypi" id="raspberryPiButton" class="button-style">List Raspberry Pi Devices</a>
                <a href="/list_sensors" id="sensorButton" class="button-style">Add Sensor</a>
                <a href="/sd-renewal" id="sdRenewalButton" class="button-style">Renew sd card</a>
            </article>
                
            </div>
        </article>
    </section>

    <!-- game control -->
    <section class="game-hidden hidden-popup hidden">
        <article class="game-controls popup">
            <button class="close-game close"><img src="/static/img/abort.svg" alt="Close button"></button>

            <h2>Game controls</h2>

            <div class="game-buttons">
                <button id="start-game-button" class="button-style">Start game</button>
                <button id="snooze-game-button" class="button-style">Snooze game</button>
                <button id="prepare-game-button" class="button-style">Prepare game</button>
                <button class=" abort-button button-style">Abort game</button>

            </div>

            <div class="abort hidden">
                <p>Are you sure you want to abort the game?</p>

                <button id="end-game-button" class="button-style">Yes, abort game</button>
            </div>

            <p class="confirmation hidden">Game aborted</p>
        </article>
    </section>

    <section id="playerTypeModal" class="prepare-hidden hidden-popup hidden modal">
        <article class="modal-content popup">
            <span class="close">&times;</span>
            <label for="player-type">Gaan kinderen of volwassen spelen:</label>
            <select id="player-type" name="player-type">
                <option value="adults">Volwassenen</option>
                <option value="kids">Kinderen</option>
            </select>
            <button id="prepare-game-modal-button" class="button-style">Prepare game</button>
        </article>
    </section>

    <!-- HIDE FROM HERE -->
    <section class="tasks-hidden hidden-popup hidden">
        <article class="task-control popup">
            <button class="close-tasks close"><img src="/static/img/abort.svg" alt="Close button"></button>
    
            <h2 class="task-title"></h2>
    
            <div class="task-control-container">
                <p class="task-description"></p>
    
                <p class="current-state">Currently: <strong></strong></p>
    
                <div class="button-container">
                    <button class="button-style solved-button">Solve</button>
                    <button class="button-style skip-button">Skip</button>
                    <button class="button-style pending-button">Pending</button>
                </div>
            </div>
        </article>
    </section>

    <!-- wake button na snooze -->
    <nav id="nav-snooze-status"></nav>
    <button id="wake-button" class="button-style" style="display: none;">Wake</button>
    
    <section class="control-container">

        <div id="prepare-result" class="hidden">
            <p id="prepare-status" class="centered-text">Preparing...</p>
            <div id="results-section">
            </div>
        </div>
        <section class="light-container">
            <article class="lights">
                <img src="../static/img/room-layout.svg" alt="Layout of the room">
                <figure class="light-buttons">
                    <img src="/static/img/light-bulb.svg" onclick="sendLightControlRequest('Light-1'); console.log('Clicked on Light-1');">
                    <img src="/static/img/light-bulb.svg" onclick="sendLightControlRequest('Light-3'); console.log('Clicked on Light-3');">
                    <img src="/static/img/light-bulb.svg" onclick="sendLightControlRequest('Light-2'); console.log('Clicked on Light-2');">
                    <img src="/static/img/light-bulb.svg" onclick="sendLightControlRequest('Light-4'); console.log('Clicked on Light-4');">
                    <img src="/static/img/light-bulb.svg" onclick="sendLightControlRequest('Light-5'); console.log('Clicked on Light-5');">
                    <img src="/static/img/light-bulb.svg" onclick="sendLightControlRequest('Light-6'); console.log('Clicked on Light-6');">
                    <img src="/static/img/light-bulb.svg" onclick="sendLightControlRequest('Light-7'); console.log('Clicked on Light-7');">
                </figure>        
            </article>
        </section>
    <!-- main -->
    <section id="reset-list-container" class="reset-list control">
        <h2>Reset Lijst</h2>
        <ul id="reset-list">
        </ul>
        <button id="reset-checklist" class="button-style">Reset</button>
    </section>

    <section class="tasks control">
        <h2>Tasks</h2>

        <div id="task-list"></div>        

        <article class="task-button-container">
            <button id="add-task-button" class="button-style">Add Task</button>
            <button id="remove-task-button" class="button-style">Remove Task</button>
            <button id="edit-task-button" class="button-style">Edit Task</button>
        </article>
        

        <!-- Modal -->
        <section id="task-modal" class="task-modal hidden-popup hidden">
            <article class="modal popup">
                <button class="close-add-task close"><img src="/static/img/abort.svg" alt="Close button"></button>
            
                <h2>Add task</h2>

                <div class="modal-content">
                    <!-- <span class="close-task modal-close">&times;</span> -->
                    <label for="task-name">Task Name:</label>
                    <input type="text" id="task-name">
                    <label for="task-description">Task Description:</label>
                    <input type="text" id="task-description">
                    <button id="save-task-button" class="button-style">Save Task</button>
                </div>
            </article>
        </section>
        <!-- <div id="task-modal" class="modal">
            <div class="modal-content">
                <span class="close-task modal-close">&times;</span>
                <label for="task-name">Task Name:</label>
                <input type="text" id="task-name">
                <label for="task-description">Task Description:</label>
                <input type="text" id="task-description">
                <button id="save-task-button" class="button-style">Save Task</button>
            </div>
        </div>  -->

        <!-- Modal for Task Removal -->
        <div id="remove-modal" class="modal">
            <div class="modal-content">
                <span class="close-remove modal-close">&times;</span>
                <h2>Select a Task to Remove</h2>
                <ul id="task-removal-list"></ul>
                <button id="confirm-remove-button" class="button-style">Confirm Removal</button>
            </div>
        </div>
        
        <div id="edit-modal" class="modal">
            <div class="modal-content">
                <span class="close-edit modal-close">&times;</span>
                <h2>Select a Task to Edit</h2>
                <ul id="task-edit-list"></ul>
            </div>
        </div>
        <div id="edit-task-modal" class="modal">
            <div class="modal-content">
                <span class="close-edit-task modal-close">&times;</span>
                <h2>Edit Task</h2>
                <label for="edit-task-name">Task Name:</label>
                <input type="text" id="edit-task-name">
                <label for="edit-task-description">Task Description:</label>
                <input type="text" id="edit-task-description">
                <button id="save-edit-task-button" class="button-style">Save Changes</button>
            </div>
        </div>

    </section>

    <!-- locks section-->
    <section class="locks control" id="lockControls">
        <h2>Actuators</h2>

    </section>
    <!--TODO: rename to a more sensible name-->
    <section class="lock-status control">
        <h2>Status</h2>

        <div class="status">
        </div>
    </section>

    <a href="{{{{ url_for('pin_info') }}}}" class="pin-info button-style">GPIO pin information</a>

    </section>
    <footer>
        <a href="/" class="button-style">Kamers</a>
        <button id="accountButton" class="button-style">My Account</button>
    </footer>

    

    <script src="{{{{ url_for('static', filename='js/sketch.js') }}}}"></script>
    <script src="{{{{ url_for('static', filename='js/index.js') }}}}"></script>
</body>
</html>
    """

    with open(f'templates/rooms/{name}.html', 'w') as file:
        file.write(html_content)    

def create_room_folder(room_name):
    folder_path = os.path.join('json', room_name)
    os.makedirs(folder_path, exist_ok=True)

    # Initialize JSON files with empty arrays or initial data
    files = {
        "checklist_data.json": [],
        "file_status.json": [],
        "game_data.json": [],
        "raspberry_pis.json": [],
        "game_status.json": {"status": "awake"},
        "sensor_data.json": [],
        "tasks.json": [],
        "timer_value": 3600
    }

    # Write initial data to JSON files
    for filename, data in files.items():
        with open(os.path.join(folder_path, filename), 'w') as f:
            json.dump(data, f)