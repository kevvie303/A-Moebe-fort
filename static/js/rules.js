$(document).ready(function () {
    const roomName = $("#room-name").text().trim();
    let ruleIdCounter = 1;

    // Define state options by sensor type
    const stateOptionsByType = {
        maglock: ["Locked", "Unlocked"],
        Sensor: ["Triggered", "Not Triggered"],
        light: ["On", "Off"],
        button: ["Triggered", "Not Triggered"],
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

        ruleCard.find(".rule-card-header").click(function () {
            const body = ruleCard.find(".rule-card-body");
            body.toggle();
            if (body.is(":visible")) {
                $(this).find("h3").text(`# Rule ${ruleId}`);
            } else {
                const constraintsPreview = rule.constraints.map(c => `${c.sensor} ${c.state || c.states.join(", ")}`).join(" + ");
                const actionsPreview = rule.actions.map(a => `${a.sensor || a.task} ${a.state || a.status || a.play_sound}`).join(" and ");
                $(this).find("h3").text(`# Rule ${ruleId} - When ${constraintsPreview}, do ${actionsPreview}`);
            }
        });

        $("#rules-container").append(ruleCard);
    }

    function createSubCard(type, sensors = [], tasks = [], data = null) {
        let subCardContent = "";

        if (type === "state-equals") {
            subCardContent = `
                When this state
                <select class="sensor-select">
                    ${sensors.map(sensor => `<option value="${sensor.name}" data-type="${sensor.type}" ${data && data.sensor === sensor.name ? 'selected' : ''}>${sensor.name}</option>`).join('')}
                </select>
                equals
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
        }

        return $(`<div class="sub-card">${subCardContent}<button class="delete-sub-card">Delete</button></div>`)
            .on("click", ".delete-sub-card", function () {
                $(this).parent().remove();
            });
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
});
