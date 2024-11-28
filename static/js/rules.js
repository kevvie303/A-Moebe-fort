$(document).ready(function () {
    const roomName = $("#room-name").text().trim();
    let ruleIdCounter = 1;

    // Define state options by sensor type
    const stateOptionsByType = {
        maglock: ["Locked", "Unlocked"],
        Sensor: ["Triggered", "Not Triggered"],
        light: ["On", "Off"],
        button: ["Triggered", "Not Triggered"],
        rfid: ["Detected", "Not Detected"],
        different: ["Active", "Inactive"],
    };

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
                ruleCard.find(".constraints-container").append(subCard);
            });
            rule.actions.forEach(action => {
                const subCard = createSubCard(action.type, action.sensors, action.tasks, action);
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
                    } else if (subCard.text().includes("Wait for")) {
                        return `<span style="background-color: #6c757d; color: #fff; padding: 2px 4px; border-radius: 4px;">Wait ${subCard.find("input[type=number]").val()} seconds</span>`;
                    } else if (subCard.text().includes("Increase value of this state")) {
                        return `<span style="background-color: #6c757d; color: #fff; padding: 2px 4px; border-radius: 4px;">Increase ${subCard.find(".sensor-select").val()} by ${subCard.find("input[type=number]").val()}</span>`;
                    }
                    return "";
                })
                .get()
                .join(" AND ");

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

        if (type === "state-equals") {
            subCardContent = `
                When this state
                <select class="sensor-select">
                    ${sensors.map(sensor => `<option value="${sensor.name}" data-type="${sensor.type}" data-allowed-values="${sensor.allowed_values || ''}" ${data && data.sensor === sensor.name ? 'selected' : ''}>${sensor.name}</option>`).join('')}
                </select>
                equals
                <select class="state-select">
                    ${data && sensors.find(sensor => sensor.name === data.sensor) ? getStateOptions(sensors.find(sensor => sensor.name === data.sensor)) : ''}
                </select>
            `;
            // Dynamically fill the state options based on the selected sensor type
            subCardContent += `
                <script>
                    $(document).ready(function() {
                        $(".sensor-select").last().change(function() {
                            const sensorType = $(this).find(":selected").data("type");
                            const allowedValues = $(this).find(":selected").data("allowed-values");
                            const stateOptions = ${JSON.stringify(stateOptionsByType)};
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
        } else if (type === "task-completed") {
            subCardContent = `
                When this task
                <select>
                    ${tasks.map(task => `<option value="${task.task}" ${data && data.sensor === task.task ? 'selected' : ''}>${task.task}</option>`).join('')}
                </select>
                has been
                <label><input type="checkbox" value="solved" ${data && data.states.includes('solved') ? 'checked' : ''}> Solved</label>
                <label><input type="checkbox" value="skipped" ${data && data.states.includes('skipped') ? 'checked' : ''}> Skipped</label>
                <label><input type="checkbox" value="auto-solved" ${data && data.states.includes('auto-solved') ? 'checked' : ''}> Auto-solved</label>
            `;
        } else if (type === "set-state") {
            // For set-state action, create dropdowns for both sensor and state
            subCardContent = `
                Set state
                <select class="sensor-select">
                    ${sensors.map(sensor => `<option value="${sensor.name}" data-type="${sensor.type}" ${data && data.sensor === sensor.name ? 'selected' : ''}>${sensor.name}</option>`).join('')}
                </select>
                to
                <select class="state-select">
                    ${data && sensors.find(sensor => sensor.name === data.sensor) ? stateOptionsByType[sensors.find(sensor => sensor.name === data.sensor).type].map(state => `<option value="${state}" ${data.state === state ? 'selected' : ''}>${state}</option>`).join('') : ''}
                </select>
            `;
            // Dynamically fill the state options based on the selected sensor type
            subCardContent += `
                <script>
                    $(document).ready(function() {
                        $(".sensor-select").last().change(function() {
                            const sensorType = $(this).find(":selected").data("type");
                            const stateOptions = ${JSON.stringify(stateOptionsByType)};
                            const states = stateOptions[sensorType] || [];
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
                <input type="text" placeholder="Enter sound file" value="${data ? data.play_sound : ''}">
                with volume
                <input type="number" placeholder="Enter volume" value="${data ? data.volume : ''}">
            `;
        } else if (type === "set-delay") {
            subCardContent = `
                Wait for
                <input type="number" placeholder="Enter seconds" value="${data ? data.delay : ''}">
                seconds
            `;
        } else if (type === "add-to-state") {
            subCardContent = `
                Increase value of this state
                <select class="sensor-select">
                    ${sensors.filter(sensor => sensor.type === "different").map(sensor => `<option value="${sensor.name}" data-type="${sensor.type}" ${data && data.sensor === sensor.name ? 'selected' : ''}>${sensor.name}</option>`).join('')}
                </select>
                by number
                <input type="number" placeholder="Enter number" value="${data ? data.increment : ''}">
            `;
        } else if (type === "max-executions") {
            subCardContent = `
                Max executions per game
                <input type="number" placeholder="Enter max executions" value="${data ? data.max_executions : ''}">
            `;
        } else if (type === "state-config") {
            subCardContent = `
                <label for="pi">Pi</label>
                <input type="text" id="pi" placeholder="Enter Pi name" value="${data ? data.pi : ''}" />

                <label for="pin">Pin</label>
                <input type="number" id="pin" placeholder="Enter pin number" value="${data ? data.pin : ''}" />

                <label for="connection-type">Connection Type</label>
                <select id="connection-type">
                    <option value="NC" ${data && data.connectionType === 'NC' ? 'selected' : ''}>NC</option>
                    <option value="NO" ${data && data.connectionType === 'NO' ? 'selected' : ''}>NO</option>
                </select>
            `;
        }

        return $(`<div class="sub-card">${subCardContent}<button class="delete-sub-card">Delete</button></div>`)
            .on("click", ".delete-sub-card", function () {
                $(this).parent().remove();
            });
    }

    function getStateOptions(sensor) {
        const allowedValues = sensor.allowed_values ? sensor.allowed_values.split(', ') : [];
        const stateOptions = stateOptionsByType[sensor.type] || [];
        return allowedValues.length > 0 ? allowedValues.map(state => `<option value="${state}">${state}</option>`).join('') : stateOptions.map(state => `<option value="${state}">${state}</option>`).join('');
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
            const actions = [];
    
            // Extract constraints
            ruleCard.find(".constraints-container .sub-card").each(function () {
                const subCard = $(this);
                const constraint = {};
    
                if (subCard.text().includes("When this state")) {
                    constraint.sensor = subCard.find(".sensor-select").val();
                    constraint.state = subCard.find(".state-select").val();
                } else if (subCard.find("select").length) {
                    // For task-completed constraint
                    constraint.sensor = subCard.find("select").val();
                    constraint.states = [];
                    subCard.find("input[type=checkbox]:checked").each(function () {
                        constraint.states.push($(this).val());
                    });
                } else if (subCard.text().includes("Max executions per game")) {
                    constraint.max_executions = subCard.find("input[type=number]").val();
                }
                constraints.push(constraint);
            });
    
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
                    action.play_sound = subCard.find("input[type=text]").val();
                    action.volume = subCard.find("input[type=number]").val();
                } else if (subCard.text().includes("Wait for")) {
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
                    ruleIdCounter = Math.max(ruleIdCounter, rule.id + 1);
                });
            });
        });
    }

    function getConstraintType(constraint) {
        if (constraint.sensor && constraint.state) {
            return "state-equals";
        } else if (constraint.sensor && constraint.states) {
            return "task-completed";
        } else if (constraint.max_executions) {
            return "max-executions";
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

    // Toggle between Rules and States
    $('.toggle-button').click(function() {
        $('.toggle-button').removeClass('active');
        $(this).addClass('active');
        const target = $(this).data('target');
        if (target === 'rules') {
            $('#rules-container').show();
            $('#search-input').show();
            $('#add-rule-btn').show();
            $('#save-rules-btn').show();
            $('#states').hide();
        } else {
            $('#rules-container').hide();
            $('#search-input').hide();
            $('#add-rule-btn').hide();
            $('#save-rules-btn').hide();
            $('#states').show();
        }
    });

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
            const piOptions = pis.map(pi => `<option value="${pi.hostname}">${pi.hostname}</option>`).join('');
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

                        <label for="pi">Pi</label>
                        <select id="pi">${piOptions}</select>

                        <label for="pin">Pin</label>
                        <input type="number" id="pin" placeholder="Enter pin number" />

                        <label for="connection-type">Connection Type</label>
                        <select id="connection-type">
                            <option value="NC">NC</option>
                            <option value="NO">NO</option>
                        </select>

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
                            <input type="text" id="name" value="${sensor.name}" readonly />

                            <label for="type">State Type</label>
                            <input type="text" id="type" value="${section}" readonly />

                            <label for="allowed-values">Allowed Values</label>
                            <input type="text" id="allowed-values" value="${sensor.allowed_values || defaultValues[section] || ''}" />

                            <label for="pi">Pi</label>
                            <input type="text" id="pi" value="${sensor.pi}" readonly />

                            <label for="pin">Pin</label>
                            <input type="number" id="pin" value="${sensor.pin}" readonly />

                            <label for="connection-type">Connection Type</label>
                            <select id="connection-type" disabled>
                                <option value="NC" ${sensor.connectionType === 'NC' ? 'selected' : ''}>NC</option>
                                <option value="NO" ${sensor.connectionType === 'NO' ? 'selected' : ''}>NO</option>
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
});
