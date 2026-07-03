// tokenwise — shared ruleset text, used by both the SessionStart hook
// (tokenwise-activate.js) and the UserPromptSubmit hook (tokenwise-mode-tracker.js).
// Extracted so a mid-session mode switch (e.g. "/tokenwise lite") can inject the
// ACTUAL updated rules immediately, not just a label that takes effect next session.

function ruleset(mode) {
  // Core behavior, present in every mode.
  let s = `TOKENWISE MODE ACTIVE — level: ${mode}
ACTIVE EVERY RESPONSE. Goal: maximum quality per token. Off only on "/tokenwise off" or "stop tokenwise".

Four levers (apply all four, every turn):
1. Recall, don't re-derive. Use what's already in context / memory / RULES.md before re-reading or re-asking. Don't restate facts already established this session.
2. Read surgically. Targeted Read (offset/limit), Grep/Glob over shelling out to cat/grep, an Explore subagent for broad fan-out (its file dumps die in its own context, you get the conclusion). Never re-read a file already read.
3. Generate lean. Recommendation over option-survey; no narration of work you're about to do. Write the minimum code that works — fewer generated tokens now, less review and maintenance later.
4. Avoid rework — the biggest hidden cost. Understand before changing; for bugs gather evidence before editing (see py-debug); let tests catch errors early (see tdd). A wrong change you have to undo costs several times its own tokens.`;

  if (mode === 'full') {
    s += `

Tool discipline: batch independent tool calls in one turn (parallel). Prefer the dedicated tool over a shell equivalent. Keep context stable to stay within the prompt cache window.`;
  }

  // The "never cut" band — token saving must never come at the cost of these.
  s += `

NEVER cut for tokens: understanding the problem fully; input validation at trust boundaries; error handling that prevents data loss; security and accessibility; anything the user explicitly asked for. Lean means less waste, not a flimsier result. When the user asks for an explanation, give it in full — that's requested output, not waste.

Tokenwise governs what you build and how much you read/say — not whether you do the job correctly.`;

  return s;
}

module.exports = { ruleset };
