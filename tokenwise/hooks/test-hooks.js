#!/usr/bin/env node
// tokenwise — smoke test for the two hooks. No framework dependency (assert +
// child_process), so it runs anywhere node runs: `node hooks/test-hooks.js`.
//
// Covers the regressions this suite is here to prevent:
//   - "/tokenwise off" must survive a subsequent SessionStart (previously it
//     didn't — deleting the flag made the next run fall back to full).
//   - The persisted flag must beat TOKENWISE_MODE (previously env always won,
//     so a persisted "off"/"lite" could never actually take effect).
//   - A mid-session "/tokenwise lite" must emit the real lite ruleset, not just
//     a label (previously "full"-only text like "Tool discipline" leaked into
//     what should've been a stricter/lighter mode).

const assert = require('assert');
const path = require('path');
const { execFileSync } = require('child_process');
const fs = require('fs');
const os = require('os');

const HOOKS_DIR = __dirname;
const NODE = process.execPath;

function withTempConfigDir(fn) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'tokenwise-test-'));
  const env = { ...process.env, CLAUDE_CONFIG_DIR: dir };
  delete env.TOKENWISE_MODE;
  try {
    fn(env, dir);
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
}

function runActivate(env) {
  const out = execFileSync(NODE, [path.join(HOOKS_DIR, 'tokenwise-activate.js')], { env });
  if (!out.toString().trim()) return null; // "off": no output at all
  return JSON.parse(out.toString());
}

function runTracker(env, prompt) {
  const out = execFileSync(NODE, [path.join(HOOKS_DIR, 'tokenwise-mode-tracker.js')], {
    input: JSON.stringify({ prompt }),
    env,
  });
  return JSON.parse(out.toString());
}

let passed = 0;
function test(name, fn) {
  try {
    fn();
    passed++;
    console.log(`ok   - ${name}`);
  } catch (e) {
    console.log(`FAIL - ${name}`);
    console.log('      ' + e.message);
    process.exitCode = 1;
  }
}

test('fresh run with no flag and no env defaults to full', () => {
  withTempConfigDir((env) => {
    const result = runActivate(env);
    assert.match(result.hookSpecificOutput.additionalContext, /level: full/);
  });
});

test('"/tokenwise off" persists across a later SessionStart', () => {
  withTempConfigDir((env) => {
    runTracker(env, '/tokenwise off');
    const result = runActivate(env);
    assert.strictEqual(result, null, 'expected no SessionStart output once off');
  });
});

test('persisted flag beats TOKENWISE_MODE env var', () => {
  withTempConfigDir((env) => {
    runTracker(env, '/tokenwise lite');
    const result = runActivate({ ...env, TOKENWISE_MODE: 'full' });
    assert.match(result.hookSpecificOutput.additionalContext, /level: lite/);
  });
});

test('TOKENWISE_MODE env is used only when no flag has ever been set', () => {
  withTempConfigDir((env) => {
    const result = runActivate({ ...env, TOKENWISE_MODE: 'lite' });
    assert.match(result.hookSpecificOutput.additionalContext, /level: lite/);
  });
});

test('mid-session "/tokenwise lite" emits the actual lite ruleset, not just a label', () => {
  withTempConfigDir((env) => {
    const result = runTracker(env, '/tokenwise lite');
    const ctx = result.hookSpecificOutput.additionalContext;
    assert.match(ctx, /Four levers/);
    assert.doesNotMatch(ctx, /Tool discipline/, 'lite must not carry the full-only paragraph');
  });
});

test('"/tokenwise lite" mid-session then a later SessionStart both agree on lite', () => {
  withTempConfigDir((env) => {
    runTracker(env, '/tokenwise lite');
    const result = runActivate(env);
    assert.match(result.hookSpecificOutput.additionalContext, /level: lite/);
  });
});

test('command works when appended mid-sentence, not just at the start', () => {
  withTempConfigDir((env) => {
    const result = runTracker(env, 'lütfen /tokenwise lite moduna geç');
    assert.match(result.hookSpecificOutput.additionalContext, /level: lite/);
  });
});

test('"stop tokenwise" turns it off; a bare "normal mode" does NOT (avoids Vim collision)', () => {
  withTempConfigDir((env) => {
    const r1 = runTracker(env, 'stop tokenwise');
    assert.match(r1.hookSpecificOutput.additionalContext, /OFF/);

    // Reset to full, then confirm an unrelated "normal mode" sentence is a no-op.
    runTracker(env, '/tokenwise full');
    execFileSync(NODE, [path.join(HOOKS_DIR, 'tokenwise-mode-tracker.js')], {
      input: JSON.stringify({ prompt: 'press escape to go back to normal mode in vim' }),
      env,
    }); // must not throw and must not touch the flag
    const result = runActivate(env);
    assert.match(result.hookSpecificOutput.additionalContext, /level: full/);
  });
});

console.log(`\n${passed} passed`);
if (process.exitCode) {
  console.log('SOME TESTS FAILED');
}
