(function () {

  let lastExitLine = "";
  let lastEcho = { text: "", time: 0 };

  function shouldEchoCommand(cmd) {
    const normalized = (cmd || "").trim();
    if (!normalized) {
      return false;
    }

    const lowered = normalized.toLowerCase();
    if (lowered.startsWith("connect ") || lowered.startsWith("create ")) {
      return false;
    }

    return true;
  }

  function echoCommand(cmd) {
    const normalized = (cmd || "").trim();
    if (!shouldEchoCommand(normalized)) {
      return;
    }

    const now = Date.now();
    if (lastEcho.text === normalized && now - lastEcho.time < 250) {
      return;
    }
    lastEcho = { text: normalized, time: now };

    const msgWindow = document.querySelector("#messagewindow");
    if (!msgWindow) {
      return;
    }

    const line = document.createElement("div");
    line.className = "cmd-echo";
    line.textContent = `> ${normalized}`;
    msgWindow.appendChild(line);
    msgWindow.scrollTop = msgWindow.scrollHeight;
  }

  function getInputField() {
    return document.querySelector("#inputfield");
  }

  function hookPluginSend() {
    if (!window.plugin_handler || typeof window.plugin_handler.onSend !== "function") {
      return false;
    }

    if (window.plugin_handler._dragonsireEchoWrapped) {
      return true;
    }

    const originalOnSend = window.plugin_handler.onSend;
    window.plugin_handler.onSend = function (line) {
      echoCommand(line);
      return originalOnSend.call(this, line);
    };
    window.plugin_handler._dragonsireEchoWrapped = true;
    return true;
  }

  function initEchoHook() {
    if (hookPluginSend()) {
      return;
    }

    let attempts = 0;
    const timer = setInterval(() => {
      attempts += 1;
      if (hookPluginSend() || attempts >= 20) {
        clearInterval(timer);
      }
    }, 250);
  }

  function sendCommand(cmd) {
    echoCommand(cmd);
    if (window.Evennia && Evennia.msg) {
      Evennia.msg("text", [cmd], {});
    } else {
      console.warn("Evennia.msg not ready");
    }
  }

  function getLatestExitLine() {
    const msgWindow = document.querySelector("#messagewindow");
    if (!msgWindow) return "";

    const lines = msgWindow.innerText.split("\n");

    for (let i = lines.length - 1; i >= 0; i--) {
      let line = lines[i].trim();
      if (line.startsWith("Exits:")) {
        return line;
      }
    }

    return "";
  }

  function parseExits(line) {
    if (!line) return [];

    return line
      .replace(/^Exits:\s*/i, "")
      .replace(/\band\b/g, "")
      .replace(/\./g, "")
      .split(",")
      .map(e => e.trim().toLowerCase())
      .filter(Boolean);
  }

  function updateCompass() {
    const exitLine = getLatestExitLine();

    // Only update if changed (prevents spam)
    if (!exitLine || exitLine === lastExitLine) return;

    lastExitLine = exitLine;

    const exits = parseExits(exitLine);

    document.querySelectorAll("#compass button").forEach(btn => {
      const dir = btn.dataset.dir.toLowerCase();

      if (exits.includes(dir)) {
        btn.disabled = false;
        btn.classList.remove("disabled");
      } else {
        btn.disabled = true;
        btn.classList.add("disabled");
      }
    });
  }

  function setupCompass() {
    document.querySelectorAll("#compass button").forEach(btn => {
      btn.addEventListener("click", (e) => {
        e.preventDefault();
        e.stopPropagation();

        if (btn.disabled) return;

        sendCommand(btn.dataset.dir);

        // update shortly after movement (no polling needed)
        setTimeout(updateCompass, 200);
      });
    });
  }

  function init() {
    setupCompass();
    initEchoHook();

    // initial update after load
    setTimeout(updateCompass, 500);

    // LOW frequency safety update (not spammy)
    setInterval(updateCompass, 1000);
  }

  window.addEventListener("load", init);

})();