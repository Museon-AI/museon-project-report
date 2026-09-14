---
name: museon-project-report
description: Configure customer reports by first choosing AI projects from HireAICreator or UGC projects from Museon, then selecting customers within that source. Use for onboarding, previewing, delivering, or adjusting project reports through Museon and Feishu CLI; bundled scheduling helpers support AI reports.
---

# Museon project reports

Use CLI commands for collection and messaging; never substitute direct production database queries. This skill reports existing content; it does not publish, reschedule, or repair content.

## Select the business type before the customer

After authorization, ask “你关心的是 AI 项目，还是素人项目？” before discovering customer candidates. Then list actual accessible customers/projects from the chosen source and ask the user to select. Reuse an explicit answer already given; never infer it from a brand name, granted workspace, or the first search result. Eazo or OKA can have both project types under the same account.

- `project_type=ai`, `source=hireaicreator`: discover HireAICreator projects through its current CLI schema. Use the AI execution and V5 layout below. `campaign-monitor +list` is not the AI customer directory; shared post-metric commands may only enrich confirmed HireAICreator publication IDs.
- `project_type=ugc`, `source=museon`: discover Museon campaign-monitor projects. Follow [ugc-reporting.md](references/ugc-reporting.md). Do not run the bundled AI collector, renderer or checkpoint scheduler on these IDs.

Show customer name, type, source, organization/workspace and actual project name together when asking for selection. Save that explicit choice and canonical workspace/project IDs. A project UUID's shape or a matching customer name cannot identify its source. If the source has no accessible results, check CLI capability and authorization; do not switch platforms. For “both”, confirm customers separately in each type and retain separate project keys and state.

Existing configurations without type/source require one-time scope confirmation before collection or delivery. Verify the original IDs against the chosen source, preserving destination, schedules and delivery history; do not silently mark old IDs as AI. The Python helpers reject missing or mismatched scope before accessing project data.

## Choose the mode

- First use or missing configuration: follow [onboarding.md](references/onboarding.md). Discover real accessible projects and recipients; do not populate another user's IDs from an example.
- Preview or one-time report: collect, render, review, and send only to the user's authorized destination. For AI follow [execution.md](references/execution.md); for UGC follow [ugc-reporting.md](references/ugc-reporting.md).
- Recurring execution: for AI follow [execution.md](references/execution.md), including trigger planning, readback, and persistent delivery state. For UGC follow [ugc-reporting.md](references/ugc-reporting.md) and verify a UGC-specific execution path before scheduling.
- Change configuration: preserve unrelated settings and delivery history; apply the requested project/time/channel/layout change, preview it, and update the existing scheduler instead of creating duplicates.

Python 3.11+ and `museoncli` are required; Feishu delivery additionally requires `lark-cli`. The command contract is verified against Museon CLI 0.6.0. Inspect `version`, `schema`, and relevant command help when using a different version. Do not silently downgrade or upgrade a user's installation. Credentials belong in CLI authentication storage, never in this skill, config, outputs, or the distributable.

## Report contract

This contract and the bundled Python helpers apply to AI/HireAICreator projects. For UGC fields and limitations read [ugc-reporting.md](references/ugc-reporting.md). For practical examples read [best-practices.md](references/best-practices.md).

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

Copy `assets/config.example.json` outside the installed skill, e.g. `~/.config/museon-project-report/config.json`. It is intentionally incomplete until onboarding selects a business type, customers and destination. Each project contains `key`, `name`, `project_type` (`ai` or `ugc`), `source` (`hireaicreator` or `museon` respectively), `workspace_id`, `campaign_id`, and IANA `timezone`. Record organization context when available. `campaign_id` belongs to the selected source; never reuse a same-name project's ID from the other platform. Use separate keys for the same customer's AI and UGC projects.

Keep snapshots, receipts, trigger files and per-project delivery state outside the package, in a user-owned state directory. Store no access tokens. The scripts never install a scheduler or turn monitoring on by themselves. Packaging or installing this skill is not activation of recurring sending.

After onboarding, a typical request is: “用 $museon-project-report 给选中的项目配置发布后 30 分钟、2 小时、6 小时快报，先发一张给我测试。”

## Repository installation and updates

This skill is maintained at https://github.com/Museon-AI/museon-project-report in `skills/museon-project-report`. Prefer HTTPS download of https://github.com/Museon-AI/museon-project-report/releases/latest/download/museon-project-report.zip; downloading requires neither a Git executable nor a GitHub account. Extract the complete skill folder into the host's personal skills directory. Record the release version or revision used. Back up an existing locally modified skill folder to a local directory before replacing it, preserving separate configuration and delivery state. Repository installation does not log in, send a test, or enable a scheduler.

Full operation requires Python 3.11+, Museon CLI (validated against 0.6.0), and Feishu CLI. The delivery helper uses Unix `fcntl` file locking: native Windows delivery is not supported. Windows users need a separately configured and verified Linux/WSL environment; do not claim successful setup until authentication, a permitted test, and scheduler execution have been verified there.
