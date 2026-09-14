# Execution and scheduling

These helpers execute only confirmed `project_type=ai`, `source=hireaicreator` projects. Validate business type before customer discovery; see onboarding. UGC uses [ugc-reporting.md](ugc-reporting.md). A generic config validation success does not mean the AI helpers support UGC. Missing legacy scope or a type/source mismatch must be resolved before running or sending; never change IDs by fuzzy name matching.

## Commands

Run Python helpers from the installed skill path, with absolute paths for user-owned configuration and output. No shell interpolation of secrets or remote content.

```text
python3 scripts/report.py validate --config CONFIG
python3 scripts/report.py collect --config CONFIG --project PROJECT_KEY --output SNAPSHOT
python3 scripts/render_card.py --snapshot SNAPSHOT --output CARD
python3 scripts/report.py due --config CONFIG --snapshot SNAPSHOT --state STATE --output TRIGGERS
python3 scripts/report.py deliver --config CONFIG --snapshot SNAPSHOT --state STATE --card CARD --triggers TRIGGERS --send
```

Pin the selected non-secret Feishu profile in `destination.profile`. The helper uses that explicit profile for send and readback. Before activation, verify that profile and credential access in the scheduler runtime; never silently fall back to a default app.

Use separate STATE files per project and destination. `collect` reads all pages from the configured history start with no future upper bound, filters workspace+campaign, and fetches post metadata and latest performance through CLI. It fails on inconsistent pagination rather than issuing a false complete report. Full data is saved locally; do not paste raw payloads to users. Validate the resulting scope and coverage before rendering. `collect` has no publication writes.

`render_card.py` is pure/offline. It uses the agreed V5 design and does not send. Feishu table components must remain at the body root; native collapsible panels need no callback backend. Preview the JSON and, on a user's authorized test, send/read back the actual card. If a large project exceeds the Feishu size limit, stop and split into numbered continuation cards while retaining every registered future row; never silently omit rows. Keep the two category layouts consistent.

`due` uses actual post published_at, timezone-aware daily times and UTC interval buckets. It returns outstanding trigger keys within catchup_minutes. It does not change state. If no triggers are due and STATE has no pending receipt, remain quiet. If a pending receipt exists, invoke deliver even with an empty trigger list so readback can finish. Invalid timestamps fail instead of using the schedule time as an invented publication timestamp.

Before delivering a checkpoint report, add a compact note to the card listing due threshold types and delayed execution (use `late_seconds` from the triggers). Label metric source/freshness independently of the due time. Coalesce all due triggers in a project into one card, retaining their individual keys. A one-time test can supply a unique trigger `[{"key":"PROJECT_KEY:DESTINATION_KEY:test:UNIQUE_VALUE","due_at":"AWARE_ISO_TIME","late_seconds":0}]`; generate actual values, do not use these symbolic strings. `destination_key()` is available in report.py. For a test, use a separate config copy with enabled=true, and a separate state file; this does not enable the scheduler.

`deliver` requires enabled=true, --send and existing destination authorization. It locks delivery state, persists pending content and a stable idempotency key before sending, saves the receipt before readback, and records completion only after readback. On readback failure, retry the existing receipt, not a fresh send. On uncertain send, reuse the existing pending key/content; after an hour, reconcile the chat rather than retrying automatically. Never erase state to force a retry. If a pending old batch is resolved while newer triggers exist, recompute due and deliver the newer batch on the next run.

## Host scheduler prompt

Adapt the following human-readable prompt to the actual configured paths and projects; use the host's supported scheduling tool to set cadence and timezone. Do not expose raw recurrence syntax to users.

“Use $museon-project-report with configuration at CONFIG. If paused, remain quiet. For each selected project, collect the latest CLI snapshot, calculate due triggers using its persistent STATE, and remain quiet if none are due and no pending receipt exists. Resolve pending receipts even with an empty due list before planning further deliveries. For a due project, generate the V5 report with separate promotion and warmup sections, add checkpoint and freshness information, send to the configured recipient, and read back before recording completion. Keep receipt and deduplication state. Do not publish or reschedule social content. Notify the user only for a delivered report, meaningful failure, or required action; avoid repeating the same unresolved error on every poll.”

A recurring task must not claim 30m/2h/6h exact historical metrics: Museon serves a synced store, and polling is not a time machine. Save snapshots per trigger for subsequent comparison. If a scheduler cannot meet the requested cadence, explain the constraint and choose a supported cadence with the user. Do not claim background execution works while the host is unavailable without verifying the host's capabilities.

## Validation checklist

- Complete pagination, matching workspace+campaign, no duplicate video IDs.
- Unknown category values are surfaced, not assigned arbitrarily.
- Distinct post denominators; null differs from zero; independent category waves.
- Actual timestamps drive checkpoints; future records never trigger post-release checks.
- Top 3 visible, up to 10 total; real returned post URLs; no callback-only expand button.
- Future schedules and cancelled counts retained; render failure is not reported merely as pending.
- One project card per trigger batch and destination; uncertain send/readback retains state.
- Failed collection does not silently render an old snapshot as current.
