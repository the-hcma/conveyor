# AGENTS.md — Ground Rules for conveyor

This file is the single source of truth for how contributors (human or AI) work on
this repository. `CLAUDE.md` (a `@AGENTS.md` import) and
`.github/copilot-instructions.md` are thin shims so Claude Code and Copilot reach
this same guidance — do not put rules in them.

---

## Session startup

At the **start of every agent session**, before acting from assumed conventions:

1. Read this `AGENTS.md` in full.
2. Read every rule under `.cursor/rules/*.mdc` whose front matter has
   `alwaysApply: true`, plus any rule whose `globs` match files you will touch.
   `AGENTS.md` and the `.cursor/rules/` files together are the contract — neither
   alone is complete.

Several org rules (`pre-pr-checks`, `pr-ship-and-review`, `stacking-tool`, …)
delegate to tooling in **repository-helpers**. Resolve that clone once:

```bash
rh="${REPOSITORY_HELPERS_DIR:-$HOME/work/ai/repository-helpers}"
```

---

## What this repo is

- **The Conveyor GitHub App** — org-owned, installed on selected repos, mints
  per-run repo-scoped tokens for release-PR creation and CD. Its permission set
  grows one phase at a time (see [issue #1](https://github.com/the-hcma/conveyor/issues/1)).
- **The Conveyor service** — a Django app that ingests GitHub webhooks, keeps a
  configurable hot window in Postgres, streams every delivery to **Redpanda**,
  serves subscribers (Kafka topics + a cursor pull API), and runs pre-configured
  **actions** on matching events.

Design constraint carried from repository-helpers#374: **webhooks are a scheduler,
not a policy engine.** An action handler that drives another workflow hands off; it
does not re-implement that workflow's decision logic. Pull-API consumers still
fetch live state and decide for themselves after a wake.

---

## Language & Runtime

- **Python ≥ 3.12**, **Django**. Dependency + venv management via **`uv`**
  (`pyproject.toml` + `uv.lock`, both committed and kept in sync).
- **Redpanda** (Kafka API) is the durable event log; producer/consumer code uses
  **`confluent-kafka`** (`confluent-kafka-python`).
- **Postgres** is the primary datastore (SQLite only for throwaway local spikes).
- Runtime services: `conveyor.service` (web, gunicorn), `conveyor-worker.service`
  (action-engine Redpanda consumer), `redpanda.service`, behind **Caddy**.
- No committed secrets. All credentials come from the environment / host — see
  `.cursor/rules/no-secret-exposure.mdc`. `.env.example` documents the keys.

---

## Formatting & Style

- **`ruff format`** is the formatter (line length 100). Run it before every commit
  and before the pre-PR gate.
- **`ruff check`** must be clean. Type-check with **`pyright`** (or `mypy` if the
  repo standardizes on it later) — no new type errors.
- Follow `.cursor/rules/lexicographic-code-organization.mdc` (public block then
  private `_` block; ASCII sort within each; sorted closed-set literals).
- Every outbound network call (GitHub API, Kafka admin, webhooks out) carries an
  explicit timeout and bounded retry — `.cursor/rules/remote-timeouts-retries.mdc`.

---

## Testing

- Tests live in `tests/` and run under **`pytest`**. Prefer the hermetic subset
  (no network, no live Kafka/Postgres — use fakes / `pytest-django` + sqlite or
  testcontainers gated behind a marker) for the CI gate.
- **Every new behaviour or bug fix ships with a test.**
- Tests must be deterministic: no `sleep` for timing, no real network, no real
  GitHub or Kafka calls in the default suite.
- Webhook-ingestion tests must cover: valid HMAC accept, bad/absent signature
  reject, duplicate `X-GitHub-Delivery` dedupe.

---

## Repository

- Remote: `https://github.com/the-hcma/conveyor` (public).
- Never commit secrets, credentials, private keys, or webhook payloads containing
  tokens. Use environment variables and the host secret store.

---

## Commits, Stacking & Pull Requests

- Stacking backend: **`gh-stack`** (see `.github/stacking-tool`). Follow the
  canonical gh-stack skill in repository-helpers
  (`${rh}/.cursor/skills/gh-stack/SKILL.md`).
- Never work directly on `main`. One logical change per branch / commit.
- **Before opening or submitting a PR**, run
  **`"${rh}/scripts/dev/pre-pr-checks"`** from your feature worktree (must exit 0),
  then submit with bare **`gh stack submit --auto`** from the same worktree. Do not
  use `submit-stack` from a consumer repo.
- Apply `ruff format` before the gate; commit format-only diffs before submit.
- Follow **Conventional Commits**: `feat:`, `fix:`, `chore:`, `docs:`, `test:`,
  `refactor:`.
- **Commit identity:** follow `${rh}/.cursor/rules/git-commit-identity.mdc` — no
  `Co-authored-by:` or agent/machine trailers, and verify commit signing
  (`commit.gpgsign` / `user.signingkey`) plus `~/.cursor/cli-config.json`
  attribution before committing.
- PRs must be **published (not draft)** with at minimum a **Summary** and a
  **Test plan**, and reference the relevant milestone in
  [issue #1](https://github.com/the-hcma/conveyor/issues/1).
- Merge via GitHub's native merge queue — **Enable auto-merge / Merge when ready**
  (`gh pr merge --auto --squash`). Do **not** use a `merge-it` label.
- After every push, **`"${rh}/scripts/dev/post-pr-submission-checks" --pr <n>`**
  must pass, then follow `.cursor/rules/pr-ship-and-review.mdc` (agent review loop;
  reply before resolve).
- Never merge a PR until all checks have run and are green.

---

## Security

- Verify `X-Hub-Signature-256` against the webhook secret on **every** inbound
  request (constant-time compare); reject otherwise.
- Per-subscription API keys for the pull API; no anonymous reads.
- No dynamic `eval` / command construction from webhook-controlled strings.
- Validate and resolve any filesystem path derived from external input before use.
- Follow `.cursor/rules/no-secret-exposure.mdc` and
  `.cursor/rules/remote-timeouts-retries.mdc`.

---

## After changing CI / config

Run `"${rh}/scripts/github-repo-lint" --repo the-hcma/conveyor --suggest` after
editing anything under `.github/**` or `.cursor/rules/**`
(`.cursor/rules/repo-practices-after-config-change.mdc`).

---

## CI Checks (all must pass)

Run locally via `"${rh}/scripts/dev/pre-pr-checks"` before every PR. No PR merges
with a failing CI check. No exceptions.
