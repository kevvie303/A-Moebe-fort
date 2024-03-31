$(document).ready(function () {
  $("#add-music-button1").click(function () {
    // Open a file selection dialog when the button is clicked
    var fileInput = $('<input type="file" accept=".mp3,.ogg,.wav">');
    fileInput.on("change", function () {
      var file = fileInput[0].files[0];
      // Send the selected file to the server
      var formData = new FormData();
      formData.append("file", file);
      $.ajax({
        type: "POST",
        url: "/add_music1",
        data: formData,
        processData: false,
        contentType: false,
        success: function (response) {
          console.log(response);
          //alert('Music added successfully!');
        },
        error: function (error) {
          console.log(error);
          alert("Failed to add music.");
        },
      });
    });
    fileInput.click(); // Trigger the file selection dialog
  });
});

$(document).ready(function () {
  // ...

  $("#select-file-button").click(function () {
    // Open a new window with the file selection page
    var fileSelectionWindow = window.open(
      "/file_selection",
      "_blank",
      "height=400,width=400"
    );

    // Poll for the selected file
    var pollTimer = setInterval(function () {
      if (fileSelectionWindow.closed) {
        clearInterval(pollTimer);
      } else {
        try {
          var selectedFile = fileSelectionWindow.selectedFile;
          if (selectedFile) {
            // Send the selected file to the server
            $.ajax({
              type: "POST",
              url: "/play_music",
              data: { file: selectedFile },
              success: function (response) {
                console.log(response);
              },
              error: function (error) {
                console.log(error);
              },
            });
            clearInterval(pollTimer);
          }
        } catch (error) {
          // Ignore any errors when accessing selectedFile property
        }
      }
    }, 1000); // Adjust the interval as needed
  });
  $("#pause-music-button").click(function () {
    // Send a request to the server to stop the music
    $.ajax({
      type: "POST",
      url: "/pause_music",
      success: function (response) {
        console.log(response);
      },
      error: function (error) {
        console.log(error);
      },
    });
  });
  $("#fade-out-music-button").click(function () {
    // Send a request to the server to stop the music
    $.ajax({
      type: "POST",
      url: "/fade_music_out_hint",
      success: function (response) {
        console.log(response);
      },
      error: function (error) {
        console.log(error);
      },
    });
  });
  $("#fade-in-music-button").click(function () {
    // Send a request to the server to stop the music
    $.ajax({
      type: "POST",
      url: "/fade_music_in_hint",
      success: function (response) {
        console.log(response);
      },
      error: function (error) {
        console.log(error);
      },
    });
  });
});
// Add a click event listener to the "light-button"
function sendLightControlRequest(lightName) {
  // Make an AJAX request using jQuery
  $.ajax({
    type: "POST",
    url: "/control_light",
    data: JSON.stringify({ light_name: lightName }),
    contentType: "application/json; charset=utf-8",
    dataType: "json",
    success: function (response) {
      // Request was successful, handle the response if needed
      console.log(response);
    },
    error: function () {
      // Request failed, handle errors
      console.error("Error making the light control request");
    },
  });
}
$(document).ready(function () {
  var lockControls = $("#lockControls");

  // Fetch the sensor data from the server
  $.ajax({
    type: "GET",
    url: "/get_sensor_data", // Replace with the actual endpoint to fetch sensor data
    success: function (sensor_data) {
      // Filter out items that are not maglocks or lights
      var filteredData = sensor_data.filter(function (item) {
        return item.type === "maglock" || item.type === "light";
      });

      var lockControlArticle = $("<article>").addClass("lock-control");

      filteredData.forEach(function (actuator) {
        var lockDiv = $("<div>").addClass("lock");
        var actuatorName = $("<p>").text(actuator.name);
        var lockButtons = $("<div>").addClass("lock-buttons");

        if (actuator.type === "maglock") {
          var lockButton = $("<button>")
            .addClass("turn-on-button icon")
            .append(
              $("<img>").attr("src", "static/img/lock.svg").attr("alt", "Lock")
            );
          var unlockButton = $("<button>")
            .addClass("turn-off-button icon")
            .append(
              $("<img>")
                .attr("src", "static/img/unlock.svg")
                .attr("alt", "Unlock")
            );
          lockButtons.append(lockButton, unlockButton);
        } else if (actuator.type === "light") {
          var onButton = $("<button>")
            .addClass("turn-on-button icon")
            .append(
              $("<img>")
                .attr("src", "static/img/light-off.svg")
                .attr("alt", "Light On")
            );
          var offButton = $("<button>")
            .addClass("turn-off-button icon")
            .append(
              $("<img>")
                .attr("src", "static/img/light-on.svg")
                .attr("alt", "Light Off")
            );
          lockButtons.append(onButton, offButton);
        }

        lockButtons.find("button").click(function () {
          var action = $(this).hasClass("turn-on-button")
            ? "locked"
            : "unlocked";
          $.ajax({
            type: "POST",
            url: "/control_maglock",
            data: { maglock: actuator.name, action: action },
            success: function (response) {
              console.log(response);
            },
            error: function (error) {
              console.log(error);
            },
          });
        });

        lockDiv.append(actuatorName, lockButtons);
        lockControlArticle.append(lockDiv);
      });

      lockControls.append(lockControlArticle);
    },
    error: function (error) {
      console.log("Error fetching sensor data:", error);
    },
  });
});

// $(document).ready(function () {
//   var maglockStatuses = {}; // Object to store maglock statuses

//   function generateMaglockElementId(maglockNumber, maglockURL) {
//     // Replace non-alphanumeric characters in the URL with underscores
//     var sanitizedURL = maglockURL.replace(/[^a-zA-Z0-9]/g, "_");
//     return `maglock${maglockNumber}_${sanitizedURL}_status`;
//   }

//   function updateMaglockStatus(maglockNumber, maglockName, maglockURL) {
//     $.ajax({
//       type: "GET",
//       url: `${maglockURL}/maglock/status/${maglockNumber}`,
//       success: function (response) {
//         var maglockStatus = response.status;
//         var maglockStatusText =
//           maglockStatus === "locked" ? "Locked" : "Unlocked";

//         // Create a unique identifier for this maglock
//         var maglockElementId = generateMaglockElementId(
//           maglockNumber,
//           maglockURL
//         );

//         // Check if the maglockStatus for this maglock is already stored
//         if (maglockStatuses[maglockElementId] === undefined) {
//           // If not, create a new element
//           var newMaglockStatusElement = $("<p>").html(
//             `${maglockName}: <strong>${maglockStatusText}</strong>`
//           );
//           newMaglockStatusElement.attr("id", maglockElementId);
//           $("#maglock-status-container").append(newMaglockStatusElement);
//         } else {
//           // If yes, update the existing element
//           var maglockStatusElement = $(`#${maglockElementId}`);
//           maglockStatusElement.html(
//             `${maglockName}: <strong>${maglockStatusText}</strong>`
//           );
//         }

//         // Store the updated maglock status in the object
//         maglockStatuses[maglockElementId] = maglockStatusText;
//       },
//       error: function (error) {
//         console.log(error);
//       },
//     });
//   }

//   function updateAllMaglockStatuses(maglockURL) {
//     $.ajax({
//       type: "GET",
//       url: `${maglockURL}/maglock/list`,
//       success: function (response) {
//         var maglocks = response.maglocks;

//         for (var i = 0; i < maglocks.length; i++) {
//           var maglock = maglocks[i];
//           updateMaglockStatus(maglock.number, maglock.name, maglockURL);
//         }
//       },
//       error: function (error) {
//         console.log(error);
//       },
//     });
//   }

//   // Initial update for maglocks from the URL where you list them
//   updateAllMaglockStatuses("http://192.168.0.104:5000");
//   updateAllMaglockStatuses("http://192.168.0.114:5001");

//   // Update maglock statuses periodically
//   /*setInterval(function () {
//     updateAllMaglockStatuses("http://192.168.0.104:5000");
//     updateAllMaglockStatuses("http://192.168.0.114:5001");
//   }, 500); // Update every 2 seconds*/
// });

// $(document).ready(function () {
//   // Create an object to store the latest sensor statuses
//   var latestSensorStatuses = {};

//   // Function to update sensor status
//   function updateSensorStatus(sensorNumber, sensorName, sensorURL) {
//     $.ajax({
//       type: "GET",
//       url: `${sensorURL}/sensor/status/${sensorNumber}`,
//       success: function (response) {
//         var sensorStatus = response.status;

//         // Check if the status has changed
//         if (latestSensorStatuses[sensorNumber] !== sensorStatus) {
//           // Store the latest sensor status in the object
//           latestSensorStatuses[sensorNumber] = sensorStatus;

//           // Create or update the sensor status element
//           var sensorStatusElement = $(`#sensor${sensorNumber}-status`);
//           if (sensorStatusElement.length) {
//             sensorStatusElement.html(
//               sensorName + ": <strong>" + sensorStatus + "</strong>"
//             );
//           } else {
//             var newSensorStatusElement = $("<p>").html(
//               sensorName + ": <strong>" + sensorStatus + "</strong>"
//             );
//             newSensorStatusElement.attr("id", `sensor${sensorNumber}-status`);
//             $("#sensor-status-container").append(newSensorStatusElement);
//           }
//         }
//       },
//       error: function (error) {
//         console.log(error);
//       },
//     });
//   }

//   // Function to update all sensor statuses
//   function updateAllSensorStatuses(sensorURL) {
//     $.ajax({
//       type: "GET",
//       url: `${sensorURL}/sensor/list`,
//       success: function (response) {
//         var sensors = response.sensors;

//         for (var sensorNumber in sensors) {
//           var sensorName = sensors[sensorNumber];
//           updateSensorStatus(sensorNumber, sensorName, sensorURL);
//         }
//       },
//       error: function (error) {
//         console.log(error);
//       },
//     });
//   }
//   function updateLastKeypadCode(sensorURL) {
//     $.ajax({
//       type: "GET",
//       url: `${sensorURL}/keypad/pressed_keys`,
//       success: function (response) {
//         var pressedKeysArrays = response.pressed_keys_arrays;
//         if (pressedKeysArrays.length > 0) {
//           // Get the last-used code from the array
//           var lastUsedCodeArray =
//             pressedKeysArrays[pressedKeysArrays.length - 1];
//           var lastUsedCode = lastUsedCodeArray.join(""); // Combine keys into a single code
//           $("#keypad-shed-code strong").text(lastUsedCode);
//         }
//       },
//       error: function (error) {
//         console.log(error);
//       },
//     });
//   }

//   // Initial update for normal sensors from the first URL
//   updateAllSensorStatuses("http://192.168.0.104:5000");
//   updateLastKeypadCode("http://192.168.0.104:5000");
//   // Initial update for IR sensors from the second URL
//   updateAllSensorStatuses("http://192.168.0.105:5001");

//   // Function to update IR sensor status
//   function updateIRSensorStatus(sensorNumber, sensorName, sensorURL) {
//     $.ajax({
//       type: "GET",
//       url: `${sensorURL}/ir-sensor/status/${sensorNumber}`,
//       success: function (response) {
//         var irSensorStatus = response.status;

//         // Check if the status has changed
//         if (latestSensorStatuses[sensorNumber] !== irSensorStatus) {
//           // Create or update the IR sensor status element
//           var irSensorStatusElement = $(`#ir-sensor${sensorNumber}-status`);
//           if (irSensorStatusElement.length) {
//             irSensorStatusElement.html(
//               sensorName + ": <strong>" + irSensorStatus + "</strong>"
//             );
//           } else {
//             var newIrSensorStatusElement = $("<p>").html(
//               sensorName + ": <strong>" + irSensorStatus + "</strong>"
//             );
//             newIrSensorStatusElement.attr(
//               "id",
//               `ir-sensor${sensorNumber}-status`
//             );
//             $("#ir-sensor-status-container").append(newIrSensorStatusElement);
//           }
//         }
//       },
//       error: function (error) {
//         console.log(error);
//       },
//     });
//   }

//   // Function to update all IR sensor statuses
//   function updateAllIRSensorStatuses(sensorURL) {
//     $.ajax({
//       type: "GET",
//       url: `${sensorURL}/ir-sensor/list`,
//       success: function (response) {
//         var irSensors = response.sensors;

//         for (var i = 0; i < irSensors.length; i++) {
//           var sensor = irSensors[i];
//           updateIRSensorStatus(sensor.number, sensor.name, sensorURL);
//         }
//       },
//       error: function (error) {
//         console.log(error);
//       },
//     });
//   }

//   // Initial update for IR sensors from the second URL
//   updateAllIRSensorStatuses("http://192.168.0.114:5001");

//   // Update normal sensor statuses periodically
//   /* setInterval(function () {
//     updateAllSensorStatuses("http://192.168.0.104:5000");
//     updateAllSensorStatuses("http://192.168.0.105:5001");
//     updateLastKeypadCode("http://192.168.0.104:5000");
//   }, 500);

//   // Update IR sensor statuses periodically
//   setInterval(function () {
//     updateAllIRSensorStatuses("http://192.168.0.114:5001");
//   }, 500);*/
// });

$(document).ready(function () {
  var intervalId;
  var speed = 2;
  intervalId = setInterval(function () {
    updateTimers();
  }, 1000);

  function updateTimers() {
    $.get("/timer/value", function (data) {
      var timeLeft = parseInt(data);
      var timePlayed = 3600 - timeLeft;
      var formattedTimeLeft = formatTime(timeLeft);
      var formattedTimePlayed = formatTime(timePlayed);
      $("#time-left").text(formattedTimeLeft);
      $("#time-played").text(formattedTimePlayed);

      $(".time-display #time-left").text(formattedTimeLeft);
      $(".time-display #time-played").text(formattedTimePlayed);

      $("#krijgsgevangenis-link .preview #time-played").text(
        formattedTimePlayed
      );
      $("#krijgsgevangenis-link .preview #time-left").text(formattedTimeLeft);
    });
  }

  function formatTime(seconds) {
    var minutes = Math.floor(seconds / 60);
    var remainingSeconds = seconds % 60;
    return (
      minutes +
      ":" +
      (remainingSeconds < 10 ? "0" : "") +
      remainingSeconds.toFixed(0)
    );
  }

  function updateSpeedDisplay() {
    var formattedSpeed = speed.toFixed(1);
    $("#speed-display").text("Timer Speed: " + formattedSpeed + "x");
  }

  function getTimerSpeed() {
    $.get("/timer/get-speed", function (data) {
      speed = parseFloat(data);
      updateSpeedDisplay();
    });
  }

  $("#start-game-button").click(function () {
    $.post("/timer/start", function (data) {
      console.log(data);
    }).done(function () {});
    intervalId = setInterval(function () {
      updateTimers();
    }, 1000);
    $(".tasks, .locks, .lock-status, .pin-info").show();
    $("#continue-button, #prepare-result, #reset-list-container").hide();
    $("#pause-button").show();
  });

  $("#end-game-button").click(function () {
    $(".tasks, .locks, .lock-status, .pin-info, #reset-list-container").show();
    $("#prepare-result").hide();
    $("#pause-button, #prepare-game-button").show();
    clearInterval(intervalId);
    updateTimers();
    $.post("/timer/stop", function (data) {
      console.log(data);
    });

    $.post("/reset_task_statuses", function (data) {
      console.log(data);
      fetchTasks(); // Refresh the list after resetting statuses
    });
    $.post("/reset_puzzles", function (data) {
      console.log(data);
      fetchTasks(); // Refresh the list after resetting statuses
    });
  });
  $("#snooze-game-button").click(function () {
    $.post("/snooze_game", function (data) {
      console.log(data);
    });
    // Display snoozed status in the nav
    $("#nav-snooze-status").text("Room Snoozed");
    // Show the "Wake" button
    $("#wake-button").show();
    $(".important-controls, #reset-list-container").hide();
  });
  $("#speed-up-button").click(function () {
    $.post("/timer/speed", { change: 0.1 }, function (data) {
      speed += 0.1;
      console.log(data);
      updateSpeedDisplay();
    });
  });

  $("#slow-down-button").click(function () {
    $.post("/timer/speed", { change: -0.1 }, function (data) {
      speed -= 0.1;
      console.log(data);
      updateSpeedDisplay();
    });
  });

  $("#reset-button").click(function () {
    $.post("/timer/reset-speed", function (data) {
      console.log(data);
      speed = 1;
      updateSpeedDisplay();
    });
  });
  function updateButtonState(pauseState) {
    if (pauseState) {
      $("#pause-button").hide();
      $("#continue-button").show();
    } else {
      $("#pause-button").show();
      $("#continue-button").hide();
    }
  }
  function getButtonState() {
    $.get("/timer/pause-state", function (data) {
      var pauseState = !data;
      updateButtonState(pauseState);
      console.log(data);
    });
  }

  $("#pause-button").click(function () {
    $.post("/timer/pause", function (data) {
      console.log(data);
      if (data === "Timer paused") {
        $("#pause-button").hide();
        $("#continue-button").show();
      }
    });
  });

  $("#continue-button").click(function () {
    $.post("/timer/continue", function (data) {
      console.log(data);
      if (data === "Timer continued") {
        $("#continue-button").hide();
        $("#pause-button").show();
      }
    });
  });

  function initializeTimer() {
    updateTimers();
    updateSpeedDisplay();
  }

  initializeTimer();
  getTimerSpeed();
  getButtonState();
});

$(document).ready(function () {
  // Check the retriever status from the JSON file
  $.get("/get_game_status", function (data) {
    if (data.status === "snoozed") {
      // Display snoozed status in the nav
      $("#nav-snooze-status").text("Room Snoozed");
      // Show the "Wake" button
      $("#wake-button").show();
      $(".important-controls").hide();
    }
  });

  // Handle the "Wake" button click
  $("#wake-button").click(function () {
    // Send a request to reset retriever status to 'awake'
    $.post("/wake_room", function (data) {
      console.log(data);
      // Hide the "Wake" button
      $("#wake-button").hide();
      $(".important-controls").show();
      // Update the snooze status in the navigation
      $("#nav-snooze-status").text("Room Awake");
    });
  });
  // Check the retriever status from the JSON file
  $.get("/get_game_status", function (data) {
    if (data.status === "prepared") {
      // Hide everything from the comment "HIDE FROM HERE"
      hideFromHere();
    }
  });
  // Function to hide everything from the comment "HIDE FROM HERE"
  function hideFromHere() {
    // Add CSS to hide the sections
    console.log("test");
    $(".tasks, .lock-status, .pin-info, #reset-list-container").hide();
  }
});

function openMediaControlPage() {
  window.open("/media_control", "_blank", "height=400,width=400");
}
$(document).ready(function () {
  $("#resume-music-button").click(function () {
    $.ajax({
      type: "POST",
      url: "/resume_music",
      success: function (response) {
        console.log(response);
      },
      error: function (error) {
        console.log(error);
      },
    });
  });
});

$(document).ready(function () {
  $("#stop-music-button").click(function () {
    $.ajax({
      type: "POST",
      url: "/stop_music",
      success: function (response) {
        console.log(response);
      },
      error: function (error) {
        console.log(error);
      },
    });
  });
  $("#reboot-pi-mag").click(function () {
    $.ajax({
      type: "POST",
      url: "/reboot-maglock-pi",
      success: function (response) {
        console.log(response);
      },
      error: function (error) {
        console.log(error);
      },
    });
  });
  $("#reboot-pi-music").click(function () {
    $.ajax({
      type: "POST",
      url: "/reboot-music-pi",
      success: function (response) {
        console.log(response);
      },
      error: function (error) {
        console.log(error);
      },
    });
  });
  $("#backup-top-pi").click(function () {
    $.ajax({
      type: "POST",
      url: "/backup-top-pi",
      success: function (response) {
        console.log(response);
      },
      error: function (error) {
        console.log(error);
      },
    });
  });
  $("#backup-middle-pi").click(function () {
    $.ajax({
      type: "POST",
      url: "/backup-middle-pi",
      success: function (response) {
        console.log(response);
      },
      error: function (error) {
        console.log(error);
      },
    });
  });
});

/*function updateState() {
  $.ajax({
    url: "/get_state", // Endpoint in your app.py to fetch the state
    type: "GET",
    success: function (response) {
      var state = response.state;
      $("#current-state").text("Walkman: " + state);
    },
    error: function () {
      $("#current-state").text("Walkman: unknown");
    },
  });
}*/
// Update the state every 5 seconds (5000 milliseconds)
//setInterval(updateState, 5000);

$(document).ready(function () {
  function updateStatusDisplay() {
    $.get("/get_file_status", function (data) {
      $("#status-display").empty();

      const playingSongs = data.filter((entry) => entry.status === "playing");
      const pausedSongs = data.filter((entry) => entry.status === "paused");

      if (playingSongs.length > 0) {
        $("#music-list").empty();

        playingSongs.forEach((entry) => {
          const { filename, soundcard_channel } = entry;
          $("#status-display").append(`<div>${filename} is playing!</div>`);
          $("#music-list").append(`
                        <li>
                            ${filename}
                            <button class="button-style pause-button" data-file="${filename}" data-channel="${soundcard_channel}">Pause</button>
                        </li>
                    `);
        });
      } else {
        $("#music-list").empty(); // Clear the list if there are no songs playing
      }

      if (pausedSongs.length > 0) {
        $("#status-display").append("<div>Paused songs:</div>");
        pausedSongs.forEach((entry) => {
          const { filename, soundcard_channel } = entry;
          $("#status-display").append(`<div>${filename} is paused!</div>`);
          $("#music-list").append(`
                        <li>
                            ${filename}
                            <button class="button-style resume-button" data-file="${filename}" data-channel="${soundcard_channel}">Resume</button>
                        </li>
                    `);
        });
      }
    });
  }

  // Handle pause button click
  $(document).on("click", ".pause-button", function () {
    const selectedFile = $(this).data("file");
    const selectedChannel = $(this).data("channel");
    $.ajax({
      type: "POST",
      url: "/pause_music",
      data: { file: selectedFile, channel: selectedChannel },
      success: function (response) {
        console.log(response);
        updateStatusDisplay(); // Update the status display after pausing the song
      },
      error: function (error) {
        console.log(error);
      },
    });
  });

  // Handle resume button click
  $(document).on("click", ".resume-button", function () {
    const selectedFile = $(this).data("file");
    const selectedChannel = $(this).data("channel");
    $.ajax({
      type: "POST",
      url: "/resume_music",
      data: { file: selectedFile, channel: selectedChannel },
      success: function (response) {
        console.log(response);
        updateStatusDisplay(); // Update the status display after resuming the song
      },
      error: function (error) {
        console.log(error);
      },
    });
  });

  // Call the function initially and update the status display every 5 seconds
  updateStatusDisplay();
  setInterval(updateStatusDisplay, 5000);
});
function updatePiStatus() {
  $.ajax({
    url: "/get-pi-status",
    method: "GET",
    success: function (data) {
      // Update the table with the latest status data
      $("#status-table").html(data);
    },
    complete: function () {
      // Schedule the next update after 5 seconds
      setTimeout(updatePiStatus, 5000);
    },
  });
}
// Start updating status on page load
$(document).ready(function () {
  updatePiStatus();
  setInterval(fetchTasks, 2000);
});

async function fetchTasks() {
  console.log("Fetching tasks...");
  try {
    const response = await fetch("/get_task_status"); // Corrected route
    const tasks = await response.json();
    console.log("Fetched tasks:", tasks);

    const taskList = document.getElementById("task-list");
    taskList.innerHTML = ""; // Clear existing list

    tasks.forEach((task) => {
      // Create a p element for displaying tasks and states
      const taskStatus = document.createElement("p");
      taskStatus.id = task.task;
      taskStatus.innerHTML = `${task.task}: <strong class="pending">${task.state}</strong>`;

      // Attach a click event to the p element
      taskStatus.addEventListener("click", () => {
        openTaskPopup(task);
      });

      taskList.appendChild(taskStatus);
    });
  } catch (error) {
    console.error("Error fetching tasks:", error);
  }
}

function openTaskPopup(task) {
  const taskPopup = document.querySelector(".tasks-hidden");
  const taskTitle = taskPopup.querySelector(".task-title");
  const taskDescription = taskPopup.querySelector(".task-description");
  const currentState = taskPopup.querySelector(".current-state strong");
  const solvedButton = taskPopup.querySelector(".solved-button");
  const skipButton = taskPopup.querySelector(".skip-button");
  const pendingButton = taskPopup.querySelector(".pending-button");

  // Populate the popup with task details
  taskTitle.textContent = task.task;
  taskDescription.textContent = task.description;
  currentState.textContent = task.state;

  // Clear any existing event listeners
  solvedButton.onclick = null;
  pendingButton.onclick = null;
  skipButton.onclick = null;
  const taskControlContainer = taskPopup.querySelector(
    ".task-control-container"
  );

  // Remove any previously added dynamic buttons and "Play hint" message
  const existingDynamicButtonContainer = taskControlContainer.querySelector(
    ".dynamic-button-container"
  );
  if (existingDynamicButtonContainer) {
    existingDynamicButtonContainer.remove();
  }

  // Create a container div for the dynamic buttons
  const dynamicButtonContainer = document.createElement("div");
  dynamicButtonContainer.className = "dynamic-button-container";

  // Create a "Play hint" message
  const playHintMessage = document.createElement("p");
  playHintMessage.textContent = "Play hint:";

  // Append the "Play hint" message to the dynamicButtonContainer
  dynamicButtonContainer.appendChild(playHintMessage);

  // Create and append 4 new buttons to the dynamicButtonContainer
  for (let i = 1; i <= 4; i++) {
    const dynamicButton = document.createElement("button");
    dynamicButton.textContent = `${task.task}-${i}`;
    dynamicButton.className = "button-style dynamic-button";
    dynamicButton.id = `button-${task.task}-${i}`;

    // Add an event listener to each button
    dynamicButton.addEventListener("click", () => {
      // AJAX request using jQuery
      $.ajax({
        type: "POST",
        url: "/play_music",
        contentType: "application/json",
        data: JSON.stringify({
          message: `${task.task}-${i}.ogg`,
        }),
        success: function (response) {
          console.log("Response from Flask:", response);
        },
        error: function (error) {
          console.error("Error:", error);
        },
      });
    });

    // Append the button to the dynamicButtonContainer
    dynamicButtonContainer.appendChild(dynamicButton);
  }

  // Insert the dynamicButtonContainer before the ".current-state" element
  taskControlContainer.insertBefore(
    dynamicButtonContainer,
    taskControlContainer.querySelector(".current-state")
  );

  // Show the appropriate button based on the task state
  if (task.state === "solved" || task.state === "skipped") {
    solvedButton.style.display = "none";
    skipButton.style.display = "none";
    pendingButton.style.display = "block";
    pendingButton.onclick = () => markAsPending(task.task);
  } else {
    solvedButton.style.display = "block";
    skipButton.style.display = "block";
    pendingButton.style.display = "none";
    solvedButton.onclick = () => markAsSolved(task.task);
    skipButton.onclick = () => markAsSkipped(task.task);
  }

  // Display the popup
  taskPopup.classList.remove("hidden");
}

// Add an event listener to close the popup
const closePopupButton = document.querySelector(".close-tasks");
closePopupButton.addEventListener("click", () => {
  const taskPopup = document.querySelector(".tasks-hidden");
  taskPopup.classList.add("hidden");
});

async function markAsSolved(taskName) {
  console.log(`Marking ${taskName} as solved...`);
  try {
    const response = await fetch(`/solve_task/${taskName}`, {
      method: "POST",
    });

    const data = await response.json();
    console.log(data.message);

    closeTaskPopup(); // Close the popup
    fetchTasks(); // Refresh the list
    response.classList.remove("pending");
    response.classList.add("unlocked");
    console.log();
  } catch (error) {
    console.error("Error marking as solved:", error);
  }
}
async function markAsSkipped(taskName) {
  console.log(`Marking ${taskName} as skipped...`);
  try {
    const response = await fetch(`/skip_task/${taskName}`, {
      method: "POST",
    });

    const data = await response.json();
    console.log(data.message);

    closeTaskPopup(); // Close the popup
    fetchTasks(); // Refresh the list
    console.log();
  } catch (error) {
    console.error("Error marking as skipped:", error);
  }
}
async function markAsPending(taskName) {
  console.log(`Marking ${taskName} as pending...`);
  try {
    const response = await fetch(`/pend_task/${taskName}`, {
      method: "POST",
    });

    const data = await response.json();
    console.log(data.message);

    closeTaskPopup(); // Close the popup
    fetchTasks(); // Refresh the list
  } catch (error) {
    console.error("Error marking as pending:", error);
  }
}

function closeTaskPopup() {
  const taskPopup = document.querySelector(".tasks-hidden");
  taskPopup.classList.add("hidden");
}

fetchTasks();

document.addEventListener("DOMContentLoaded", function () {
  document
    .getElementById("add-task-button")
    .addEventListener("click", function () {
      document.getElementById("task-modal").style.display = "block";
    });

  document
    .querySelector(".close-add-task")
    .addEventListener("click", function () {
      console.log("Close button clicked");
      document.getElementById("task-modal").style.display = "none";
    });

  document
    .getElementById("save-task-button")
    .addEventListener("click", function () {
      const taskName = document.getElementById("task-name").value;
      const taskDescription = document.getElementById("task-description").value;

      if (taskName && taskDescription) {
        // Send a POST request to your Flask route to add a new task
        // Adjust the route and data as needed
        fetch("/add_task", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            task: taskName,
            description: taskDescription,
            state: "pending",
          }),
        })
          .then((response) => response.json())
          .then((data) => {
            console.log(data.message);
            fetchTasks(); // Refresh the list
          })
          .catch((error) => console.error("Error adding task:", error));
      }

      document.getElementById("task-modal").style.display = "none";
    });
  document
    .getElementById("remove-task-button")
    .addEventListener("click", function () {
      populateTaskRemovalList(); // Populate the list of tasks
      document.getElementById("remove-modal").style.display = "block";
    });

  document
    .querySelector(".close-remove")
    .addEventListener("click", function () {
      document.getElementById("remove-modal").style.display = "none";
    });
  async function removeTask(taskName) {
    console.log(`Removing ${taskName}...`);
    try {
      const response = await fetch("/remove_task", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ task: taskName }),
      });

      const data = await response.json();
      console.log(data.message);
      fetchTasks(); // Refresh the list
    } catch (error) {
      console.error("Error removing task:", error);
    }
  }

  document
    .getElementById("confirm-remove-button")
    .addEventListener("click", function () {
      const selectedTask = document.querySelector(
        'input[name="task"]:checked'
      ).value;
      if (selectedTask) {
        const confirmRemove = confirm(
          `Are you sure you want to remove the task "${selectedTask}"?`
        );
        if (confirmRemove) {
          removeTask(selectedTask);
          document.getElementById("remove-modal").style.display = "none";
        }
      }
    });

  async function populateTaskRemovalList() {
    try {
      const response = await fetch("/get_task_status");
      const tasks = await response.json();

      const taskRemovalList = document.getElementById("task-removal-list");
      taskRemovalList.innerHTML = "";

      tasks.forEach((task) => {
        const li = document.createElement("li");
        const radio = document.createElement("input");
        radio.type = "radio";
        radio.name = "task";
        radio.value = task.task;
        li.textContent = `${task.task} - ${task.state}`;
        li.prepend(radio);
        taskRemovalList.appendChild(li);
      });
    } catch (error) {
      console.error("Error fetching tasks for removal:", error);
    }
  }
  const editButton = document.getElementById("edit-task-button");
  const editModal = document.getElementById("edit-modal");
  const taskEditList = document.getElementById("task-edit-list");
  const editTaskModal = document.getElementById("edit-task-modal");
  const editTaskNameInput = document.getElementById("edit-task-name");
  const editTaskDescriptionInput = document.getElementById(
    "edit-task-description"
  );
  const saveEditTaskButton = document.getElementById("save-edit-task-button");
  let previousSaveEditTaskListener;
  // Event listener for opening the edit modal
  editButton.addEventListener("click", function () {
    // Fetch the list of tasks from the server
    fetch("/get_tasks")
      .then((response) => response.json())
      .then((tasks) => {
        // Clear the previous task list
        taskEditList.innerHTML = "";

        // Populate the modal with tasks
        tasks.forEach((task) => {
          const li = document.createElement("li");
          const editTaskButton = document.createElement("button");
          editTaskButton.textContent = task.task;
          editTaskButton.classList.add("button-style");
          editTaskButton.addEventListener("click", function () {
            // Open the edit task modal and populate with current task info
            editTaskNameInput.value = task.task;
            editTaskDescriptionInput.value = task.description;
            editTaskModal.style.display = "block";
            // Save the current task being edited
            const currentTask = task;

            // Remove any previous event listeners
            if (previousSaveEditTaskListener) {
              saveEditTaskButton.removeEventListener(
                "click",
                previousSaveEditTaskListener
              );
            }

            // Add a new event listener for the save button
            previousSaveEditTaskListener = function () {
              // Get the edited task information
              const editedTaskName = editTaskNameInput.value;
              const editedTaskDescription = editTaskDescriptionInput.value;

              // Send the edited information to the server
              fetch("/edit_task", {
                method: "POST",
                headers: {
                  "Content-Type": "application/json",
                },
                body: JSON.stringify({
                  task: currentTask.task,
                  editedTaskName: editedTaskName,
                  editedTaskDescription: editedTaskDescription,
                }),
              })
                .then((response) => response.json())
                .then((data) => {
                  console.log(data.message);
                  // Close the edit task modal
                  editTaskModal.style.display = "none";
                  // Fetch tasks again to refresh the list
                  fetchTasks();
                })
                .catch((error) => {
                  console.error("Error editing task:", error);
                });
            };

            saveEditTaskButton.addEventListener(
              "click",
              previousSaveEditTaskListener
            );
          });
          li.appendChild(editTaskButton);
          taskEditList.appendChild(li);
        });

        // Show the edit modal
        editModal.style.display = "block";
      })
      .catch((error) => {
        console.error("Error fetching tasks:", error);
      });
    document
      .querySelector(".close-edit")
      .addEventListener("click", function () {
        document.getElementById("edit-modal").style.display = "none";
      });
    document
      .querySelector(".close-edit-task")
      .addEventListener("click", function () {
        document.getElementById("edit-task-modal").style.display = "none";
      });
  });
});
$(document).ready(function () {
  var prepareButton = $("#prepare-game-button");
  var playerTypeModal = $("#playerTypeModal");
  var prepareGameModalButton = $("#prepare-game-modal-button");
  var updateStatusInterval = setInterval(updateRetrieverStatus, 1000);
  var updatePlayStatus;
  var updateWakeStatus;
  var prepareResult = $("#prepare-result");
  var prepareStatus = $("#prepare-status");
  var resultsSection = $("#results-section");

  // Show the player type modal when the "Prepare game" button is clicked
  prepareButton.on("click", function () {
    playerTypeModal.show();
  });

  // Close the modal if the close button or outside the modal is clicked
  $(".close").on("click", function () {
    playerTypeModal.hide();
  });

  // Handle the "Prepare game" button inside the modal
  prepareGameModalButton.on("click", function () {
    var selectedPlayerType = $("#player-type").val();
    playerTypeModal.hide(); // Close the modal

    // Only proceed with preparation if a player type is selected
    if (selectedPlayerType) {
      performPreparation(selectedPlayerType);
    } else {
      alert("Please select a player type.");
    }
  });

  // Function to perform the preparation steps
  function performPreparation(playerType, prefix) {
    prepareButton.hide();
    prepareResult.show();
    $(".tasks, .lock-status, .pin-info, #reset-list-container").hide();
    prepareStatus.html("Preparing...");
    clearInterval(updateStatusInterval);
    updatePlayStatus = setInterval(updatePlayingStatus, 1000);

    // Use the playerType variable in your preparation logic
    $.ajax({
      type: "POST",
      url: "/prepare",
      data: { playerType: playerType, prefix: "vol" },
      success: function (response) {
        prepareStatus.html(
          "Prepared - Status: OK. Game will start when the door is open or the start game button has been clicked."
        );

        // Debugging: Output the response.message to the console
        console.log(response.message);

        resultsSection.empty();

        // Loop through the JSON data and create a neat display
        for (var device in response.message) {
          var deviceStatus = response.message[device];
          var deviceDiv = $("<div>").addClass("device-status");
          var header = $("<h3>").text(device);
          deviceDiv.append(header);

          var statusContainer = $("<div>").addClass("prepare-status-container");

          for (var script in deviceStatus) {
            var status = deviceStatus[script];
            var statusText = status ? "Running" : "Not Running";
            var scriptDiv = $("<div>").addClass("script-status");

            // Dynamically set the color based on the service status
            var colorClass = status ? "text-green" : "text-red";
            scriptDiv.html(
              `<p class="${colorClass}">${script}: ${statusText}</p>`
            );

            statusContainer.append(scriptDiv);
          }

          deviceDiv.append(statusContainer);
          resultsSection.append(deviceDiv);
        }
      },
      error: function () {
        prepareStatus.html("Error occurred during preparation.");
      },
    });
  }
  function updateRetrieverStatus() {
    console.log("hi");
    $.get("/get_game_status", function (data) {
      if (data.status === "prepared") {
        prepareButton.hide();
        performPreparation(); // Trigger the preparation function
      }
    });
  }
  function updatePlayingStatus() {
    $.get("/get_game_status", function (data) {
      if (data.status === "playing") {
        console.log("hii");
        clearInterval(updatePlayStatus);
        prepareButton.hide();
        $(".tasks, .locks, .lock-status, .pin-info").show();
        $("#prepare-result, #reset-list-container").hide();
      }
    });
  }
  $.get("/get_game_status", function (data) {
    if (data.status === "playing") {
      clearInterval(updatePlayStatus);
      prepareButton.hide();
      $(".tasks, .locks, .lock-status, .pin-info").show();
      $("#prepare-result, #snooze-game-button, #reset-list-container").hide();
    }
  });
  $.get("/get_game_status", function (data) {
    if (data.status === "awake") {
      console.log("hii");
      clearInterval(updateWakeStatus);
      prepareButton.show();
      $("#prepare-game-button").show();
      $("#prepare-result").hide();
    }
  });
});

let programmaticChange = false;

async function sendLockRequest(task, isChecked) {
  try {
    const response = await fetch("/lock", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ task, isChecked }),
    });

    const data = await response.json();

    if (data.success) {
      console.log("Locking action executed successfully");
    } else {
      console.error("Error executing locking action:", data.error);
    }
  } catch (error) {
    console.error("Error:", error);
  }
}

document.addEventListener("DOMContentLoaded", () => {
  const socket = io({ transports: ["websocket"] });

  // Event listener for Socket.IO connection
  socket.on("connect", () => {
    console.log("Connected to Socket.IO");
    socket.emit("join_room", { room: "all_clients" });
  });

  // Event listener for joining a room acknowledgment
  socket.on("join_room_ack", (data) => {
    console.log("Joined room:", data.room);
    // Fetch and display the initial checklist when the client joins the room
    updateChecklist();
  });

  // Event listener for checklist updates
  socket.on("checklist_update", (data) => {
    console.log("Received checklist_update event:", data);
    // Update your checklist UI based on the received data
    updateChecklist();
  });

  // ... (other event listeners) ...

  // Function to update the checklist UI
  $("#reset-checklist").click(function () {
    // Send a request to the server to stop the music
    $.ajax({
      type: "POST",
      url: "/reset-checklist",
      success: function (response) {
        updateChecklist();
        console.log(response);
        const resetListContainer = document.getElementById(
          "reset-list-container"
        );
        const readyToPrepareMessage = resetListContainer.querySelector("p");

        if (readyToPrepareMessage) {
          resetListContainer.removeChild(readyToPrepareMessage);
        }
      },
      error: function (error) {
        console.log(error);
      },
    });
  });
  async function updateChecklist() {
    try {
      // Fetch game status using $.get
      $.get("/get_game_status", function (data) {
        if (data.status === "awake") {
          // If the game is "awake," proceed to fetch and display the checklist
          fetchAndDisplayChecklist();
        } else {
          // If the game is not "awake," hide the reset list
          hideResetList();
        }
      });
    } catch (error) {
      console.error("Error:", error);
    }
  }
  function displayChecklist(checklist) {
    const resetListContainer = document.getElementById("reset-list-container");
    const resetList = document.getElementById("reset-list");

    // Check if all tasks are completed
    const allCompleted = checklist.every((item) => item.completed);

    if (allCompleted) {
      // If all tasks are completed, hide the checklist and show "ready to prepare"
      resetList.style.display = "none";
      const readyToPrepareMessage = document.createElement("p");
      readyToPrepareMessage.textContent = "Ready to prepare";

      // Check if the message is already present to avoid duplication
      if (!resetListContainer.contains(readyToPrepareMessage)) {
        resetListContainer.appendChild(readyToPrepareMessage);
      }
    } else {
      // If not all tasks are completed, display the checklist
      resetList.style.display = "flex";
      resetList.innerHTML = ""; // Clear existing checklist items
      checklist.forEach((item, index) => {
        const listItem = document.createElement("li");
        const checkbox = document.createElement("input");
        checkbox.type = "checkbox";
        checkbox.id = item.task.replace(/\s/g, "");
        checkbox.checked = item.completed;

        const label = document.createElement("label");
        label.textContent = item.task;
        label.setAttribute("for", checkbox.id);

        // Apply line-through style if the task is completed
        if (item.completed) {
          label.style.textDecoration = "line-through";
        }

        listItem.appendChild(checkbox);
        listItem.appendChild(label);
        // if (index < checklist.length - 1) {
        //   listItem.style.borderBottom = "1px solid #ccc";
        // }
        resetList.appendChild(listItem);

        checkbox.addEventListener("change", async () => {
          if (!programmaticChange) {
            programmaticChange = true;
            const isChecked = checkbox.checked;
            const task = label.textContent.trim();
            await sendLockRequest(task, isChecked);
            programmaticChange = false;
          }
        });
      });

      // Show the checklist
      resetListContainer.style.display = "flex";
    }
  }
  function fetchAndDisplayChecklist() {
    // Fetch checklist data
    fetch("/get-checklist")
      .then((response) => response.json())
      .then((data) => {
        if (data.success) {
          console.log("Checklist data:", data.checklist);
          displayChecklist(data.checklist);
        } else {
          console.error("Error getting checklist:", data.error);
        }
      })
      .catch((error) => {
        console.error("Error:", error);
      });
  }

  function hideResetList() {
    const resetListContainer = document.getElementById("reset-list-container");
    resetListContainer.style.display = "none";
  }
});
document.addEventListener("DOMContentLoaded", function () {
  function fetchAndDisplayRaspberryPis() {
    fetch("/check_devices_status")
      .then((response) => response.json())
      .then((data) => {
        let piListDiv = document.querySelector(".pi-list");
        let rebootDiv = document.querySelector(".reboot");

        // Clear existing entries
        piListDiv.innerHTML = "<h3>Raspberry Pi Devices</h3>";
        rebootDiv.innerHTML = "<h3>Reboot Controls</h3>";

        data.forEach((pi) => {
          // Add to the Raspberry Pi list
          let piInfo = document.createElement("div");
          piInfo.textContent = `Hostname: ${pi.hostname}, IP Address: ${
            pi.ip_address
          }, Status: ${pi.online ? "Online" : "Offline"}`;
          piListDiv.appendChild(piInfo);

          // Create reboot buttons
          let rebootButton = document.createElement("button");
          rebootButton.textContent = `Reboot ${pi.hostname}`;
          rebootButton.className = "button-style";
          rebootButton.onclick = function () {
            sendRebootRequest(pi.ip_address);
            console.log(`Rebooting ${pi.hostname}`);
          };
          rebootDiv.appendChild(rebootButton);
        });
      })
      .catch((error) =>
        console.error("Error fetching Raspberry Pi data:", error)
      );
  }
  function sendRebootRequest(ipAddress) {
    fetch("/reboot_pi", {
      method: "POST",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
      },
      body: `ip_address=${encodeURIComponent(ipAddress)}`,
    })
      .then((response) => response.json())
      .then((data) => console.log(data.message))
      .catch((error) => console.error("Error sending reboot request:", error));
  }
  setInterval(function () {
    fetchAndDisplayRaspberryPis();
  }, 1000);
});
document.addEventListener("DOMContentLoaded", function () {
  var listPiButton = document.querySelector('a[href="/list_raspberrypi"]');
  var loader = document.getElementById("loader");

  listPiButton.addEventListener("click", function () {
    loader.hidden = false; // Show the loader
  });
  window.addEventListener("pagehide", function () {
    loader.hidden = true; // Hide the loader
  });
});
