#!/usr/bin/env node
// tokenwise — UserPromptSubmit hook.
// Watches the user's prompt for "/tokenwise <mode>" or a deactivation phrase and
// updates the mode flag file the activate hook reads. Keeps the persisted mode in
// sync with what the user asked for, mid-session, without a restart.

const fs = require('fs');
const path = require('path');
const { ruleset } = require('./tokenwise-ruleset');
const { flagPath } = require('./tokenwise-flag');

// Per-project flag — see tokenwise-flag.js. Resolved once per run.
const FLAG = flagPath();

function setMode(mode) {
  try {
    fs.mkdirSync(path.dirname(FLAG), { recursive: true });
    fs.writeFileSync(FLAG, mode);
  } catch (e) { /* best-effort */ }
}
// "off" is written explicitly, not represented by deleting the file — a deleted
// flag reads back as "no flag yet", which falls through to the env var / "full"
// default on the next SessionStart and silently re-enables the mode the user just
// turned off (this is what previously made "/tokenwise off" non-persistent).
function clearMode() {
  setMode('off');
}

function emit(mode, message) {
  process.stdout.write(JSON.stringify({
    hookSpecificOutput: { hookEventName: 'UserPromptSubmit', additionalContext: message },
  }), () => process.exit(0));
}

let input = '';
process.stdin.on('data', (chunk) => { input += chunk; });
process.stdin.on('end', () => {
  try {
    const data = JSON.parse(input.replace(/^﻿/, ''));
    const prompt = (data.prompt || '').trim().toLowerCase();

    // Deactivation phrase — deliberately requires the word "tokenwise" itself.
    // A bare "normal mode" was too generic and collided with unrelated usage
    // (e.g. Vim's "normal mode"), silently turning tokenwise off mid-conversation.
    if (/\bstop tokenwise\b/.test(prompt)) {
      clearMode();
      emit('off', 'TOKENWISE MODE OFF');
      return;
    }

    // "/tokenwise [lite|full|off]" (also accepts @ or $ prefix some agents use).
    // Matches at the start of the prompt OR after whitespace, so it still fires
    // when the command is appended mid-sentence or at the end of the message —
    // not just when it's the very first thing typed.
    const m = prompt.match(/(?:^|\s)[/@$]tokenwise(?:\s+(\w+))?/);
    if (m) {
      const arg = (m[1] || '').toLowerCase();
      if (arg === 'off') {
        clearMode();
        emit('off', 'TOKENWISE MODE OFF');
      } else {
        const mode = (arg === 'lite' || arg === 'full') ? arg : 'full';
        setMode(mode);
        // Emit the actual ruleset for the new mode, not just a label — otherwise
        // a mid-session "/tokenwise lite" only relabels the mode and the stricter
        // "full" behavior (or vice versa) keeps applying until the next SessionStart.
        emit(mode, 'TOKENWISE MODE CHANGED — level: ' + mode + '\n\n' + ruleset(mode));
      }
    }
  } catch (e) {
    // Silent fail — never block the prompt.
  }
});
