#!/usr/bin/env node
// tokenwise — SessionStart activation hook.
//
// Runs on every session start / resume / clear / compact:
//   1. Resolves the active mode (persisted flag > env default > "full").
//   2. Writes a flag file so a statusline (and the mode tracker) can read it.
//   3. Emits the tokenwise ruleset as hidden SessionStart context, so the
//      token-discipline behavior is active EVERY response, not only when the
//      skill happens to trigger.
//   4. If the project has a RULES.md at the cwd root, injects it too — so project
//      conventions load automatically and never need re-explaining (zero tokens
//      spent re-stating what the project already wrote down).

const fs = require('fs');
const path = require('path');
const { ruleset } = require('./tokenwise-ruleset');
const { flagPath } = require('./tokenwise-flag');

// Per-project flag — see tokenwise-flag.js. Resolved once per run.
const FLAG = flagPath();

// Priority: persisted flag (the user's most recent explicit "/tokenwise ..." choice,
// including "off") beats the env var. The flag file always holds a valid mode once
// written — "off" is written explicitly (see tokenwise-mode-tracker.js), never
// represented by the file's absence, so a user's "off" survives compact/resume/restart.
// TOKENWISE_MODE is only the *initial* default for a machine that has never set a flag.
function readMode() {
  try {
    const m = fs.readFileSync(FLAG, 'utf8').replace(/^﻿/, '').trim().toLowerCase();
    if (m === 'lite' || m === 'full' || m === 'off') return m;
  } catch (e) { /* no flag yet — fall through to env / default */ }
  const env = (process.env.TOKENWISE_MODE || '').trim().toLowerCase();
  if (env === 'lite' || env === 'full' || env === 'off') return env;
  return 'full';
}

// Cap RULES.md size — this plugin's whole premise is spending fewer tokens; an
// unbounded project file injected every single turn would work against that.
const RULES_MAX_CHARS = 6000;

function readProjectRules() {
  try {
    const p = path.join(process.cwd(), 'RULES.md');
    let raw = fs.readFileSync(p, 'utf8').replace(/^﻿/, '');
    if (!raw.trim()) return '';
    if (raw.length > RULES_MAX_CHARS) {
      raw = raw.slice(0, RULES_MAX_CHARS) +
        `\n\n[...truncated — RULES.md is over ${RULES_MAX_CHARS} chars; trim it so it loads fully every turn.]`;
    }
    return raw;
  } catch (e) { /* no RULES.md — fine */ }
  return '';
}

function emit(ctx) {
  // Wait for the write to actually flush before exiting — on Windows, stdout.write
  // to a piped/redirected stream is not guaranteed synchronous, so exiting right
  // after the call can truncate the output the hook is supposed to emit.
  process.stdout.write(JSON.stringify({
    hookSpecificOutput: { hookEventName: 'SessionStart', additionalContext: ctx },
  }), () => process.exit(0));
}

const mode = readMode();

// "off" is a real, persisted state (see readMode) — don't touch or delete the flag
// here. Deleting it would make readMode() fall through to the env/full default on
// the very next SessionStart, silently re-enabling a mode the user turned off.
if (mode === 'off') {
  process.exit(0);
}

try {
  fs.mkdirSync(path.dirname(FLAG), { recursive: true });
  fs.writeFileSync(FLAG, mode);
} catch (e) { /* flag is best-effort */ }

let ctx = ruleset(mode);
const rules = readProjectRules();
if (rules) {
  ctx += '\n\n---\n\n# Project RULES.md (auto-loaded by tokenwise — treat as project conventions)\n\n' + rules;
}
emit(ctx); // emit() exits once the write flushes
