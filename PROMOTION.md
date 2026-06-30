# Promotion Kit

Repository: https://github.com/YfengJ/change-radar

## Tagline

AI coding is fast. Change Radar is the seatbelt.

## Short Pitch

Change Radar is a Codex skill and zero-dependency scanner that makes AI agents map blast radius, risk score, touched contracts, hidden risk, verification plan, and CI gates before changing code or declaring work done.

The repo now includes visual diagrams for the agent workflow, risk ladder, and CI gate.

## X / Twitter

I made Change Radar, a Codex skill for safer AI-assisted coding.

It pushes the agent to map:
- blast radius
- P0/P1/P2/P3 risk score
- touched contracts
- hidden risk cues
- possible secrets / focused tests / skipped tests in added lines
- meaningful verification
- CI risk gates
- completion evidence

AI coding is fast. This is the seatbelt.

https://github.com/YfengJ/change-radar

## LinkedIn

I built Change Radar, a Codex skill for making AI-assisted coding safer.

The core idea is simple: before an agent changes code or says "done", it should understand the blast radius, touched contracts, risk cues, and evidence needed to verify the work.

The skill includes a lightweight Python scanner that inspects git changes, project manifests, risky file paths, high-signal added lines, nearby tests, likely verification commands, missing evidence, and CI risk thresholds. The workflow then asks the agent to map contracts and prove completion requirement by requirement.

AI coding is fast. The missing piece is often engineering judgment around the patch.

Repo: https://github.com/YfengJ/change-radar

## Hacker News / Reddit

Show HN: Change Radar, a Codex skill for safer AI-assisted coding

I built a small Codex skill called Change Radar. It is meant for the moment before an AI coding agent edits a repo or claims a task is complete.

It makes the agent create a compact change brief, scan the repository for risk cues, produce a P0/P1/P2/P3 risk score, map touched contracts, choose verification commands, and audit completion against the original request.

There is also a dependency-free Python script that reports changed files, project signals, risky paths, possible secrets, focused/skipped tests, nearby tests, blocking evidence gaps, suggested validation commands, JSON output, and optional CI failure gates.

Repo: https://github.com/YfengJ/change-radar

## Chinese Launch Post

我做了一个 Codex skill：Change Radar。

它解决的问题很直接：AI 写代码越来越快，但真正容易翻车的地方往往不是“能不能写出 patch”，而是改动范围、隐含契约、测试选择和最终验收证据。

Change Radar 会让 agent 在动代码前后做一套工程化检查：

- 这次改动的 blast radius 是什么
- 风险级别是 P0/P1/P2/P3，分数是多少
- 碰到了哪些 API / 数据 / 配置 / UI / 部署契约
- 哪些文件路径暴露了高风险信号
- 新增行里有没有疑似 secret、test.only 或跳过测试
- 应该跑哪些测试才算真的证明了改动
- CI 里要不要因为高风险直接阻断
- 最后能不能逐条对上用户的原始需求

我还放了一个零依赖 Python 扫描脚本，可以自动看 git diff、项目类型、风险线索、新增行高风险内容、附近测试、阻断缺口、推荐验证命令，并输出 JSON 或按风险阈值让 CI 失败。

AI coding is fast. Change Radar is the seatbelt.

https://github.com/YfengJ/change-radar

## GitHub Description

Risk score, verification plan, and CI gate for safer AI-assisted coding with Codex.

## Suggested Topics

codex, codex-skill, ai-coding, coding-agents, code-review, testing, developer-tools, software-engineering, risk-analysis
