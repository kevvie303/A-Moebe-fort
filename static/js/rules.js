$(document).ready(function () {
    const roomName = $("#room-name").text().trim();
    let ruleIdCounter = 1;
    function generateRandomId() {
        return Math.floor(1000 + Math.random() * 9000).toString();
    }

    function createRuleCard(rule = null) {
        const ruleId = rule ? rule.id : generateRandomId();
        const ruleCard = $(`
            <div class="rule-card" data-rule-id="${ruleId}">
                <div class="rule-card-header">
                    <h3># New Rule</h3>
                    <button class="delete-rule">Delete</button>
                </div>
                <div class="rule-card-body">
                    <div>
                        <h4 class="section-title">When all constraints pass</h4>
                        <div class="button-group constraints">
                            <button class="btn btn-green add-constraint" data-type="state-equals">+ Equals</button>
                            <button class="btn btn-orange add-constraint" data-type="task-completed">+ Completed</button>
                            <button class="btn btn-blue add-constraint" data-type="task-solvable">+ Solvable</button>
                            <button class="btn btn-gray add-constraint" data-type="max-executions">+ Max Executions</button>
                            <button class="btn btn-red add-constraint" data-type="not">+ Not</button>
                        </div>
                        <div class="constraints-container"></div>
                    </div>
                    <div>
                        <h4 class="section-title">Then execute these actions</h4>
                        <div class="button-group actions">
                            <button class="btn btn-green add-action" data-type="set-state">+ State</button>
                            <button class="btn btn-orange add-action" data-type="set-task-status">+ Task Status</button>
                            <button class="btn btn-blue add-action" data-type="play-sound">+ Play Sound</button>
                            <button class="btn btn-gray add-action" data-type="set-delay">+ Delay</button>
                            <button class="btn btn-gray add-action" data-type="add-to-state">+ Add to State</button>
                        </div>
                        <div class="actions-container"></div>
                    </div>
                </div>
            </div>
        `);
        ruleCard.attr('data-rule-id', ruleId);
        if (rule) {
            // Populate rule card with existing rule data
            ruleCard.find(".rule-card-header h3").text(`# Rule ${ruleId}`);
            rule.constraints.forEach(constraint => {
                const subCard = createSubCard(constraint.type, constraint.sensors, constraint.tasks, constraint);
                if (constraint.type === "not") {
                    constraint.nestedConstraints.forEach(nestedConstraint => {
                        const nestedCard = createSubCard("state-equals", constraint.sensors, constraint.tasks, nestedConstraint);
                        // Explicitly set the state select options and selected value for nested constraints
                        const sensorSelect = nestedCard.find(".sensor-select");
                        const stateSelect = nestedCard.find(".state-select");
                        
                        // Get the sensor's allowed values
                        const selectedSensor = sensorSelect.val();
                        const sensorOption = sensorSelect.find(`option[value="${selectedSensor}"]`);
                        const allowedValues = sensorOption.data("allowed-values") || '';
                        
                        // Populate state options
                        const states = allowedValues ? allowedValues.split(', ') : [];
                        stateSelect.html(states.map(state => 
                            `<option value="${state}" ${state === nestedConstraint.state ? 'selected' : ''}>${state}</option>`
                        ).join(''));
                        
                        subCard.find(".nested-constraints").append(nestedCard);
                    });
                }
                // Explicitly set the state select options and selected value
                if (constraint.type === "state-equals" || constraint.type === "set-state") {
                    const sensorSelect = subCard.find(".sensor-select");
                    const stateSelect = subCard.find(".state-select");
                    
                    // Get the sensor's allowed values
                    const selectedSensor = sensorSelect.val();
                    const sensorOption = sensorSelect.find(`option[value="${selectedSensor}"]`);
                    const allowedValues = sensorOption.data("allowed-values") || '';
                    
                    // Populate state options
                    const states = allowedValues ? allowedValues.split(', ') : [];
                    stateSelect.html(states.map(state => 
                        `<option value="${state}" ${state === constraint.state ? 'selected' : ''}>${state}</option>`
                    ).join(''));
                }
                
                ruleCard.find(".constraints-container").append(subCard);
            });
            
            // Similar modification for actions
            rule.actions.forEach(action => {
                const subCard = createSubCard(action.type, action.sensors, action.tasks, action);
                
                // Explicitly set the state select options and selected value for set-state actions
                if (action.type === "set-state") {
                    const sensorSelect = subCard.find(".sensor-select");
                    const stateSelect = subCard.find(".state-select");
                    
                    // Get the sensor's allowed values
                    const selectedSensor = sensorSelect.val();
                    const sensorOption = sensorSelect.find(`option[value="${selectedSensor}"]`);
                    const allowedValues = sensorOption.data("allowed-values") || '';
                    
                    // Populate state options
                    const states = allowedValues ? allowedValues.split(', ') : [];
                    stateSelect.html(states.map(state => 
                        `<option value="${state}" ${state === action.state ? 'selected' : ''}>${state}</option>`
                    ).join(''));
                }
                
                ruleCard.find(".actions-container").append(subCard);
            });
        }

        ruleCard.find(".delete-rule").click(function () {
            ruleCard.remove();
        });

        function generatePreview() {
            // Generate a human-readable preview for constraints
            const constraintsPreview = ruleCard
                .find(".constraints-container .sub-card")
                .map(function () {
                    const subCard = $(this);
                    if (subCard.text().includes("When this state")) {
                        return `<span style="background-color: #28a745; color: #fff; padding: 2px 4px; border-radius: 4px;">${subCard.find(".sensor-select").val()} is ${subCard.find(".state-select").val()}</span>`;
                    } else if (subCard.text().includes("When this task")) {
                        const task = subCard.find("select").val();
                        const states = subCard
                            .find("input[type=checkbox]:checked")
                            .map(function () {
                                return $(this).val();
                            })
                            .get()
                            .join(", ");
                        return `<span style="background-color: #fd7e14; color: #fff; padding: 2px 4px; border-radius: 4px;">${task} is ${states}</span>`;
                    } else if (subCard.text().includes("Max executions per game")) {
                        return `<span style="background-color: #6c757d; color: #fff; padding: 2px 4px; border-radius: 4px;">Max executions: ${subCard.find("input[type=number]").val()}</span>`;
                    }
                    return "";
                })
                .get()
                .join(" AND ");

            // Generate a human-readable preview for actions
            const actionsPreview = ruleCard
                .find(".actions-container .sub-card")
                .map(function () {
                    const subCard = $(this);
                    if (subCard.text().includes("Set state")) {
                        return `<span style="background-color: #28a745; color: #fff; padding: 2px 4px; border-radius: 4px;">Set ${subCard.find(".sensor-select").val()} to ${subCard.find(".state-select").val()}</span>`;
                    } else if (subCard.text().includes("Set task")) {
                        return `<span style="background-color: #fd7e14; color: #fff; padding: 2px 4px; border-radius: 4px;">Set task ${subCard.find("select").val()} to ${subCard.find("select:last").val()}</span>`;
                    } else if (subCard.text().includes("Play sound")) {
                        return `<span style="background-color: #007bff; color: #fff; padding: 2px 4px; border-radius: 4px;">Play ${subCard.find("input[type=text]").val()} at volume ${subCard.find("input[type=number]").val()}</span>`;
                    } else if (subCard.text().includes("Delay")) {
                        return `<span style="background-color: #6c757d; color: #fff; padding: 2px 4px; border-radius: 4px;">Wait ${subCard.find("input[type=number]").val()} seconds</span>`;
                    } else if (subCard.text().includes("Increase value of this state")) {
                        return `<span style="background-color: #6c757d; color: #fff; padding: 2px 4px; border-radius: 4px;">Increase ${subCard.find(".sensor-select").val()} by ${subCard.find("input[type=number]").val()}</span>`;
                    }
                    return "";
                })
                .get()
                .join(" ");

            // Update the header with a concise preview
            ruleCard.find(".rule-card-header h3").html(`# Rule ${ruleId} - When ${constraintsPreview}, do ${actionsPreview}`);
        }

        ruleCard.find(".rule-card-header").click(function () {
            const body = ruleCard.find(".rule-card-body");
            body.toggle();

            if (body.is(":visible")) {
                $(this).find("h3").text(`# Rule ${ruleId}`);
            } else {
                generatePreview();
            }
        });

        // Collapse the rule card by default and generate preview
        ruleCard.find(".rule-card-body").hide();
        generatePreview();

        $("#rules-container").append(ruleCard);
    }

    function filterRules() {
        const searchTerm = $("#search-input").val().toLowerCase();
        $(".rule-card").each(function () {
            const ruleCard = $(this);
            const ruleText = ruleCard.text().toLowerCase();
            if (ruleText.includes(searchTerm)) {
                ruleCard.show();
            } else {
                ruleCard.hide();
            }
        });
    }

    $("#search-input").on("input", filterRules);

    function createSubCard(type, sensors = [], tasks = [], data = null) {
        let subCardContent = "";
        if (type === "not") {
            subCardContent = `
                <h4>None of these constraints should be met:</h4>
                <div class="nested-constraints"></div>
                <button class="btn btn-green add-nested-constraint">+ Equals</button>
            `;
        
            const subCard = $(`<div class="sub-card not-constraint">
                ${subCardContent}
                <button class="delete-sub-card">Delete</button>
            </div>`);
        
            subCard.find(".add-nested-constraint").click(function () {
                fetchSensorsAndTasks().done(function (sensors, tasks) {
                    const nestedCard = createSubCard("state-equals", sensors[0], tasks[0]); // Default to "state-equals"
                    subCard.find(".nested-constraints").append(nestedCard);
                });
            });
        
            subCard.find(".delete-sub-card").click(function () {
                subCard.remove();
            });
        
            return subCard;
        }
        
        if (type === "state-equals" || type === "set-state") {
            const actionText = type === "state-equals" ? "When this state" : "Set state";
            const equalsText = type === "state-equals" ? "equals" : "to";
            
            // Group sensors by type
            const groupedSensors = sensors.reduce((acc, sensor) => {
                if (!acc[sensor.type]) acc[sensor.type] = [];
                acc[sensor.type].push(sensor);
                return acc;
            }, {});

            // Populate sensor options with headers
            const sensorOptions = Object.keys(groupedSensors).map(type => `
                <optgroup label="${type.charAt(0).toUpperCase() + type.slice(1)}">
                    ${groupedSensors[type].map(sensor => `
                        <option value="${sensor.name}" data-type="${sensor.type}" data-allowed-values="${sensor.allowed_values || ''}" ${data && data.sensor === sensor.name ? 'selected' : ''}>${sensor.name}</option>
                    `).join('')}
                </optgroup>
            `).join('');

            // Determine initial state options
            const initialStateOptions = data && sensors.find(sensor => sensor.name === data.sensor) 
                ? getStateOptions(sensors.find(sensor => sensor.name === data.sensor)) 
                : '';

            subCardContent = `
                ${actionText}
                <select class="sensor-select">
                    <option value="" disabled selected>Select sensor</option>
                    ${sensorOptions}
                </select>
                ${equalsText}
                <select class="state-select">
                    <option value="" disabled selected>Select state</option>
                    ${initialStateOptions}
                </select>
            `;
        } else if (type === "task-completed") {
            subCardContent = `
                When this task
                <select>
                    ${tasks.map(task => `<option value="${task.task}" ${data && data.task === task.task ? 'selected' : ''}>${task.task}</option>`).join('')}
                </select>
                has been
                <label><input type="checkbox" value="solved" ${data && data.states.includes('solved') ? 'checked' : ''}> Solved</label>
                <label><input type="checkbox" value="skipped" ${data && data.states.includes('skipped') ? 'checked' : ''}> Skipped</label>
                <label><input type="checkbox" value="auto-solved" ${data && data.states.includes('auto-solved') ? 'checked' : ''}> Auto-solved</label>
            `;
        } else if (type === "set-task-status") {
            subCardContent = `
                Set task
                <select>
                    ${tasks.map(task => `<option value="${task.task}" ${data && data.task === task.task ? 'selected' : ''}>${task.task}</option>`).join('')}
                </select>
                to
                <select>
                    <option value="solved" ${data && data.status === 'solved' ? 'selected' : ''}>Solved</option>
                    <option value="skipped" ${data && data.status === 'skipped' ? 'selected' : ''}>Skipped</option>
                    <option value="auto-solved" ${data && data.status === 'auto-solved' ? 'selected' : ''}>Auto-solved</option>
                </select>
            `;
        } else if (type === "play-sound") {
            subCardContent = `
                Play sound
                <input type="text" id="selected-sound" placeholder="Select sound..." readonly value="${data ? data.play_sound : ''}">
                <button type="button" class="select-sound-btn">Select Sound</button>
                <label for="volume">Volume:</label>
                <input type="number" id="volume" min="0" max="100" value="${data ? data.volume : 50}">
                <h3>Select Pi's:</h3>
                <div id="pi-list"></div>
            `;
        } else if (type === "set-delay") {
            subCardContent = `
                <label>Delay (seconds):</label>
                <input type="number" class="delay-input" value="${data ? data.delay : 0}">
            `;
        } else if (type === "add-to-state") {
            subCardContent = `
                Increase value of this state
                <select class="sensor-select">
                    ${sensors.map(sensor => `<option value="${sensor.name}" data-type="${sensor.type}" data-allowed-values="${sensor.allowed_values || ''}" ${data && data.sensor === sensor.name ? 'selected' : ''}>${sensor.name}</option>`).join('')}
                </select>
                by number
                <input type="number" placeholder="Enter number" value="${data ? data.increment : ''}">
            `;
            // Dynamically fill the state options based on the selected sensor type
            subCardContent += `
                <script>
                    $(document).ready(function() {
                        $(".sensor-select").last().change(function() {
                            const sensorType = $(this).find(":selected").data("type");
                            const allowedValues = $(this).find(":selected").data("allowed-values");
                            const states = allowedValues ? allowedValues.split(', ') : (stateOptions[sensorType] || []);
                            let optionsHtml = '';
                            states.forEach(state => {
                                optionsHtml += \`<option value="\${state}">\${state}</option>\`;
                            });
                            $(this).siblings(".state-select").html(optionsHtml);
                        });
        
                        // Trigger change event to populate states on initial load
                        $(".sensor-select").last().trigger("change");
                    });
                </script>
            `;
        } else if (type === "max-executions") {
            subCardContent = `
                Max executions per game
                <input type="number" placeholder="Enter max executions" value="${data ? data.max_executions : ''}">
            `;
        } else if (type === "state-config") {
            subCardContent = `
                <label for="pi">Pi</label>
                <input type="text" id="pi" placeholder="Enter Pi name" value="${data ? data.pi : ''}" ${data && data.type === 'logic' ? 'disabled' : ''} />

                <label for="pin">Pin</label>
                <input type="number" id="pin" placeholder="Enter pin number" value="${data ? data.pin : ''}" ${data && data.type === 'logic' ? 'disabled' : ''} />

                <label for="connection-type">Connection Type</label>
                <select id="connection-type" ${data && data.type === 'logic' ? 'disabled' : ''}>
                    <option value="NC" ${data && data.connectionType === 'NC' ? 'selected' : ''}>NC</option>
                    <option value="NO" ${data && data.connectionType === 'NO' ? 'selected' : ''}>NO</option>
                </select>
            `;
        }

        const subCard = $(`<div class="sub-card">
            ${subCardContent}
            <button class="move-up">↑</button>
            <button class="move-down">↓</button>
            <button class="delete-sub-card">Delete</button>
        </div>`);
        subCard.find('.sensor-select').on('change', function() {
            const selectedOption = $(this).find(':selected');
            const sensorType = selectedOption.data('type');
            const allowedValues = selectedOption.data('allowed-values');
            
            // Get state options
            let states = [];
            if (allowedValues) {
                states = allowedValues.split(', ');
            }
            
            // Populate state select
            const stateSelect = $(this).siblings('.state-select');
            stateSelect.empty();
            states.forEach(state => {
                stateSelect.append(`<option value="${state}">${state}</option>`);
            });
            
            // If there was a previously selected state, try to maintain it
            if (data && data.state && states.includes(data.state)) {
                stateSelect.val(data.state);
            }
        });
        subCard.find('.select-sound-btn').click(function () {  
            $('#sound-popup').show();
            loadSounds();
        });

        subCard.find('.delete-sub-card').click(function () {
            subCard.remove();
        });

        subCard.find('.move-up').click(function () {
            const currentCard = $(this).closest('.sub-card');
            currentCard.prev('.sub-card').before(currentCard);
        });

        subCard.find('.move-down').click(function () {
            const currentCard = $(this).closest('.sub-card');
            currentCard.next('.sub-card').after(currentCard);
        });

        if (type === "play-sound" && data) {
            loadPis().then(() => {
                data.pi.forEach(pi => {
                    subCard.find(`#pi-list input[value="${pi}"]`).prop('checked', true);
                });
            });
        }

        return subCard;
    }

    function loadSounds() {
        $.get('/get_sounds', function (sounds) {
            const soundList = $('#sound-list');
            soundList.empty();
            sounds.forEach(sound => {
                const soundButton = $(`<button class="sound-button">${sound}</button>`);
                soundButton.click(function () {
                    $('#selected-sound').val(sound);
                    $('#sound-popup').hide();
                });
                soundList.append(soundButton);
            });
        });
    }

    function loadPis() {
        console.log("Calling loadPis()");
        return $.get(`/get_raspberry_pis/${roomName}`, function (pis) {
            console.log("Received Pis:", pis);
            const piList = $('#pi-list');
            piList.empty();
            pis.forEach(pi => {
                if (pi.services.includes('sound')) {
                    const piCheckbox = $(`<label><input type="checkbox" value="${pi.hostname}"> ${pi.hostname}</label>`);
                    piList.append(piCheckbox);
                }
            });
        }).fail(function (jqXHR, textStatus, errorThrown) {
            console.error("Failed to load Pis:", textStatus, errorThrown);
        });
    }
    function getStateOptions(sensor, selectedValue = null) {
        const allowedValues = sensor.allowed_values ? sensor.allowed_values.split(', ') : [];
        return allowedValues.map(state => 
            `<option value="${state}" ${state === selectedValue ? 'selected' : ''}>${state}</option>`
        ).join('');
    }

    function fetchSensorsAndTasks() {
        return $.when(
            $.get(`/get_sensors/${roomName}`),
            $.get(`/get_tasks/${roomName}`)
        );
    }

    function getRulesData() {
        const rules = [];
        $("#rules-container .rule-card").each(function () {
            const ruleCard = $(this);
            const constraints = [];
    
            ruleCard.find(".constraints-container .sub-card").each(function () {
                const subCard = $(this);
                const constraint = {};
    
                // Handle "not" constraints separately
                if (subCard.hasClass("not-constraint")) {
                    constraint.type = "not";
                    constraint.nestedConstraints = [];
                    subCard.find(".nested-constraints .sub-card").each(function () {
                        const nestedCard = $(this);
                        constraint.nestedConstraints.push({
                            sensor: nestedCard.find(".sensor-select").val(),
                            state: nestedCard.find(".state-select").val(),
                        });
                    });
                    constraints.push(constraint); // Add only the "not" constraint
                } else if (!subCard.closest(".nested-constraints").length) {
                    // Add other constraints only if they are not inside a "not" block
                    if (subCard.text().includes("When this state")) {
                        constraint.type = "state-equals";
                        constraint.sensor = subCard.find(".sensor-select").val();
                        constraint.state = subCard.find(".state-select").val();
    
                } else if (subCard.text().includes("When this task")) {
                    constraint.type = "task-completed";
                    constraint.task = subCard.find("select").val();
                    constraint.states = subCard.find("input[type=checkbox]:checked").map(function () {
                        return $(this).val();
                    }).get();
                } else if (subCard.text().includes("Max executions per game")) {
                    constraint.type = "max-executions";
                    constraint.max_executions = subCard.find("input[type=number]").val();
                }
                constraints.push(constraint);
            }
        });
        const actions = [];
            // Extract actions
            ruleCard.find(".actions-container .sub-card").each(function () {
                const subCard = $(this);
                const action = {};
            
                if (subCard.text().includes("Set state")) {
                    action.sensor = subCard.find(".sensor-select").val();
                    action.state = subCard.find(".state-select").val();
                } else if (subCard.text().includes("Set task")) {
                    action.task = subCard.find("select").val();
                    action.status = subCard.find("select:last").val();
                } else if (subCard.text().includes("Play sound")) {
                    action.play_sound = subCard.find("#selected-sound").val();
                    action.volume = subCard.find("#volume").val();
                    action.pi = subCard.find("#pi-list input:checked").map(function () {
                        return $(this).val();
                    }).get();
                } else if (subCard.text().includes("Delay")) {
                    action.delay = subCard.find("input[type=number]").val();
                } else if (subCard.text().includes("Increase value of this state")) {
                    action.sensor = subCard.find(".sensor-select").val();
                    action.increment = subCard.find("input[type=number]").val();
                }
            
                actions.push(action);
            });
        
            // Build rule object
            rules.push({
                id: ruleCard.data('rule-id'),
                sensor_name: ruleCard.find(".rule-card-header h3").text().trim(),
                constraints: constraints,
                actions: actions,
            });
        });
    
        return rules;
    }

    function saveRules() {
        const rules = getRulesData();
        $.ajax({
            url: `/save_rules/${roomName}`,
            type: "POST",
            contentType: "application/json",
            data: JSON.stringify(rules),
            success: function () {
                alert("Rules saved successfully!");
            },
            error: function () {
                alert("Failed to save rules.");
            },
        });
    }

    function loadRules() {
        $.get(`/get_rules/${roomName}`, function (rules) {
            fetchSensorsAndTasks().done(function (sensors, tasks) {
                rules.forEach(rule => {
                    rule.constraints.forEach(constraint => {
                        constraint.type = getConstraintType(constraint);
                        constraint.sensors = sensors[0]; // Ensure sensors are correctly assigned
                        constraint.tasks = tasks[0]; // Ensure tasks are correctly assigned
                    });
                    rule.actions.forEach(action => {
                        action.type = getActionType(action);
                        action.sensors = sensors[0]; // Ensure sensors are correctly assigned
                        action.tasks = tasks[0]; // Ensure tasks are correctly assigned
                    });
                    createRuleCard(rule);
                    console.log(rule);
                    ruleIdCounter = Math.max(ruleIdCounter, rule.id + 1);
                });
            });
        });
    }

    function getConstraintType(constraint) {
        if (constraint.sensor && constraint.state) {
            return "state-equals";
        } else if (constraint.task && constraint.states) {
            return "task-completed";
        } else if (constraint.max_executions) {
            return "max-executions";
        } else if (constraint.nestedConstraints) {
            return "not";
        }
        return "";
    }

    function getActionType(action) {
        if (action.sensor && action.state) {
            return "set-state";
        } else if (action.task && action.status) {
            return "set-task-status";
        } else if (action.play_sound && action.volume) {
            return "play-sound";
        } else if (action.delay) {
            return "set-delay";
        } else if (action.sensor && action.increment) {
            return "add-to-state";
        }
        return "";
    }

    $("#add-rule-btn").click(function () {
        createRuleCard();
    });

    $(document).on("click", ".add-constraint", function () {
        fetchSensorsAndTasks().done(function (sensors, tasks) {
            const subCard = createSubCard($(this).data("type"), sensors[0], tasks[0]);
            $(this).closest(".rule-card").find(".constraints-container").append(subCard);
        }.bind(this));
    });

    $(document).on("click", ".add-action", function () {
        fetchSensorsAndTasks().done(function (sensors, tasks) {
            const subCard = createSubCard($(this).data("type"), sensors[0], tasks[0]);
            $(this).closest(".rule-card").find(".actions-container").append(subCard);
        }.bind(this));
    });

    $("#save-rules-btn").click(saveRules);

    // Load existing rules on page load
    loadRules();
    
        // Default allowed values for each section
        const defaultValues = {
            light: 'on, off',
            Sensor: 'Triggered, Not Triggered',
            maglock: 'locked, unlocked',
            button: 'Triggered, Not Triggered',
            logic: '',
            rfid: 'Detected, Not Detected',
            different: 'Active, Inactive',
        };
    
        // Fetch available Pis from raspberry_pis.json
        function fetchAvailablePis() {
            return $.get(`/get_raspberry_pis/${roomName}`);
        }
    
        // Add State functionality
        $('.add-state-btn').click(function() {
            const section = $(this).data('section');
            const allowedValues = defaultValues[section] || '';
            fetchAvailablePis().done(function(pis) {
                const piOptions = section !== 'logic' ? pis.map(pi => `<option value="${pi.hostname}">${pi.hostname}</option>`).join('') : '';
                const stateCard = `
                    <div class="state-card">
                        <div class="state-card-header">
                            <h3>${section} State</h3>
                        </div>
                        <div class="state-card-body">
                            <label for="name">State Name</label>
                            <input type="text" id="name" placeholder="Enter state name" />
    
                            <label for="type">State Type</label>
                            <input type="text" id="type" value="${section}" readonly />
    
                            <label for="allowed-values">Allowed Values</label>
                            <input type="text" id="allowed-values" value="${allowedValues}" />
    
                            ${section !== 'logic' ? `
                            <label for="pi">Pi</label>
                            <select id="pi">${piOptions}</select>
    
                            <label for="pin">Pin</label>
                            <input type="number" id="pin" placeholder="Enter pin number" />
    
                            <label for="connection-type">Connection Type</label>
                            <select id="connection-type">
                                <option value="NC">NC</option>
                                <option value="NO">NO</option>
                            </select>
                            ` : ''}
    
                            <button class="remove-state-btn">Remove</button>
                        </div>
                    </div>
                `;
                $('#' + section + ' .state-list').append(stateCard);
                $('.state-card-body').hide();
            });
        });
    
        // Remove State functionality
        $(document).on('click', '.remove-state-btn', function() {
            $(this).closest('.state-card').remove();
        });
    
        // Toggle state card body visibility
        $(document).on('click', '.state-card-header', function() {
            const body = $(this).siblings('.state-card-body');
            body.toggle();
        });
    
        // Initialize with rules section visible
        $('#rules-container').show();
        $('#states').hide();
    
        // Populate state editor with existing states
        function populateStates() {
            $.get(`/get_sensors/${roomName}`, function (sensors) {
                sensors.forEach(sensor => {
                    let section = sensor.type;
                    if (sensor.type === "different" || sensor.type === "rfid") {
                        section = sensor.type;
                    }
                    const stateCard = `
                        <div class="state-card">
                            <div class="state-card-header">
                                <h3>${sensor.name}</h3>
                            </div>
                            <div class="state-card-body">
                                <label for="name">State Name</label>
                                <input type="text" id="name" value="${sensor.name}" />
    
                                <label for="type">State Type</label>
                                <input type="text" id="type" value="${section}" />
    
                                <label for="allowed-values">Allowed Values</label>
                                <input type="text" id="allowed-values" value="${sensor.allowed_values || defaultValues[section] || ''}" />
    
                                <label for="pi">Pi</label>
                                <input type="text" id="pi" value="${sensor.pi}" />
    
                                <label for="pin">Pin</label>
                                <input type="number" id="pin" value="${sensor.pin}" />
    
                                <label for="connection-type">Connection Type</label>
                                <select id="connection-type">
                                    <option value="NC" ${sensor.connection_type === 'NC' ? 'selected' : ''}>NC</option>
                                    <option value="NO" ${sensor.connection_type === 'NO' ? 'selected' : ''}>NO</option>
                                </select>
    
                                <button class="remove-state-btn">Remove</button>
                            </div>
                        </div>
                    `;
                    $('#' + section + ' .state-list').append(stateCard);
                });
                $('.state-card-body').hide();
            });
        }
    
        // Call populateStates on page load
        populateStates();
    
        // Save states functionality
        function saveStates() {
            const states = [];
            $(".state-card").each(function () {
                const stateCard = $(this);
                const state = {
                    name: stateCard.find("#name").val(),
                    type: stateCard.find("#type").val(),
                    allowed_values: stateCard.find("#allowed-values").val(),
                    pi: stateCard.find("#pi").val(),
                    pin: stateCard.find("#pin").val(),
                    connection_type: stateCard.find("#connection-type").val(),
                    state: "init"
                };
                states.push(state);
            });
    
            $.ajax({
                url: `/save_states/${roomName}`,
                type: "POST",
                contentType: "application/json",
                data: JSON.stringify(states),
                success: function () {
                    alert("States saved successfully!");
                },
                error: function () {
                    alert("Failed to save states.");
                },
            });
        }
    
        $("#save-states-btn").click(saveStates);
    
        // Ensure loadPis() is called when the add-sound button is pressed
        $(document).on("click", ".add-action[data-type='play-sound']", function () {
            loadPis();
        });
});
$(document).on('change', '.sensor-select', function() {
    const sensorOption = $(this).find(':selected');
    const allowedValues = sensorOption.data('allowed-values') || '';
    const stateSelect = $(this).siblings('.state-select');
    
    const states = allowedValues ? allowedValues.split(', ') : [];
    const optionsHtml = states.map(state => 
        `<option value="${state}">${state}</option>`
    ).join('');
    
    stateSelect.html(optionsHtml);
});