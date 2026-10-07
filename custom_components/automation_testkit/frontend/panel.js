/* Automation Test Kit panel — vanilla-JS custom element (no build step).
 *
 * HA injects the `hass` object via setCustomPanelProperties (root.hass = ...),
 * which our setter below picks up. Everything is driven through HA's own
 * WebSocket API (`trace/list`, `trace/get`, `config/entity_registry/list`),
 * the `automation.trigger` service, and our custom `automation_testkit/parse_trace`
 * command. No iframe, no external server.
 */
class AutomationTestKitPanel extends HTMLElement {
  set hass(hass) {
    this._hass = hass;
    if (!this._booted) {
      this._booted = true;
      this._build();
      this._loadAutomations();
    }
  }

  get hass() {
    return this._hass;
  }

  /* ---------------------------------------------------------------- shell */

  _build() {
    this.innerHTML = `
      <style>
        :host { display: block; }
        .atk { padding: 16px 16px 24px; color: var(--primary-text-color); }
        .atk-toolbar { display: flex; align-items: center; gap: 12px; margin-bottom: 16px; }
        .atk-title { font-size: 1.3em; font-weight: 500; }
        .atk-spacer { flex: 1; }
        .atk-btn {
          background: var(--primary-color, #03a9f4); color: var(--text-primary-color, #fff);
          border: none; border-radius: 4px; padding: 8px 14px; cursor: pointer;
          font-size: 0.9em;
        }
        .atk-btn:disabled { opacity: 0.5; cursor: default; }
        .atk-cols { display: flex; gap: 16px; align-items: flex-start; }
        .atk-col { flex: 1; min-width: 0; }
        .atk-col-detail { flex: 1.6; }
        .atk-col h3 {
          margin: 0 0 8px; font-size: 0.8em; text-transform: uppercase;
          letter-spacing: 0.05em; color: var(--secondary-text-color);
        }
        .atk-list { display: flex; flex-direction: column; gap: 6px; max-height: 60vh; overflow-y: auto; }
        .atk-item {
          display: flex; flex-direction: column; align-items: flex-start; gap: 2px;
          text-align: left; width: 100%; padding: 8px 10px; cursor: pointer;
          background: var(--card-background-color, transparent);
          border: 1px solid var(--divider-color, rgba(128,128,128,0.3));
          border-radius: 6px; color: var(--primary-text-color);
        }
        .atk-item:hover { border-color: var(--primary-color, #03a9f4); }
        .atk-item.selected { border-color: var(--primary-color, #03a9f4); background: var(--primary-color, #03a9f4); color: var(--text-primary-color, #fff); }
        .atk-item-name { font-weight: 500; }
        .atk-item-id { font-size: 0.8em; color: var(--secondary-text-color); }
        .atk-item.selected .atk-item-id { color: inherit; opacity: 0.85; }
        .atk-item-meta { display: flex; gap: 6px; align-items: center; font-size: 0.78em; }
        .badge { padding: 1px 7px; border-radius: 10px; font-size: 0.85em; }
        .badge-ok { background: var(--success-color, #43a047); color: #fff; }
        .badge-err { background: var(--error-color, #e53935); color: #fff; }
        .badge-run { background: var(--warning-color, #ff9800); color: #fff; }
        .atk-detail { display: flex; flex-direction: column; gap: 12px; }
        .atk-section { border: 1px solid var(--divider-color, rgba(128,128,128,0.3)); border-radius: 6px; padding: 10px 12px; }
        .atk-section h4 { margin: 0 0 6px; font-size: 0.85em; color: var(--secondary-text-color); }
        .atk-kv { font-size: 0.9em; }
        .atk-kv b { font-weight: 500; }
        pre.atk-raw {
          margin: 0; padding: 8px; overflow: auto; font-size: 0.78em;
          background: var(--secondary-background-color, rgba(0,0,0,0.15));
          border-radius: 4px; max-height: 40vh;
        }
        .atk-status { font-size: 0.85em; color: var(--secondary-text-color); }
        .atk-status.err { color: var(--error-color, #e53935); }
        .atk-empty { color: var(--secondary-text-color); font-size: 0.9em; padding: 8px 0; }
        .atk-replay { margin-top: 4px; align-self: flex-start; }
        .atk-trigger-wrap { margin-bottom: 6px; }
        .atk-trigger { display: flex; align-items: center; gap: 8px; }
        .atk-trigger-label { flex: 1; font-size: 0.85em; }
        .atk-edit { display: flex; flex-direction: column; gap: 6px; margin-top: 6px; }
        .atk-edit.hidden { display: none; }
        .atk-edit-ta {
          width: 100%; min-height: 80px; font-family: monospace; font-size: 0.78em;
          background: var(--secondary-background-color, rgba(0,0,0,0.15));
          color: var(--primary-text-color);
          border: 1px solid var(--divider-color, rgba(128,128,128,0.3));
          border-radius: 4px; padding: 6px; box-sizing: border-box;
        }
        .atk-dryrun { border-color: var(--warning-color, #ff9800) !important; }
        .atk-call { margin-bottom: 8px; }
        .atk-call-name { font-weight: 500; }
        .atk-call-target { font-size: 0.85em; color: var(--secondary-text-color); }
      </style>
      <div class="atk">
        <div class="atk-toolbar">
          <span class="atk-title">Automation Test Kit</span>
          <span class="atk-spacer"></span>
          <button id="atk-refresh" class="atk-btn">Refresh</button>
        </div>
        <div class="atk-cols">
          <div class="atk-col">
            <h3>Automations</h3>
            <div id="atk-autos" class="atk-list"></div>
          </div>
          <div class="atk-col">
            <h3>Trace runs</h3>
            <div id="atk-runs" class="atk-list"></div>
          </div>
          <div class="atk-col atk-col-detail">
            <h3>Detail</h3>
            <div id="atk-detail" class="atk-detail"></div>
          </div>
        </div>
      </div>
    `;
    this.querySelector("#atk-refresh").addEventListener("click", () =>
      this._loadAutomations()
    );
  }

  /* ------------------------------------------------------------ low level */

  _callWS(type, data = {}) {
    return this._hass.callWS(Object.assign({ type }, data));
  }

  _errText(err) {
    return String((err && err.message) || err);
  }

  _clear(id) {
    const el = this.querySelector(id);
    if (el) el.textContent = "";
    return el;
  }

  _spinner(text) {
    const el = document.createElement("div");
    el.className = "atk-empty";
    el.textContent = text;
    return el;
  }

  _empty(text) {
    return this._spinner(text);
  }

  _error(text) {
    const el = document.createElement("div");
    el.className = "atk-status err";
    el.textContent = text;
    return el;
  }

  /* ---------------------------------------------------------- automations */

  async _loadAutomations() {
    this._selected = null;
    this._clear("#atk-runs");
    this._clear("#atk-detail");
    const autos = this._clear("#atk-autos");
    autos.appendChild(this._spinner("Loading automations…"));
    try {
      const registry = await this._callWS("config/entity_registry/list");
      const list = registry.filter((e) =>
        (e.entity_id || "").startsWith("automation.")
      );
      this._automations = list;
      this._renderAutomations(list);
    } catch (err) {
      autos.textContent = "";
      autos.appendChild(this._error("Failed to load automations: " + this._errText(err)));
    }
  }

  _renderAutomations(list) {
    const autos = this._clear("#atk-autos");
    if (!list.length) {
      autos.appendChild(this._empty("No automations found."));
      return;
    }
    for (const a of list) {
      const item = document.createElement("button");
      item.className = "atk-item";
      item.dataset.uniqueId = a.unique_id;
      const name = document.createElement("span");
      name.className = "atk-item-name";
      name.textContent = a.name || a.original_name || a.entity_id;
      const id = document.createElement("span");
      id.className = "atk-item-id";
      id.textContent = a.entity_id;
      item.appendChild(name);
      item.appendChild(id);
      item.addEventListener("click", () => this._selectAutomation(a));
      autos.appendChild(item);
    }
  }

  _selectAutomation(a) {
    this._selected = a;
    const autos = this.querySelector("#atk-autos");
    autos.querySelectorAll(".atk-item").forEach((el) => {
      el.classList.toggle("selected", el.dataset.uniqueId === a.unique_id);
    });
    this._loadConfig(a);
    this._loadTraces(a);
  }

  /* ---------------------------------------------------------------- traces */

  async _loadConfig(a) {
    const detail = this._clear("#atk-detail");
    detail.appendChild(this._spinner("Loading config…"));
    try {
      const cfg = await this._callWS("automation_testkit/config", {
        entity_id: a.entity_id,
      });
      this._renderConfig(a, cfg);
    } catch (err) {
      detail.textContent = "";
      detail.appendChild(this._error("Failed to load config: " + this._errText(err)));
    }
  }

  _renderConfig(a, cfg) {
    const detail = this._clear("#atk-detail");

    const head = document.createElement("div");
    head.className = "atk-section";
    const h4 = document.createElement("h4");
    h4.textContent = a.name || a.original_name || a.entity_id;
    head.appendChild(h4);
    const kv = document.createElement("div");
    kv.className = "atk-kv";
    const row = document.createElement("div");
    const b = document.createElement("b");
    b.textContent = "Entity: ";
    row.appendChild(b);
    row.appendChild(document.createTextNode(a.entity_id));
    kv.appendChild(row);
    head.appendChild(kv);
    detail.appendChild(head);

    const trigs = cfg.triggers || [];
    const sec = document.createElement("div");
    sec.className = "atk-section";
    const th = document.createElement("h4");
    th.textContent = "Configured triggers — simulate one (isolated)";
    sec.appendChild(th);
    if (!trigs.length) {
      const e = document.createElement("div");
      e.className = "atk-empty";
      e.textContent = "No triggers defined.";
      sec.appendChild(e);
    }
    trigs.forEach((tv) => {
      sec.appendChild(this._triggerRow(a, tv));
    });
    detail.appendChild(sec);

    const cond = document.createElement("div");
    cond.className = "atk-section";
    const ch = document.createElement("h4");
    ch.textContent = "Conditions (" + (cfg.conditions || []).length + ")";
    cond.appendChild(ch);
    const cpre = document.createElement("pre");
    cpre.className = "atk-raw";
    cpre.textContent = JSON.stringify(cfg.conditions || [], null, 2);
    cond.appendChild(cpre);
    detail.appendChild(cond);

    const act = document.createElement("div");
    act.className = "atk-section";
    const ah = document.createElement("h4");
    ah.textContent = "Actions (" + (cfg.actions || []).length + ")";
    act.appendChild(ah);
    const apre = document.createElement("pre");
    apre.className = "atk-raw";
    apre.textContent = JSON.stringify(cfg.actions || [], null, 2);
    act.appendChild(apre);
    detail.appendChild(act);

    const hint = document.createElement("div");
    hint.className = "atk-status";
    hint.textContent = "Select a trace run to inspect what actually happened.";
    detail.appendChild(hint);
  }

  async _loadTraces(a) {
    const runs = this._clear("#atk-runs");
    runs.appendChild(this._spinner("Loading traces…"));
    try {
      const traces = await this._callWS("trace/list", {
        domain: "automation",
        item_id: a.unique_id,
      });
      this._traces = traces;
      this._renderTraces(traces);
    } catch (err) {
      runs.textContent = "";
      runs.appendChild(this._error("Failed to load traces: " + this._errText(err)));
    }
  }

  _renderTraces(traces) {
    const runs = this._clear("#atk-runs");
    if (!traces.length) {
      runs.appendChild(this._empty("No traces recorded for this automation."));
      return;
    }
    for (const t of traces) {
      const item = document.createElement("button");
      item.className = "atk-item";
      item.dataset.runId = t.run_id;
      const name = document.createElement("span");
      name.className = "atk-item-name";
      name.textContent = t.run_id.slice(0, 12) + "…";
      const meta = document.createElement("span");
      meta.className = "atk-item-meta";

      const stateBadge = document.createElement("span");
      stateBadge.className =
        "badge " + (t.script_execution === "error" ? "badge-err" : t.state === "running" ? "badge-run" : "badge-ok");
      stateBadge.textContent =
        t.script_execution === "error" ? "error" : t.state || "done";
      meta.appendChild(stateBadge);

      if (t.timestamp && t.timestamp.start) {
        const time = document.createElement("span");
        time.textContent = new Date(t.timestamp.start).toLocaleString();
        meta.appendChild(time);
      }
      item.appendChild(name);
      item.appendChild(meta);
      item.addEventListener("click", () => this._selectTrace(t));
      runs.appendChild(item);
    }
  }

  async _selectTrace(t) {
    const a = this._selected;
    if (!a) return;
    const runs = this.querySelector("#atk-runs");
    runs.querySelectorAll(".atk-item").forEach((el) => {
      el.classList.toggle("selected", el.dataset.runId === t.run_id);
    });

    const detail = this._clear("#atk-detail");
    detail.appendChild(this._spinner("Loading trace…"));
    try {
      const raw = await this._callWS("trace/get", {
        domain: "automation",
        item_id: a.unique_id,
        run_id: t.run_id,
      });
      const parsed = await this._callWS("automation_testkit/parse_trace", {
        trace: raw,
      });
      this._renderDetail(a, raw, parsed);
    } catch (err) {
      detail.textContent = "";
      detail.appendChild(this._error("Failed to load trace: " + this._errText(err)));
    }
  }

  /* ---------------------------------------------------------------- detail */

  _renderDetail(a, raw, parsed) {
    const detail = this._clear("#atk-detail");
    const t = parsed.trace || {};

    // Header
    const head = document.createElement("div");
    head.className = "atk-section";
    const alias = document.createElement("h4");
    alias.textContent = t.alias || a.name || a.entity_id;
    head.appendChild(alias);
    const kv = document.createElement("div");
    kv.className = "atk-kv";
    const lines = [
      ["Entity", a.entity_id],
      ["State", t.state || "—"],
      ["Trigger", t.trigger_description || "—"],
    ];
    if (t.error) lines.push(["Error", t.error]);
    for (const [k, v] of lines) {
      const row = document.createElement("div");
      const b = document.createElement("b");
      b.textContent = k + ": ";
      row.appendChild(b);
      row.appendChild(document.createTextNode(String(v)));
      kv.appendChild(row);
    }
    head.appendChild(kv);
    detail.appendChild(head);

    // Simulation spec (the value-add vs HA's native viewer)
    const specs = parsed.trigger_events || [];
    if (specs.length) {
      const sec = document.createElement("div");
      sec.className = "atk-section";
      const h = document.createElement("h4");
      h.textContent = "Trigger simulation";
      sec.appendChild(h);
      const pre = document.createElement("pre");
      pre.className = "atk-raw";
      pre.textContent = JSON.stringify(specs, null, 2);
      sec.appendChild(pre);
      detail.appendChild(sec);
    }

    // Executed trigger variables (with isolated simulate)
    const executed = parsed.executed_triggers || [];
    if (executed.length) {
      const sec = document.createElement("div");
      sec.className = "atk-section";
      const h = document.createElement("h4");
      h.textContent = "Executed triggers — simulate one (isolated)";
      sec.appendChild(h);
      executed.forEach((tv) => {
        sec.appendChild(this._triggerRow(a, tv));
      });
      const pre = document.createElement("pre");
      pre.className = "atk-raw";
      pre.textContent = JSON.stringify(executed, null, 2);
      sec.appendChild(pre);
      detail.appendChild(sec);
    }

    // Conditions + actions
    const cond = document.createElement("div");
    cond.className = "atk-section";
    const ch = document.createElement("h4");
    ch.textContent = "Conditions (" + (t.conditions || []).length + ")";
    cond.appendChild(ch);
    const cpre = document.createElement("pre");
    cpre.className = "atk-raw";
    cpre.textContent = JSON.stringify(t.conditions || [], null, 2);
    cond.appendChild(cpre);
    detail.appendChild(cond);

    const act = document.createElement("div");
    act.className = "atk-section";
    const ah = document.createElement("h4");
    ah.textContent = "Actions (" + (t.actions || []).length + ")";
    act.appendChild(ah);
    const apre = document.createElement("pre");
    apre.className = "atk-raw";
    apre.textContent = JSON.stringify(t.actions || [], null, 2);
    act.appendChild(apre);
    detail.appendChild(act);

    // Replay
    const btn = document.createElement("button");
    btn.className = "atk-btn atk-replay";
    btn.textContent = "Replay (run actions)";
    btn.addEventListener("click", () => this._replay(a));
    detail.appendChild(btn);
  }

  async _replay(a) {
    if (!confirm("Replay this automation? It will run its actions on real devices.")) {
      return;
    }
    const detail = this.querySelector("#atk-detail");
    const status = document.createElement("div");
    status.className = "atk-status";
    status.textContent = "Replaying…";
    detail.appendChild(status);
    try {
      await this._hass.callService(
        "automation",
        "trigger",
        { skip_condition: true },
        { entity_id: a.entity_id }
      );
      status.textContent = "Replayed. Refreshing traces…";
      setTimeout(() => this._loadTraces(a), 1500);
    } catch (err) {
      status.className = "atk-status err";
      status.textContent = "Replay failed: " + this._errText(err);
    }
  }

  async _simulate(a, triggerVar) {
    if (
      !confirm(
        "Simulate this trigger? It runs the full pipeline (trigger → conditions → actions) on this automation only, without waking other automations."
      )
    ) {
      return;
    }
    const detail = this.querySelector("#atk-detail");
    const status = document.createElement("div");
    status.className = "atk-status";
    status.textContent = "Simulating…";
    detail.appendChild(status);
    try {
      await this._callWS("automation_testkit/simulate", {
        entity_id: a.entity_id,
        trigger: triggerVar,
        skip_condition: false,
      });
      status.textContent = "Simulated. Refreshing traces…";
      setTimeout(() => this._loadTraces(a), 1500);
    } catch (err) {
      status.className = "atk-status err";
      status.textContent = "Simulate failed: " + this._errText(err);
    }
  }

  async _dryRun(a, tv) {
    const detail = this.querySelector("#atk-detail");
    const status = document.createElement("div");
    status.className = "atk-status";
    status.textContent = "Dry-running…";
    detail.appendChild(status);
    try {
      const r = await this._callWS("automation_testkit/dry_run", {
        entity_id: a.entity_id,
        trigger: tv,
        skip_condition: false,
      });
      status.remove();
      this._renderDryRunResult(r);
    } catch (err) {
      status.className = "atk-status err";
      status.textContent = "Dry-run failed: " + this._errText(err);
    }
  }

  _renderDryRunResult(r) {
    const detail = this.querySelector("#atk-detail");
    const prev = detail.querySelector(".atk-dryrun");
    if (prev) prev.remove();

    const sec = document.createElement("div");
    sec.className = "atk-section atk-dryrun";
    const h = document.createElement("h4");
    h.textContent = "Dry-run result (no device touched)";
    sec.appendChild(h);

    const calls = r.calls || [];
    const outcome = r.script_execution;
    const execText =
      outcome === "failed_conditions"
        ? "conditions FAILED"
        : outcome === "finished"
          ? "would run"
          : outcome || "unknown";

    const summary = document.createElement("div");
    summary.className = "atk-kv";
    summary.textContent =
      "Outcome: " + execText + " — " + calls.length + " service call(s) would be made.";
    sec.appendChild(summary);

    const conds = r.conditions || [];
    if (conds.length) {
      const condSec = document.createElement("div");
      const ch = document.createElement("h4");
      ch.textContent = "Conditions (" + conds.length + ")";
      condSec.appendChild(ch);
      conds.forEach((c) => {
        const row = document.createElement("div");
        row.className = "atk-call";
        const name = document.createElement("div");
        name.className = "atk-call-name";
        const pass = c.result === true;
        name.textContent = (pass ? "✓ " : "✗ ") + c.path;
        name.style.color = pass
          ? "var(--success-color, #43a047)"
          : "var(--error-color, #e53935)";
        row.appendChild(name);
        if (c.error) {
          const err = document.createElement("div");
          err.className = "atk-call-target";
          err.textContent = c.error;
          row.appendChild(err);
        }
        condSec.appendChild(row);
      });
      sec.appendChild(condSec);
    }

    if (!calls.length) {
      const e = document.createElement("div");
      e.className = "atk-empty";
      e.textContent =
        "No service calls captured (conditions may have failed, or no actions).";
      sec.appendChild(e);
    }
    calls.forEach((c) => {
      const row = document.createElement("div");
      row.className = "atk-call";
      const name = document.createElement("div");
      name.className = "atk-call-name";
      name.textContent = c.domain + "." + c.service;
      const tgt = document.createElement("div");
      tgt.className = "atk-call-target";
      if (c.target && c.target.entity_id) {
        tgt.textContent = "→ " + c.target.entity_id;
      }
      const data = document.createElement("pre");
      data.className = "atk-raw";
      data.textContent = JSON.stringify(c.data || {}, null, 2);
      row.appendChild(name);
      row.appendChild(tgt);
      row.appendChild(data);
      sec.appendChild(row);
    });

    detail.insertBefore(sec, detail.firstChild);
  }

  _triggerRow(a, tv) {
    const wrap = document.createElement("div");
    wrap.className = "atk-trigger-wrap";

    const row = document.createElement("div");
    row.className = "atk-trigger";
    const label = document.createElement("span");
    label.className = "atk-trigger-label";
    label.textContent =
      (tv.platform || "trigger") +
      (tv.description ? " — " + tv.description : "");
    const simBtn = document.createElement("button");
    simBtn.className = "atk-btn";
    simBtn.textContent = "Simulate";
    simBtn.addEventListener("click", () => this._simulate(a, tv));
    const dryBtn = document.createElement("button");
    dryBtn.className = "atk-btn";
    dryBtn.textContent = "Dry run";
    dryBtn.addEventListener("click", () => this._dryRun(a, tv));
    const editBtn = document.createElement("button");
    editBtn.className = "atk-btn";
    editBtn.textContent = "Edit";
    row.appendChild(label);
    row.appendChild(simBtn);
    row.appendChild(dryBtn);
    row.appendChild(editBtn);
    wrap.appendChild(row);

    const panel = document.createElement("div");
    panel.className = "atk-edit hidden";
    const ta = document.createElement("textarea");
    ta.className = "atk-edit-ta";
    ta.rows = 8;
    ta.value = JSON.stringify(tv, null, 2);
    const goBtn = document.createElement("button");
    goBtn.className = "atk-btn";
    goBtn.textContent = "Simulate edited value";
    goBtn.addEventListener("click", () => {
      let edited;
      try {
        edited = JSON.parse(ta.value);
      } catch (e) {
        alert("Invalid JSON: " + e.message);
        return;
      }
      this._simulate(a, edited);
    });
    panel.appendChild(ta);
    panel.appendChild(goBtn);
    wrap.appendChild(panel);

    editBtn.addEventListener("click", () => {
      panel.classList.toggle("hidden");
    });

    return wrap;
  }
}

customElements.define("automation-testkit", AutomationTestKitPanel);
