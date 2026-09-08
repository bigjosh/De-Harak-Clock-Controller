/* ES5 and XMLHttpRequest keep this usable by the controller's older browsers. */
(function () {
    "use strict";

    var endpoint = "cgi-bin/dld-trial.cgi";
    var grid = document.getElementById("panel-grid");
    var gridBody = document.getElementById("panel-grid-body");
    var status = document.getElementById("deploy-status");
    var output = document.getElementById("deploy-output");
    var outputNote = document.getElementById("output-note");
    var buttons = [];
    var token = null;
    var busy = true;
    var timer = null;

    function setStatus(message, kind) {
        status.className = "alert alert-" + (kind || "info");
        if (status.textContent !== message) { status.textContent = message; }
    }

    function setBusy(value) {
        var i;
        busy = value;
        grid.setAttribute("aria-busy", value ? "true" : "false");
        for (i = 0; i < buttons.length; i += 1) { buttons[i].disabled = value; }
    }

    function later(callback, delay) {
        if (timer !== null) { window.clearTimeout(timer); }
        timer = window.setTimeout(function () { timer = null; callback(); }, delay);
    }

    function request(method, query, data, callback) {
        var xhr = new XMLHttpRequest();
        var finished = false;
        function finish(error) {
            var response = null;
            if (finished) { return; }
            finished = true;
            if (!error) {
                try { response = JSON.parse(xhr.responseText); }
                catch (ignored) { error = "The service returned an unreadable response."; }
            }
            callback(xhr.status || 0, response, error);
        }
        xhr.open(method, endpoint + query, true);
        xhr.timeout = 15000;
        xhr.setRequestHeader("Accept", "application/json");
        if (data !== null) { xhr.setRequestHeader("Content-Type", "application/json"); }
        xhr.onreadystatechange = function () { if (xhr.readyState === 4) { finish(null); } };
        xhr.onerror = function () { finish("Unable to reach the deployment service."); };
        xhr.ontimeout = function () { finish("The deployment service took too long to reply."); };
        try { xhr.send(data === null ? null : JSON.stringify(data)); }
        catch (ignored) { finish("Unable to send the request to the deployment service."); }
    }

    function validJob(job) {
        return job && typeof job.id === "string" && /^[A-Za-z0-9_-]{1,128}$/.test(job.id) &&
            typeof job.digit === "string" && /^(h(?:0[1-9]|1[0-2])|m[0-5][0-9])$/i.test(job.digit) &&
            /^(running|succeeded|failed)$/.test(job.state) && typeof job.output === "string";
    }

    function rememberJob(id) {
        var hash = "#job=" + encodeURIComponent(id);
        if (window.location.hash === hash) { return; }
        if (window.history && window.history.replaceState) {
            window.history.replaceState(null, "", hash);
        } else { window.location.replace(hash); }
    }

    function savedJob() {
        var match = /^#job=([A-Za-z0-9_-]{1,128})$/.exec(window.location.hash);
        return match ? match[1] : null;
    }

    function showJob(job) {
        var i;
        var selected;
        var nearBottom = output.scrollHeight - output.scrollTop - output.clientHeight < 60;
        rememberJob(job.id);
        for (i = 0; i < buttons.length; i += 1) {
            selected = buttons[i].getAttribute("data-digit") === job.digit.toLowerCase();
            buttons[i].className = "btn btn-default panel-digit" + (i < 12 ? " hour" : "") + (selected ? " active" : "");
            buttons[i].setAttribute("aria-pressed", selected ? "true" : "false");
        }
        if (output.textContent !== job.output) {
            output.textContent = job.output || "Waiting for deployment output\u2026";
            if (nearBottom) { output.scrollTop = output.scrollHeight; }
        }
        outputNote.hidden = !job.truncated;
        outputNote.textContent = job.truncated ? "Only the most recent console output is shown." : "";
        if (job.state === "running") {
            setBusy(true);
            setStatus("Deploying " + job.digit.toUpperCase() + "\u2026 Output updates automatically.");
            later(function () { pollJob(job.id); }, 1000);
        } else {
            setBusy(true);
            setStatus(job.digit.toUpperCase() + (job.state === "succeeded" ? " trial deployment completed." :
                " trial deployment failed" + (typeof job.exit_code === "number" ? " (exit " + job.exit_code + ")" : "") + ". See the output below."),
                job.state === "succeeded" ? "success" : "danger");
            loadSession(null, true, null);
        }
    }

    function pollJob(id) {
        request("GET", "?action=status&job=" + encodeURIComponent(id), null,
            function (code, data, error) {
                if (!error && code === 200 && validJob(data && data.job)) { showJob(data.job); return; }
                if (code === 404 || code === 410) {
                    setStatus("This deployment's saved output is no longer available. Checking for an active deployment\u2026", "warning");
                    loadSession(null, true, null);
                    return;
                }
                setBusy(true);
                setStatus("Progress is temporarily unavailable. Retrying automatically; the deployment may still be running.", "warning");
                later(function () { pollJob(id); }, 2000);
            });
    }

    /* Session/status recovery only reads state. It never repeats a deployment POST. */
    function loadSession(preferredId, preserveStatus, uncertainDigit) {
        setBusy(true);
        request("GET", "?action=session", null, function (code, data, error) {
            if (error || code !== 200 || !data || typeof data.token !== "string" || !data.token) {
                setStatus((data && typeof data.error === "string" ? data.error :
                    "Cannot connect to the deployment service.") + " Retrying automatically\u2026", "warning");
                later(function () { loadSession(preferredId, preserveStatus, uncertainDigit); }, 2000);
                return;
            }
            token = data.token;
            if (validJob(data.active_job)) { showJob(data.active_job); return; }
            if (preferredId) { pollJob(preferredId); return; }
            setBusy(false);
            if (uncertainDigit) {
                setStatus("The start request for " + uncertainDigit.toUpperCase() + " could not be confirmed, and no deployment is active. It has not been retried. Check the digit before selecting it again.", "warning");
            } else if (!preserveStatus) {
                setStatus("Ready. Choose a panel to start its trial deployment.");
            }
        });
    }

    function startDeploy(digit) {
        var actionToken;
        if (busy || !token) { return; }
        setBusy(true);
        if (timer !== null) { window.clearTimeout(timer); timer = null; }
        actionToken = token;
        token = null;
        setStatus("Starting trial deployment to " + digit.toUpperCase() + "\u2026");
        request("POST", "", {digit: digit, token: actionToken}, function (code, data, error) {
            if (!error && (code === 200 || code === 202) && validJob(data && data.job)) { showJob(data.job); return; }
            if (!error && validJob(data && data.active_job)) { showJob(data.active_job); return; }
            if (error || code === 0 || code >= 500 || (code >= 200 && code < 300)) {
                setStatus("The start request could not be confirmed. Checking for an active deployment; this request will not be repeated.", "warning");
                loadSession(null, true, digit);
                return;
            }
            setStatus(data && typeof data.error === "string" ? data.error : "The deployment request was refused. Please try again after checking the service.", "danger");
            loadSession(null, true, null);
        });
    }

    function makeGrid() {
        var row, col, index, name, tr, td, button;
        for (row = 0; row < 6; row += 1) {
            tr = document.createElement("tr");
            for (col = 0; col < 12; col += 1) {
                index = row * 12 + col;
                name = row === 0 ? "h" + ("0" + (col + 1)).slice(-2) : "m" + ("0" + (index - 12)).slice(-2);
                td = document.createElement("td");
                button = document.createElement("button");
                button.type = "button";
                button.className = "btn btn-default panel-digit" + (row === 0 ? " hour" : "");
                button.textContent = name.toUpperCase();
                button.disabled = true;
                button.setAttribute("data-digit", name);
                button.setAttribute("aria-label", "Trial deploy to " + name.toUpperCase() + ", FFS index " + index);
                button.setAttribute("aria-pressed", "false");
                button.onclick = function () { startDeploy(this.getAttribute("data-digit")); };
                buttons.push(button);
                td.appendChild(button);
                tr.appendChild(td);
            }
            gridBody.appendChild(tr);
        }
    }

    makeGrid();
    loadSession(savedJob(), false, null);
}());
