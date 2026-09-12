# Review Log

## Review — README.md rewrite (2026-09-12)

**Scope:** Uncommitted change to `README.md` (working tree vs. `HEAD`). No other files changed since the last commit.

**Change summary:** Replaced the original 2-line README with an expanded overview: project vision, a "Status: In planning" callout, a highlights list, a stack table, a "Getting Started" section, and pointers to `planning/PLAN.md` and `LICENSE`.

### Findings

1. **Minor — `.env.example` referenced but doesn't exist yet.**
   The "Getting Started" section instructs `cp .env.example .env`, but no `.env.example` file exists in the repo yet (only a gitignored `.env`). PLAN.md §4 lists `.env.example` as a committed file, and this whole section is explicitly framed as the *future, not-yet-runnable* flow ("Once built, the intended flow is..."), so this is a forward-reference to planned state rather than a factual error about the present. Low priority; worth revisiting once `.env.example` is actually added to the repo, to confirm the command still matches.

2. **No other accuracy issues found.** Everything else in the README was checked against `planning/PLAN.md` and the actual repo tree:
   - Directory layout claims (`frontend/`, `backend/`, `scripts/`, `test/` don't exist yet) — confirmed accurate; the README correctly labels the project "In planning" rather than implying these are built.
   - Stack table (Next.js static export, FastAPI/`uv`, SQLite bind mount, SSE, LiteLLM→OpenRouter/Cerebras with `openrouter/openai/gpt-oss-120b`, simulator-default/Massive-optional market data) — matches PLAN.md §3, §6, §9 verbatim.
   - Port `8000` and single-container framing — matches PLAN.md §3, §11.
   - `$10,000` cash and 10 default tickers — matches PLAN.md §2, §7.
   - License link — `LICENSE` file exists at repo root.

### Verdict

No blocking issues. The one minor finding (`.env.example` not yet present) is a natural consequence of the project being pre-implementation and is already appropriately hedged in the README's own wording. No changes required before commit.

## Review — custom plugin and marketplace (2026-09-12)

**Scope:** Commit `036fb13` — "created custom plugin and marketplace". Adds three new files: `.claude-plugin/marketplace.json`, `independent-reviewer/.claude-plugin/plugin.json`, `independent-reviewer/hooks/hooks.json`. This is tooling infrastructure (a local Claude Code plugin marketplace), not part of the FinAlly application itself, so it isn't governed by `planning/PLAN.md`.

### Findings

1. **Blocking (for the plugin's own purpose) — `independent-reviewer/hooks/hooks.json` is a 0-byte empty file.**
   An empty file is not valid JSON, so if the plugin's hook wiring is ever loaded/parsed, it will fail. The plugin's whole stated purpose ("independent review of all changes since last commit") has no hook logic behind it yet — `plugin.json` and `marketplace.json` declare the plugin, but the hook that would actually do anything is unwritten. This is presumably expected work-in-progress scaffolding rather than a finished feature, but it means the plugin does nothing yet.

2. **Minor — `independent-reviewer/.claude-plugin/plugin.json` has no trailing newline.**
   POSIX text-file convention; harmless to JSON parsing, but inconsistent with `marketplace.json` which does end with one.

3. **No structural issues in `marketplace.json`.** `name`, `owner` (`name`/`email`), and a `plugins` array entry with `name`/`source`/`version`/`description` all match the conventional Claude Code marketplace manifest shape, and `source: "./independent-reviewer"` correctly points at the sibling plugin directory that was added in the same commit.

4. **Observation — this plugin looks like it's meant to replace/formalize the ad-hoc "change-reviewer" Stop hook behavior seen in this session** (the repeated automated review requests targeting this same `planning/REVIEW.md` file). Once `hooks/hooks.json` is filled in, worth checking it doesn't end up duplicating or conflicting with whatever Stop hook is already configured in `.claude/settings.json`.

### Verdict

Not blocking for the FinAlly app (this is dev tooling, unrelated to the product code), but the plugin as committed is inert: `hooks/hooks.json` needs real content before `independent-reviewer` does anything. Recommend filling in the hook definition (and adding a trailing newline to `plugin.json`) before relying on this plugin.
