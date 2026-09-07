# conveyor

An org GitHub App plus an always-on **Django** service that owns the
`merge → release → production` pipeline for `the-hcma`.

- **The App** — one org-owned GitHub App (`Conveyor`), installed on selected repos,
  minting per-run repo-scoped tokens for release-PR creation and CD.
- **The service** — receives GitHub webhooks, keeps a configurable recent window
  queryable in Postgres, streams every delivery to **Redpanda** for durable
  long-retention replay, lets other systems **subscribe** by repo + event type
  (Kafka topics or a cursor **pull API**), and runs **pre-configured actions** on
  matching events (e.g. `release` published → publish the release + advance
  production to the new version, behind the existing protected-environment
  reviewer gate).

## Status

Bootstrapping. See **[the-hcma/conveyor#1](https://github.com/the-hcma/conveyor/issues/1)**
for the full design, phases, and milestones. Predecessors:
[repository-helpers#607](https://github.com/the-hcma/repository-helpers/issues/607)
(the App) and
[repository-helpers#374](https://github.com/the-hcma/repository-helpers/issues/374)
(webhook wake layer) — both closed and folded in here.

## Architecture (target)

```
GitHub (Conveyor App webhook)
        │  POST /webhooks/github   (X-Hub-Signature-256, X-GitHub-Delivery)
        ▼
  Conveyor (Django)
    ingest → verify HMAC → dedupe delivery id
      ├─► Postgres  "hot" tier   (configurable window)
      └─► Redpanda  gh.<event>   (durable log)
    action engine (Redpanda consumer)  → pre-configured handlers
    pull API   GET /api/events?since=<cursor>
    Django UI  deliveries / subscriptions / action runs
```

## Development

Django + `uv`. Python is pinned in `.python-version`.

```bash
uv sync --group dev                       # venv + deps
cp .env.example .env                      # local config (never commit .env)
CONVEYOR_DEBUG=1 uv run python manage.py migrate
CONVEYOR_DEBUG=1 uv run python manage.py runserver
uv run pytest -m 'not live' -q            # hermetic tests
```

Local CI gate (from a repository-helpers clone):

```bash
"${REPOSITORY_HELPERS_DIR:-$HOME/work/ai/repository-helpers}/scripts/dev/pre-pr-checks"
```

Ground rules for contributors (human or agent) live in
**[AGENTS.md](./AGENTS.md)** and **[.cursor/rules/](./.cursor/rules/)** — read both
at the start of every session.

## License

[MIT](./LICENSE) — Copyright (c) 2026 the-hcma.
