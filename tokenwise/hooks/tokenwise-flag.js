// tokenwise — shared flag-file path resolution, used by both hooks.
//
// The flag is keyed per project (a short hash of the cwd the hook runs in, which
// is the project root for SessionStart/UserPromptSubmit — the same assumption
// tokenwise-activate.js already makes when it looks for ./RULES.md). Without this,
// two sessions in different projects — or even two sessions in the same project —
// shared a single global flag, so "/tokenwise off" in one project silently flipped
// the mode for every other open session on the machine.

const fs = require('fs');
const os = require('os');
const path = require('path');
const crypto = require('crypto');

function claudeDir() {
  return process.env.CLAUDE_CONFIG_DIR || path.join(os.homedir(), '.claude');
}

function flagPath() {
  const key = crypto.createHash('sha1').update(process.cwd()).digest('hex').slice(0, 10);
  return path.join(claudeDir(), `.tokenwise-active-${key}`);
}

module.exports = { claudeDir, flagPath };
