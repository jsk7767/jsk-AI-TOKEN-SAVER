#!/usr/bin/env node
"use strict";

const reminder =
  "JSK-SAVE: cache→search→slice; bound tools; no unchanged reread/passed rerun; findings+PASS evidence only.";

let input = "";
process.stdin.on("data", chunk => { input += chunk; });
process.stdin.on("error", () => process.exit(0));
process.stdin.on("end", () => {
  if ((process.env.JSK_TOKEN_SAVER || "").toLowerCase() === "off") return;
  try {
    if (input) JSON.parse(input);
    process.stdout.write(JSON.stringify({
      hookSpecificOutput: {
        hookEventName: "UserPromptSubmit",
        additionalContext: reminder
      }
    }));
  } catch (_) {
    // Hook failures must never block a user prompt.
  }
});
