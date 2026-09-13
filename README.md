# Museon Project Report

A Codex skill for project publishing reports through Museon CLI and Feishu CLI. Promotion and warmup content have separate schedules, average views, top posts and publication checkpoints.

## Install without Git

Download [museon-project-report.zip](https://github.com/Museon-AI/museon-project-report/releases/latest/download/museon-project-report.zip), drag it into Codex, and say:

> 安装这个 Skill，然后引导我选择客户项目、日报时间和飞书接收人。先发测试卡片，我确认后再启用定时。

Or give Codex the [skill directory](https://github.com/Museon-AI/museon-project-report/tree/main/skills/museon-project-report) and ask it to install using HTTPS download. No Git executable or GitHub account is needed to download the public package.

Museon and Feishu login is still required to access your own projects and send reports. The verified CLI contract is Museon CLI 0.6.0; the complete runtime requires Python 3.11+. The current delivery helper requires a Unix-compatible environment; native Windows delivery is not supported. Installation alone does not enable recurring sends.

## Maintenance

Edit `skills/museon-project-report`, validate the skill and scripts, then publish a release ZIP containing the `museon-project-report` folder. Keep private configuration, tokens, customer snapshots and delivery state out of this repository.
