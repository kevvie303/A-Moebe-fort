function loadData(room) {
    fetch(`/data/${room}`)
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            console.log(data); // Log the data for inspection
            displayData(data);
        })
        .catch(error => {
            console.error('There was a problem with the fetch operation:', error);
        });
}


function formatTime(duration) {
    const minutes = Math.floor(duration / 60);
    const seconds = (duration % 60).toFixed(2);
    return `${minutes}m ${seconds}s`;
}

function displayData(data) {
    const taskTable = document.getElementById('task-table');
    taskTable.innerHTML = `
        <tr>
            <th>Task</th>
            <th>Fastest Time</th>
            <th>Slowest Time</th>
        </tr>
    `; // Clear the table headers

    if (!data || !Array.isArray(data) || data.length === 0) {
        taskTable.innerHTML += `<tr><td colspan="3">No data available.</td></tr>`;
        return;
    }

    const taskDurations = {};

    data.forEach(entry => {
        const startTime = new Date(entry.start_time);

        Object.entries(entry.tasks).forEach(([taskName, taskDetails]) => {
            const solvedTime = new Date(taskDetails.timestamp);
            const duration = (solvedTime - startTime) / 1000; // duration in seconds
            
            // Initialize the task entry if not already present
            if (!taskDurations[taskName]) {
                taskDurations[taskName] = {
                    fastest: duration,
                    slowest: duration
                };
            } else {
                // Update the fastest and slowest times for the task
                if (duration < taskDurations[taskName].fastest) {
                    taskDurations[taskName].fastest = duration;
                }
                if (duration > taskDurations[taskName].slowest) {
                    taskDurations[taskName].slowest = duration;
                }
            }
        });
    });

    // Populate the table with task data
    Object.entries(taskDurations).forEach(([taskName, times]) => {
        const fastestTime = formatTime(times.fastest);
        const slowestTime = formatTime(times.slowest);
        taskTable.innerHTML += `
            <tr>
                <td>${taskName}</td>
                <td>${fastestTime}</td>
                <td>${slowestTime}</td>
            </tr>
        `;
    });
}

// Function to convert time from seconds to minutes:seconds format
function formatTime(seconds) {
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = Math.round(seconds % 60);
    return `${minutes}m ${remainingSeconds}s`;
}
