// plan-renderer: turn a Plan-Contract markdown + a progress.json overlay
// into a structured, interactive HTML view.
//
// Source of truth: plan.md (reviewer-owned). Live state overlay:
// progress.json (implementer-owned). Renderer is deterministic – no
// LLM in the loop. Buttons emit copyable prompt strings to send back
// to the agent.

const STATE_ORDER = ["pending", "in-progress", "done", "blocked"];

const SUB_STATE_LABEL = {
  "idle": "idle",
  "coding": "coding",
  "inner-review": "inner review",
  "applying-fixes": "applying fixes",
  "ready": "ready for outer review",
};

const LIFECYCLE_LABEL = {
  "pending": "pending",
  "current": "current",
  "under-review": "under review",
  "needs-fixes": "needs fixes",
  "completed": "completed",
};

// ─── Parse ────────────────────────────────────────────────────────────────

function parsePlan(md) {
  const plan = {
    title: "",
    intro: "",
    phaseFlowMermaid: "",
    phaseStatus: {},      // phase number -> lifecycle string
    automationContract: "",
    definitionOfDone: [],
    phases: [],           // [{ num, title, statusLine, intro, work[], acceptance[] }]
    filesByPhase: {},     // phase number -> [{ id, text }]
    testPlanByPhase: {},  // phase number -> raw text
    decisions: [],        // [{ title, body }]
    openQuestions: [],
    risks: [],
  };

  // Title and intro
  const lines = md.split(/\r?\n/);
  let i = 0;
  while (i < lines.length && !lines[i].startsWith("# ")) i++;
  if (i < lines.length) {
    plan.title = lines[i].replace(/^# /, "").trim();
    i++;
  }
  const introBuf = [];
  while (i < lines.length && !lines[i].startsWith("## ")) {
    introBuf.push(lines[i]);
    i++;
  }
  plan.intro = introBuf.join("\n").trim();

  // Split remainder by ## sections
  const rest = lines.slice(i).join("\n");
  const sections = splitByHeading(rest, /^## (.+)$/m);

  for (const sec of sections) {
    const heading = sec.heading;
    const body = sec.body;
    if (heading === "Phase Flow") {
      const m = body.match(/```mermaid\s*([\s\S]*?)```/);
      plan.phaseFlowMermaid = m ? m[1].trim() : "";
    } else if (heading === "Phase Status") {
      plan.phaseStatus = parsePhaseStatusTable(body);
    } else if (heading === "Automation Contract") {
      plan.automationContract = body.trim();
    } else if (heading === "Definition of Done") {
      plan.definitionOfDone = parseBullets(body);
    } else if (/^Phase (\d+):/.test(heading)) {
      plan.phases.push(parsePhase(heading, body));
    } else if (heading === "Files to Create or Modify by Phase") {
      const subs = splitByHeading(body, /^### Phase (\d+)\s*$/m);
      for (const s of subs) {
        const num = parseInt(s.heading, 10);
        plan.filesByPhase[num] = parseTaggedBullets(s.body);
      }
    } else if (heading === "Test Plan") {
      const subs = splitByHeading(body, /^### Phase (\d+)\s*$/m);
      for (const s of subs) {
        const num = parseInt(s.heading, 10);
        plan.testPlanByPhase[num] = s.body.trim();
      }
    } else if (heading === "Decisions") {
      plan.decisions = parseDecisions(body);
    } else if (heading === "Open Questions") {
      plan.openQuestions = parseBullets(body);
    } else if (heading === "Residual Risks") {
      plan.risks = parseBullets(body);
    } else if (heading === "Recommended Execution Order") {
      // ignored – represented by Phase Flow + Phase headings
    }
  }

  // If Phase Status table missing, fall back to per-phase Status: line
  for (const phase of plan.phases) {
    if (!plan.phaseStatus[phase.num] && phase.statusLine) {
      plan.phaseStatus[phase.num] = phase.statusLine;
    }
  }

  return plan;
}

function splitByHeading(text, re) {
  const out = [];
  const lines = text.split(/\r?\n/);
  let current = null;
  for (const line of lines) {
    const m = line.match(re);
    if (m) {
      if (current) out.push(current);
      current = { heading: m[1].trim(), body: "" };
    } else if (current) {
      current.body += line + "\n";
    }
  }
  if (current) out.push(current);
  return out;
}

function parsePhase(heading, body) {
  const m = heading.match(/^Phase (\d+):\s*(.+)$/);
  const num = parseInt(m[1], 10);
  const title = m[2].trim();

  const phase = {
    num, title,
    statusLine: "",
    intro: "",
    work: [],
    acceptance: [],
  };

  // Find ### Work and ### Acceptance Criteria
  const subs = splitByHeading(body, /^### (.+)$/m);

  // intro: prose before first ### heading
  const firstSubAt = body.search(/^### /m);
  const preface = firstSubAt === -1 ? body : body.slice(0, firstSubAt);
  const prefaceLines = preface.split(/\r?\n/);
  const introBuf = [];
  for (const ln of prefaceLines) {
    const sm = ln.match(/^Status:\s*(.+)$/);
    if (sm) { phase.statusLine = sm[1].trim().toLowerCase(); continue; }
    introBuf.push(ln);
  }
  phase.intro = introBuf.join("\n").trim();

  for (const s of subs) {
    if (s.heading === "Work") {
      phase.work = parseTaggedBullets(s.body);
    } else if (s.heading === "Acceptance Criteria") {
      phase.acceptance = parseTaggedBullets(s.body);
    }
  }
  return phase;
}

function parsePhaseStatusTable(body) {
  const out = {};
  const rows = body.split(/\r?\n/).filter(l => l.trim().startsWith("|"));
  for (const row of rows) {
    const cells = row.split("|").map(c => c.trim()).filter(c => c.length > 0);
    if (cells.length < 2) continue;
    if (/^Phase$/i.test(cells[0]) || /^-+$/.test(cells[0])) continue;
    const m = cells[0].match(/Phase\s+(\d+)/i);
    if (!m) continue;
    out[parseInt(m[1], 10)] = cells[1].toLowerCase();
  }
  return out;
}

function parseBullets(body) {
  const out = [];
  const lines = body.split(/\r?\n/);
  let buf = null;
  for (const ln of lines) {
    if (/^-\s+/.test(ln)) {
      if (buf) out.push(buf.trim());
      buf = ln.replace(/^-\s+/, "");
    } else if (buf && /^\s+/.test(ln) && ln.trim().length > 0) {
      buf += " " + ln.trim();
    } else if (buf && ln.trim().length === 0) {
      out.push(buf.trim());
      buf = null;
    }
  }
  if (buf) out.push(buf.trim());
  return out;
}

function parseTaggedBullets(body) {
  // `- [w1] text` or `- text` (auto-assign id by index if missing)
  const out = [];
  let autoIdx = 1;
  for (const raw of parseBullets(body)) {
    const m = raw.match(/^\[([wfa]\d+|[a-z]+\d+)\]\s+(.+)$/i);
    if (m) {
      out.push({ id: m[1].toLowerCase(), text: m[2] });
    } else {
      // auto-id; prefix derived from caller context isn't known here,
      // so we use plain numbering and the caller can prefix as needed.
      out.push({ id: String(autoIdx), text: raw });
    }
    autoIdx++;
  }
  return out;
}

function parseDecisions(body) {
  const out = [];
  const bullets = parseBullets(body);
  for (const b of bullets) {
    // Pattern: **Title.** body…  or  **Title** body…
    const m = b.match(/^\*\*([^*]+?)\*\*\.?\s*(.*)$/);
    if (m) {
      out.push({ title: m[1].trim().replace(/\.$/, ""), body: m[2].trim() });
    } else {
      out.push({ title: "", body: b });
    }
  }
  return out;
}

// ─── Merge plan + progress ───────────────────────────────────────────────

function mergeProgress(plan, progress) {
  if (!progress) return plan;
  for (const phase of plan.phases) {
    const p = progress.phases?.[phase.num];
    if (!p) continue;
    phase.progress = p;
  }
  plan._progress = progress;
  return plan;
}

// ─── Render ──────────────────────────────────────────────────────────────

// ─── Inline markdown ─────────────────────────────────────────────────────
// Minimal inline transforms applied to plan prose: **bold**, _italic_,
// `code`, [label](url). Block-level structure is already handled by the
// section parser, so this is purely span-level.

function escapeHtml(s) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

function renderInline(text) {
  if (text == null) return "";
  let s = escapeHtml(text);

  // Code spans first – their content must not be re-processed by later
  // transforms. Stash with a private placeholder.
  const codes = [];
  s = s.replace(/`([^`]+)`/g, (_, c) => ` C${codes.push(c) - 1} `);

  // Links: [label](url) – restrict url to a safe-ish charset.
  s = s.replace(/\[([^\]]+)\]\(([^)\s]+)\)/g, (_, label, url) => {
    const safe = url.replace(/"/g, "&quot;");
    return `<a href="${safe}" target="_blank" rel="noopener">${label}</a>`;
  });

  // Bold: **text**
  s = s.replace(/\*\*([^*\n]+)\*\*/g, "<strong>$1</strong>");

  // Italic: _text_ (avoids collision with ** since we already removed bold)
  s = s.replace(/(^|[\s(])_([^_\n]+)_(?=$|[\s.,;:!?)])/g, "$1<em>$2</em>");

  // Restore code spans last.
  s = s.replace(/ C(\d+) /g, (_, i) => `<code>${codes[+i]}</code>`);

  return s;
}

// Render a multi-line prose block: extracts ```mermaid``` and other fenced
// code blocks into proper <pre> elements, and renders the remaining text as
// paragraphs (separated by blank lines) with renderInline applied. Used for
// phase intros where authors may embed sequence/class/ER diagrams.
function renderProseBlocks(text, container) {
  const fenceRe = /```(\w+)?\n([\s\S]*?)```/g;
  let lastIndex = 0;
  let m;
  while ((m = fenceRe.exec(text)) !== null) {
    const before = text.slice(lastIndex, m.index);
    emitProseParagraphs(before, container);
    const lang = (m[1] || "").toLowerCase();
    const body = m[2].replace(/\s+$/, "");
    if (lang === "mermaid") {
      const pre = document.createElement("pre");
      pre.className = "mermaid";
      pre.textContent = body;
      container.appendChild(pre);
    } else {
      const pre = document.createElement("pre");
      pre.className = "code-block";
      const code = document.createElement("code");
      if (lang) code.className = `lang-${lang}`;
      code.textContent = body;
      pre.appendChild(code);
      container.appendChild(pre);
    }
    lastIndex = m.index + m[0].length;
  }
  emitProseParagraphs(text.slice(lastIndex), container);
}

function emitProseParagraphs(text, container) {
  const trimmed = text.replace(/^\s+|\s+$/g, "");
  if (!trimmed) return;
  for (const p of trimmed.split(/\n\s*\n/)) {
    const t = p.trim();
    if (!t) continue;
    container.appendChild(el("p", { className: "phase-intro", html: renderInline(t) }));
  }
}

function el(tag, attrs = {}, children = []) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (v == null || v === false) continue;
    if (k === "className") node.className = v;
    else if (k === "onClick") node.addEventListener("click", v);
    else if (k === "html") node.innerHTML = v;
    else node.setAttribute(k, v);
  }
  for (const c of [].concat(children)) {
    if (c == null || c === false) continue;
    if (typeof c === "string") node.appendChild(document.createTextNode(c));
    else node.appendChild(c);
  }
  return node;
}

function renderPlan(plan, root) {
  root.innerHTML = "";
  setAppTitle(plan.title);
  root.appendChild(renderHeader(plan));
  if (plan.phaseFlowMermaid) root.appendChild(renderPhaseFlow(plan));
  root.appendChild(renderPhasesPanel(plan));
  root.appendChild(renderDecisions(plan));
  root.appendChild(renderFooterSections(plan));
}

function setAppTitle(title) {
  if (!title) return;
  const bar = document.querySelector(".app-bar .app-title");
  if (bar) bar.innerHTML = renderInline(title);
  document.title = title;
}

function renderHeader(plan) {
  const chips = plan.phases.map(ph => {
    const state = (plan.phaseStatus[ph.num] || "pending").toLowerCase();
    return el("span", { className: `chip chip-${state}` }, [
      el("span", { className: "chip-dot" }),
      `P${ph.num} ${LIFECYCLE_LABEL[state] || state}`,
    ]);
  });
  return el("header", { className: "plan-header" }, [
    el("p", { className: "plan-intro", html: renderInline(plan.intro) }),
    el("div", { className: "phase-chips" }, chips),
  ]);
}

function renderPhaseFlow(plan) {
  const card = el("section", { className: "card card-flow" });
  card.appendChild(el("h2", {}, "Phase Flow"));
  const pre = el("pre", { className: "mermaid" }, plan.phaseFlowMermaid);
  card.appendChild(pre);
  return card;
}

function renderPhasesPanel(plan) {
  const wrap = el("section", { className: "phases" });
  for (const phase of plan.phases) {
    const state = (plan.phaseStatus[phase.num] || "pending").toLowerCase();
    wrap.appendChild(renderPhase(phase, state, plan));
  }
  return wrap;
}

function renderPhase(phase, state, plan) {
  const expanded = state === "current";
  const card = el("article", { className: `card phase phase-${state}`, "data-phase": phase.num });

  // Header (always visible)
  const head = el("div", {
    className: "phase-head",
    role: "button",
    "aria-expanded": expanded ? "true" : "false",
    onClick: (e) => {
      const c = e.currentTarget.parentElement;
      c.classList.toggle("collapsed");
      e.currentTarget.setAttribute(
        "aria-expanded",
        c.classList.contains("collapsed") ? "false" : "true"
      );
    },
  }, [
    el("span", { className: "phase-num" }, `Phase ${phase.num}`),
    el("span", { className: "phase-title", html: renderInline(phase.title) }),
    el("span", { className: `chip chip-${state}` }, [
      el("span", { className: "chip-dot" }),
      LIFECYCLE_LABEL[state] || state,
    ]),
  ]);
  card.appendChild(head);
  if (!expanded) card.classList.add("collapsed");

  // Body
  const body = el("div", { className: "phase-body" });

  if (phase.progress) body.appendChild(renderLivePanel(phase));
  if (phase.intro) {
    const intro = el("div", { className: "phase-intro-block" });
    renderProseBlocks(phase.intro, intro);
    body.appendChild(intro);
  }

  // Two-col: Work | Files
  const grid = el("div", { className: "phase-grid" });
  grid.appendChild(renderItemList("Work", phase.work, phase.progress, phase.num, "work"));
  const files = plan.filesByPhase[phase.num] || [];
  grid.appendChild(renderItemList("Files", files, phase.progress, phase.num, "files"));
  body.appendChild(grid);

  // Acceptance full-width
  body.appendChild(renderItemList("Acceptance Criteria", phase.acceptance, phase.progress, phase.num, "acceptance"));

  // Actions
  body.appendChild(renderPhaseActions(phase, state));

  card.appendChild(body);
  return card;
}

function renderLivePanel(phase) {
  const p = phase.progress;
  const live = el("div", { className: "live-panel" });
  const head = el("div", { className: "live-head" }, [
    el("span", { className: "live-label" }, "Live"),
    el("span", { className: "live-sub" }, [
      el("span", { className: "live-meta" }, [
        el("span", { className: "live-meta-k" }, "sub-state"),
        el("span", { className: `live-substate sub-${p.sub_state}` }, SUB_STATE_LABEL[p.sub_state] || p.sub_state),
      ]),
      el("span", { className: "live-meta" }, [
        el("span", { className: "live-meta-k" }, "cycle"),
        el("span", {}, `${p.cycle} / ${p.cycle_cap}`),
      ]),
      el("span", { className: "live-meta" }, [
        el("span", { className: "live-meta-k" }, "started"),
        el("span", {}, fmtTime(p.started_at)),
      ]),
      el("span", { className: "live-meta" }, [
        el("span", { className: "live-meta-k" }, "updated"),
        el("span", {}, fmtRelative(p.updated_at || phase.progress?.activity?.[0]?.at)),
      ]),
    ]),
  ]);
  live.appendChild(head);

  // Activity log
  if (p.activity?.length) {
    const log = el("ol", { className: "activity-log" });
    for (const ev of p.activity) {
      log.appendChild(el("li", { className: `activity activity-${ev.role}` }, [
        el("span", { className: "activity-time" }, fmtClock(ev.at)),
        el("span", { className: "activity-role" }, ev.role),
        el("span", { className: "activity-msg", html: renderInline(ev.msg) }),
      ]));
    }
    live.appendChild(log);
  }

  // Proposed decisions from implementer
  if (p.proposed_decisions?.length) {
    const prop = el("div", { className: "proposed-decisions" });
    prop.appendChild(el("div", { className: "proposed-label" }, `${p.proposed_decisions.length} proposed decision(s) from implementer`));
    for (const d of p.proposed_decisions) {
      prop.appendChild(el("div", { className: "proposed-card" }, [
        el("p", { className: "proposed-text", html: renderInline(d.text) }),
        el("p", { className: "proposed-just", html: renderInline(d.justification) }),
        el("div", { className: "actions" }, [
          el("button", {
            className: "btn",
            onClick: () => emitPrompt(
              `Apply this proposed decision to ## Decisions in the plan: "${d.text}". Justification recorded by the implementer: ${d.justification}.`
            ),
          }, "send to plan"),
          el("button", {
            className: "btn btn-ghost",
            onClick: () => emitPrompt(
              `Reject the implementer's proposed decision: "${d.text}". Explain in the plan or progress log why it was rejected.`
            ),
          }, "reject"),
        ]),
      ]));
    }
    live.appendChild(prop);
  }

  return live;
}

function renderItemList(label, items, progress, phaseNum, kind) {
  const wrap = el("div", { className: `items items-${kind}` });
  wrap.appendChild(el("h4", { className: "items-label" }, label));
  if (!items.length) {
    wrap.appendChild(el("p", { className: "items-empty" }, "–"));
    return wrap;
  }
  const ul = el("ul", { className: "items-list" });
  for (const item of items) {
    // Resolve item state from progress overlay
    const itemId = normalizeItemId(item.id, kind);
    const state = progress?.items?.[itemId]?.state || "pending";
    const note = progress?.items?.[itemId]?.note;
    ul.appendChild(el("li", { className: `item item-${state}` }, [
      el("span", { className: "item-state-dot" }),
      el("span", { className: "item-id" }, itemId),
      el("span", { className: "item-text", html: renderInline(item.text) }),
      note && el("span", { className: "item-note", html: renderInline(note) }),
      el("span", { className: `chip chip-tiny chip-${state}` }, state),
    ]));
  }
  wrap.appendChild(ul);
  return wrap;
}

function normalizeItemId(rawId, kind) {
  // Files-to-Create-or-Modify bullets use [f1] naturally; Work uses [w1];
  // Acceptance uses [a1]. If the parser auto-assigned a plain number, add a prefix.
  if (/^[wfa]\d+$/i.test(rawId)) return rawId.toLowerCase();
  const prefix = kind === "work" ? "w" : kind === "files" ? "f" : kind === "acceptance" ? "a" : "x";
  return prefix + rawId;
}

function renderPhaseActions(phase, state) {
  const actions = el("div", { className: "phase-actions" });
  if (state === "current") {
    actions.appendChild(actionBtn("regenerate work", () =>
      emitPrompt(`Regenerate the ### Work bullets for Phase ${phase.num} of the implementation plan. Preserve existing acceptance criteria.`)));
    actions.appendChild(actionBtn("split this phase", () =>
      emitPrompt(`Split Phase ${phase.num} ("${phase.title}") into two smaller phases. Renumber subsequent phases.`)));
    actions.appendChild(actionBtn("ask implementer to pause", () =>
      emitPrompt(`Pause Phase ${phase.num} implementation. Save current progress.json state and wait for review.`)));
    actions.appendChild(actionBtn("promote to under-review", () =>
      emitPrompt(`Phase ${phase.num} implementation reports ready. Run review-implementation on Phase ${phase.num}.`)));
  } else if (state === "needs-fixes") {
    actions.appendChild(actionBtn("implement fixes", () =>
      emitPrompt(`Run implement-fixes for Phase ${phase.num}, applying the outstanding review findings.`)));
  } else if (state === "completed") {
    actions.appendChild(actionBtn("reopen", () =>
      emitPrompt(`Reopen Phase ${phase.num} ("${phase.title}"). Roll its lifecycle back to current and explain why in ## Decisions.`)));
  } else if (state === "pending") {
    actions.appendChild(actionBtn("start phase", () =>
      emitPrompt(`Start Phase ${phase.num} ("${phase.title}"). Run implement-phase on Phase ${phase.num}.`)));
  }
  return actions;
}

function actionBtn(label, onClick) {
  return el("button", { className: "btn", onClick }, label);
}

function renderDecisions(plan) {
  const card = el("section", { className: "card card-decisions" });
  const proposedCount = (plan._progress?.phases ? Object.values(plan._progress.phases) : [])
    .flatMap(p => p.proposed_decisions || []).length;
  card.appendChild(el("h2", {}, [
    `Decisions (${plan.decisions.length})`,
    proposedCount > 0 && el("span", { className: "badge badge-attention" }, `${proposedCount} proposed`),
  ]));
  const grid = el("div", { className: "decisions-grid" });
  for (const d of plan.decisions) {
    grid.appendChild(el("div", { className: "decision-card" }, [
      d.title && el("div", { className: "decision-title", html: renderInline(d.title) }),
      el("p", { className: "decision-body", html: renderInline(d.body) }),
      el("div", { className: "actions" }, [
        el("button", {
          className: "btn btn-ghost",
          onClick: () => emitPrompt(`Revisit this decision in ## Decisions: "${d.title || d.body}". Surface tradeoffs and propose alternatives.`),
        }, "revisit"),
        el("button", {
          className: "btn btn-ghost",
          onClick: () => emitPrompt(`Remove this decision from ## Decisions and explain why it no longer applies: "${d.title || d.body}".`),
        }, "remove"),
      ]),
    ]));
  }
  card.appendChild(grid);
  card.appendChild(el("div", { className: "decisions-tools" }, [
    el("button", {
      className: "btn",
      onClick: () => emitPrompt(`Add a new decision to ## Decisions. Topic: [fill in]. Recommend an option and list tradeoffs.`),
    }, "+ add decision"),
  ]));
  return card;
}

function renderFooterSections(plan) {
  const wrap = el("section", { className: "footer-sections" });

  // Open Questions
  const oq = el("div", { className: "card card-half" });
  oq.appendChild(el("h2", {}, `Open Questions (${plan.openQuestions.length})`));
  if (plan.openQuestions.length === 0) {
    oq.appendChild(el("p", { className: "muted", html: renderInline("_none_") }));
  } else {
    const ul = el("ul", {});
    for (const q of plan.openQuestions) ul.appendChild(el("li", { html: renderInline(q) }));
    oq.appendChild(ul);
  }
  oq.appendChild(el("button", {
    className: "btn btn-ghost",
    onClick: () => emitPrompt(`Append a new open question to ## Open Questions: [fill in]. This section is append-only.`),
  }, "+ add open question"));
  wrap.appendChild(oq);

  // Risks
  const risks = el("div", { className: "card card-half" });
  risks.appendChild(el("h2", {}, `Residual Risks (${plan.risks.length})`));
  if (plan.risks.length === 0) {
    risks.appendChild(el("p", { className: "muted", html: renderInline("_none_") }));
  } else {
    const ul = el("ul", {});
    for (const r of plan.risks) ul.appendChild(el("li", { html: renderInline(r) }));
    risks.appendChild(ul);
  }
  wrap.appendChild(risks);

  return wrap;
}

// ─── Prompt emit (toast + copy to clipboard) ─────────────────────────────

function emitPrompt(text) {
  navigator.clipboard?.writeText(text).catch(() => {});
  showToast(text);
}

function showToast(text) {
  const existing = document.getElementById("plan-toast");
  if (existing) existing.remove();
  const toast = el("div", { id: "plan-toast", className: "toast", role: "status" }, [
    el("div", { className: "toast-label" }, "prompt copied to clipboard – paste it into the agent"),
    el("pre", { className: "toast-prompt" }, text),
    el("button", { className: "btn btn-ghost toast-close", onClick: () => toast.remove() }, "dismiss"),
  ]);
  document.body.appendChild(toast);
  setTimeout(() => { if (document.body.contains(toast)) toast.classList.add("toast-fade"); }, 6000);
  setTimeout(() => toast.remove(), 7200);
}

// ─── Time helpers ────────────────────────────────────────────────────────

function fmtTime(iso) {
  if (!iso) return "–";
  const d = new Date(iso);
  return d.toLocaleString();
}
function fmtClock(iso) {
  if (!iso) return "–";
  const d = new Date(iso);
  return d.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" });
}
function fmtRelative(iso) {
  if (!iso) return "–";
  const ms = Date.now() - new Date(iso).getTime();
  const min = Math.round(ms / 60000);
  if (Math.abs(min) < 1) return "just now";
  if (Math.abs(min) < 60) return `${min} min ago`;
  const hr = Math.round(min / 60);
  if (Math.abs(hr) < 48) return `${hr} h ago`;
  return fmtTime(iso);
}

// ─── Theme ───────────────────────────────────────────────────────────────

function applyTheme(mode) {
  document.documentElement.setAttribute("data-omnis-palette", "black-silver");
  if (mode === "dark") {
    document.documentElement.setAttribute("data-omnis-mode", "dark");
  } else {
    document.documentElement.removeAttribute("data-omnis-mode");
  }
  // Theme mermaid too
  if (window.mermaid) {
    window.mermaid.initialize({
      startOnLoad: false,
      theme: mode === "dark" ? "dark" : "default",
      securityLevel: "loose",
    });
  }
}

function initThemeToggle() {
  const saved = localStorage.getItem("plan-renderer-theme") ||
    (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
  applyTheme(saved);
  const btn = document.getElementById("theme-toggle");
  btn.textContent = saved === "dark" ? "light mode" : "dark mode";
  btn.addEventListener("click", () => {
    const cur = document.documentElement.getAttribute("data-omnis-mode") === "dark" ? "dark" : "light";
    const next = cur === "dark" ? "light" : "dark";
    localStorage.setItem("plan-renderer-theme", next);
    applyTheme(next);
    btn.textContent = next === "dark" ? "light mode" : "dark mode";
    // Re-render mermaid with the new theme
    rerenderMermaid();
  });
}

async function rerenderMermaid() {
  if (!window.mermaid) return;
  const blocks = document.querySelectorAll("pre.mermaid, .mermaid-rendered");
  for (const b of blocks) {
    if (b.classList.contains("mermaid-rendered")) {
      // restore source from data attribute
      const src = b.getAttribute("data-mermaid-src");
      if (src) {
        const pre = document.createElement("pre");
        pre.className = "mermaid";
        pre.textContent = src;
        b.replaceWith(pre);
      }
    }
  }
  await renderMermaid();
}

async function renderMermaid() {
  if (!window.mermaid) return;
  const blocks = document.querySelectorAll("pre.mermaid");
  let i = 0;
  for (const b of blocks) {
    const src = b.textContent;
    try {
      const { svg } = await window.mermaid.render(`mmd-${Date.now()}-${i++}`, src);
      const div = document.createElement("div");
      div.className = "mermaid-rendered";
      div.setAttribute("data-mermaid-src", src);
      div.innerHTML = svg;
      b.replaceWith(div);
    } catch (err) {
      console.error("mermaid render failed:", err);
    }
  }
}

// ─── Auto-refresh ────────────────────────────────────────────────────────

const REFRESH_CYCLE = [0, 5, 15, 60];   // seconds; 0 = off

function refreshLabel(sec) {
  return sec === 0 ? "auto-refresh: off" : `auto-refresh: ${sec}s`;
}

function initRefreshToggle() {
  const btn = document.getElementById("refresh-toggle");
  if (!btn) return;
  let cur = parseInt(localStorage.getItem("plan-renderer-refresh") || "0", 10);
  if (!REFRESH_CYCLE.includes(cur)) cur = 0;
  btn.textContent = refreshLabel(cur);
  scheduleReload(cur);
  btn.addEventListener("click", () => {
    const idx = (REFRESH_CYCLE.indexOf(cur) + 1) % REFRESH_CYCLE.length;
    cur = REFRESH_CYCLE[idx];
    localStorage.setItem("plan-renderer-refresh", String(cur));
    btn.textContent = refreshLabel(cur);
    scheduleReload(cur);
  });
}

let _reloadTimer = null;
function scheduleReload(sec) {
  if (_reloadTimer) { clearTimeout(_reloadTimer); _reloadTimer = null; }
  if (sec > 0) {
    _reloadTimer = setTimeout(() => {
      sessionStorage.setItem("plan-renderer-scroll", String(window.scrollY));
      location.reload();
    }, sec * 1000);
  }
}

function restoreScroll() {
  const y = parseInt(sessionStorage.getItem("plan-renderer-scroll") || "0", 10);
  if (y > 0) {
    sessionStorage.removeItem("plan-renderer-scroll");
    requestAnimationFrame(() => window.scrollTo(0, y));
  }
}

// ─── Boot ────────────────────────────────────────────────────────────────

async function fetchText(url) {
  const r = await fetch(url);
  if (!r.ok) throw new Error(`fetch ${url}: ${r.status}`);
  return r.text();
}

async function fetchJsonOrNull(url) {
  try {
    const r = await fetch(url);
    if (!r.ok) return null;
    return await r.json();
  } catch {
    return null;
  }
}

// Read inline data baked into the HTML by bake.mjs, if present.
function readInlinePlan() {
  const el = document.getElementById("plan-md");
  return el ? el.textContent : null;
}
function readInlineProgress() {
  const el = document.getElementById("plan-progress");
  if (!el) return null;
  const txt = el.textContent.trim();
  if (!txt) return null;
  try { return JSON.parse(txt); } catch (e) {
    console.error("inline progress JSON parse failed:", e);
    return null;
  }
}

async function loadSources() {
  // Prefer baked-in data.
  const inlinePlan = readInlinePlan();
  if (inlinePlan != null) {
    return { planMd: inlinePlan, progress: readInlineProgress(), mode: "baked" };
  }
  // Fall back to fetching from the served folder (dev mode).
  const params = new URLSearchParams(location.search);
  const planUrl = params.get("plan") || "sample/implementation-plan.md";
  const progressUrl = params.get("progress") || planUrl.replace(/\.md$/, ".progress.json");
  const planMd = await fetchText(planUrl);
  const progress = await fetchJsonOrNull(progressUrl);
  return { planMd, progress, mode: "fetched" };
}

async function boot() {
  initThemeToggle();
  initRefreshToggle();

  const root = document.getElementById("plan-root");
  root.innerHTML = '<p class="muted">loading…</p>';

  let sources;
  try {
    sources = await loadSources();
  } catch (err) {
    root.innerHTML = `<p class="muted">failed to load plan: ${err.message}. If you opened the un-baked dev page from <code>file://</code>, either run <code>node bake.mjs</code> to produce a self-contained file or serve the folder via HTTP.</p>`;
    return;
  }

  const plan = mergeProgress(parsePlan(sources.planMd), sources.progress);
  renderPlan(plan, root);
  await renderMermaid();
  restoreScroll();
}

window.addEventListener("DOMContentLoaded", boot);
