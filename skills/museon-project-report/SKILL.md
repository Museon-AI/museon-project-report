---
name: museon-project-report
description: Configure and deliver HireAICreator project publishing reports through Museon CLI and Feishu CLI, with separate promotion and warmup schedules, average views, top posts, and post-publication checkpoints. Use for onboarding, previewing, scheduling, or adjusting these project reports.
---

# Museon project reports

Produce one project report per card, using the approved V5 layout. Use CLI commands for collection and messaging; never substitute direct production database queries. This skill reports existing content; it does not publish, reschedule, or repair content.

## Choose the mode

- First use or missing configuration: follow [onboarding.md](references/onboarding.md). Discover real accessible projects and recipients; do not populate another user's IDs from an example.
- Preview or one-time report: collect, render, review, and send only to the user's authorized destination. Follow [execution.md](references/execution.md).
- Recurring execution: follow [execution.md](references/execution.md), including trigger planning, readback, and persistent delivery state.
- Change configuration: preserve unrelated settings and delivery history; apply the requested project/time/channel/layout change, preview it, and update the existing scheduler instead of creating duplicates.

Python 3.11+ and `museoncli` are required; Feishu delivery additionally requires `lark-cli`. The command contract is verified against Museon CLI 0.6.0. Inspect `version`, `schema`, and relevant command help when using a different version. Do not silently downgrade or upgrade a user's installation. Credentials belong in CLI authentication storage, never in this skill, config, outputs, or the distributable.

## Report contract

The pure renderer is `scripts/render_card.py`. Read its help for the exact invocation; input is the snapshot produced by `scripts/report.py collect`.

- Yellow header and yellow project total; bold, centered **推广内容** and **养号内容** section titles.
- Both sections use the same structure: today's publishing count and mean views, next schedule time, past and all registered future waves, latest elapsed wave's top posts, and actionable exceptions. Empty categories remain visible.
- Each category selects its own latest elapsed wave. Display the top 3 by latest synced cumulative views, with native expansion to ranks 4–10. Do not fall back to an older successful wave without disclosing it.
- Wave mean views use distinct published posts with non-null views, including genuine zeroes. Missing metrics and no published posts display `—`. Do not divide by all scheduled posts or average account averages. Cancelled videos are excluded from expected counts and are not failures.
- Report today's mean views by actual publication date in the configured timezone; today's expected count is by scheduled date. State this distinction in the note.
- Show metric freshness. Synced cumulative values observed at 30m/2h/6h are **observations at the checkpoint**, not exact historical platform values at those ages. Late runs and stale metrics must be labelled; never invent absent historical measurements.
- `scheduled` does not prove publication. Check `published_content_id`, actual post timestamp, manual confirmation, `render_job_status`, and materialization errors. Describe only recorded evidence.
- Match project by both workspace and campaign. Classify with `account_operation_stage=promotable|warmup`; flag unclassified rows instead of guessing based on copy or group presence.

## Persistent configuration

Copy `assets/config.example.json` outside the installed skill, e.g. `~/.config/museon-project-report/config.json`. It is intentionally incomplete until onboarding selects projects and destination. Each project contains `key`, `name`, `workspace_id`, `campaign_id`, and IANA `timezone`.

Keep snapshots, receipts, trigger files and per-project delivery state outside the package, in a user-owned state directory. Store no access tokens. The scripts never install a scheduler or turn monitoring on by themselves. Packaging or installing this skill is not activation of recurring sending.

After onboarding, a typical request is: “用 $museon-project-report 给选中的项目配置发布后 30 分钟、2 小时、6 小时快报，先发一张给我测试。”

## Repository installation and updates

This skill is maintained at https://github.com/Museon-AI/museon-project-report in `skills/museon-project-report`. Prefer HTTPS download of https://github.com/Museon-AI/museon-project-report/releases/latest/download/museon-project-report.zip; downloading requires neither a Git executable nor a GitHub account. Extract the complete skill folder into the host's personal skills directory. Record the release version or revision used. Back up an existing locally modified skill folder to a local directory before replacing it, preserving separate configuration and delivery state. Repository installation does not log in, send a test, or enable a scheduler.

Full operation requires Python 3.11+, Museon CLI (validated against 0.6.0), and Feishu CLI. The delivery helper uses Unix `fcntl` file locking: native Windows delivery is not supported. Windows users need a separately configured and verified Linux/WSL environment; do not claim successful setup until authentication, a permitted test, and scheduler execution have been verified there.
