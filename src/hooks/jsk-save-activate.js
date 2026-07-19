#!/usr/bin/env node
"use strict";

const fs = require("fs");
const os = require("os");
const path = require("path");

if ((process.env.JSK_TOKEN_SAVER || "").toLowerCase() === "off") {
  process.exit(0);
}

const roots = [];
if (process.env.CLAUDE_PLUGIN_ROOT) {
  roots.push(process.env.CLAUDE_PLUGIN_ROOT);
}
roots.push(path.resolve(__dirname, "..", ".."));

const candidates = [];
for (const root of roots) {
  candidates.push(
    path.join(root, ".agents", "skills", "jsk-ai-token-saver", "SKILL.md"),
    path.join(root, "skills", "jsk-ai-token-saver", "SKILL.md")
  );
}
candidates.push(
  path.join(os.homedir(), ".claude", "skills", "jsk-ai-token-saver", "SKILL.md")
);

function safeRead(candidate) {
  try {
    const stat = fs.lstatSync(candidate);
    if (!stat.isFile() || stat.isSymbolicLink() || stat.size > 16384) {
      return "";
    }
    return fs.readFileSync(candidate, "utf8");
  } catch (_) {
    return "";
  }
}

let skill = "";
for (const candidate of candidates) {
  skill = safeRead(candidate);
  if (skill) break;
}

const fallback =
  "JSK-SAVE. correctness>safety>evidence>success>tokens. " +
  "cache→search→slice; bound tools; no unchanged reread/passed rerun; " +
  "return findings and PASS evidence, not transcripts.";
const body = skill ? skill.replace(/^---[\s\S]*?---\s*/, "").trim() : fallback;
process.stdout.write(body);
