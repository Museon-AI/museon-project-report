# Museon Project Report

A Codex skill for customer reports delivered through Museon CLI and Feishu CLI. Setup first asks whether you monitor **AI projects** or **UGC projects**, then lets you choose customers accessible within that project type. AI data comes from HireAICreator; UGC data comes from Museon campaigns. A customer may have both, so its name never determines the source.

## Install without Git

Copy this into Codex:

> 帮我安装 https://github.com/Museon-AI/museon-project-report 的日报 Skill，检查并补齐 Museon 和飞书 CLI，完成登录授权。先问我关注 AI 项目还是素人项目，再列出该类型下我有权限的客户，让我自己选。然后配置日报时间和接收人，先发测试卡片，我确认后再启用定时。如果我已经明确选过类型或客户，就沿用，不要重复问。

You can also download [museon-project-report.zip](https://github.com/Museon-AI/museon-project-report/releases/latest/download/museon-project-report.zip), drag it into Codex, and send the same request. Public HTTPS download needs neither Git nor a GitHub account. Museon and Feishu authorization is still required to access your projects and deliver reports.

## What happens after login

1. Choose **AI projects** or **UGC projects** (素人项目). To monitor both, configure each type separately.
2. Choose customers from that type's live accessible list. For example, Eazo or OKA may have both AI and UGC projects; selecting AI must not silently include their UGC campaigns.
3. Choose the timezone, frequency and recipient, then check a real-data test card.
4. Activate supported recurring execution after confirming the test. Later, ask Codex to change customers, times or recipients directly.

The included publishing/checkpoint scripts support **AI projects**: promotion and warmup have separate schedules, mean views and Top posts. UGC reports require collection through the installed Museon campaign CLI and a separately verified execution path; this package does not provide a ready-made UGC recurring collector. Do not treat selecting UGC as enabling the AI script for UGC.

See [onboarding](skills/museon-project-report/references/onboarding.md) for setup and [best practices](skills/museon-project-report/references/best-practices.md) for customer selection and metric definitions. The validated CLI release is Museon CLI 0.6.0; inspect the installed schema for the commands available today. Python 3.11+ is required. The included delivery helper needs a Unix-compatible environment; native Windows delivery is not supported. Installation alone does not enable recurring sends.

## Maintenance

Edit `skills/museon-project-report`, validate the skill and scripts, then publish a release ZIP containing the `museon-project-report` folder. Back up an existing installation locally before replacement. Keep private configuration, tokens, customer snapshots and delivery state out of this repository. Old configurations without a project type must be confirmed and migrated before collection resumes.
