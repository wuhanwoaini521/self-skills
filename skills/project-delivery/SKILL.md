---
name: project-delivery
description: Orchestrate end-to-end engineering delivery from a short user request - classify the task, analyze requirements, plan, implement, run functional tests, run conditional UI review, run an independent code review, fix findings, regress, accept, and write auditable execution logs under .ai-runs/. Use when the user asks to implement a feature, fix a bug, modify or build project behavior, refactor code, redesign or improve a page or UI, upgrade dependencies, or otherwise deliver an engineering task in a repository, even without an explicit workflow prompt. Do not use for read-only questions such as explaining code or interpreting an error message.
---

# Project Delivery

## Overview

用户给一句话（"修一下这个 bug"、"增加一个搜索功能"、"这个页面太丑了，重新设计"），本 skill 把它当成一次**可交付的软件工程任务**，自动跑完理解 → 分类 → 计划 → 开发 → 测试 → Review → 修复 → 回归 → 验收 → 留痕。

它是 **Workflow Orchestrator**，不是 coding style / UI design / 测试框架 skill：它不复制别人的内容，只负责判断"这是什么任务、需要哪些阶段、要调用哪些 skill、要过哪些门禁"。

两条主原则：

1. **固定质量门禁，动态选择阶段。** 每个任务都必须有"验证 + 独立 review + 回归 + 验收结论"；但具体阶段按任务类型裁剪（Python 后端 bug 不启动 UI review）。
2. **流程是可靠性的来源，不是负担。** 小任务走轻量留痕，大任务才上完整仪式；不要把 5 分钟的修复变成 2 小时的流程表演。

## 何时触发 / 何时不触发

触发（用户要求实际改动、交付）：

- 实现功能、修 bug、改行为、重构代码、重做或优化页面/UI、升级依赖、任何"把这件事做完"的请求。

不触发（只读问答）：

- "解释一下这段代码"、"这个报错是什么意思"、"这段实现为什么这么写"、"帮我看下这个 diff 有什么风险"——只要没有要求修改项目，就不要启动完整流程，按普通问答回答即可。

边界情况：用户明确说"只分析不改代码"时，走分析与计划，产出结论和 `02-plan.md`，不进入实现阶段。

## 核心流程

```text
Short user request
        ↓
Understand context   (git status、仓库规则、工具链)
        ↓
Classify task        (bug-fix / new-feature / ui-feature / ui-redesign / refactor / maintenance)
        ↓
Choose workflow      (阶段集 + 门禁 + skill 组合)
        ↓
Plan                 (步骤、预期改动文件、测试与 review 策略、验收标准)
        ↓
Implement            (读懂再改、最小改动、跟随仓库约定)
        ↓
Functional test      (针对性测试 → 集成 → 关键手工验证)
        ↓
Review               (code review；UI 任务加独立 UI review)
        ↓
Fix                  (P0/P1 必修，修完重跑针对性验证)
        ↓
Regression           (按改动风险选覆盖面)
        ↓
Final acceptance     (PASS / PASS_WITH_NOTES / BLOCKED)
        ↓
Execution report     (.ai-runs/ 下的可审计记录)
```

## 阶段与门禁（精简版）

| 阶段 | 做什么 | 出口条件 | 细则 |
| --- | --- | --- | --- |
| Understand | `git status`、仓库指令、真实工具链 | 知道改哪儿、用什么命令 | `references/workflow.md` |
| Classify | 判定任务类型与规模 | 类型唯一确定，UI 判定明确 | `references/task-routing.md` |
| Analyze | 目标、验收标准、约束、风险 | 验收标准可判定真假 | `references/requirements-analysis.md` |
| Plan | 步骤、预期文件、测试与 review 策略 | 用户不需要额外确认即可开工 | `references/workflow.md` |
| Develop | 实现改动 | 改动最小且符合仓库约定 | `references/development.md` |
| Functional test | 跑针对性测试与关键路径验证 | 与改动直接相关的路径已验证 | `references/functional-testing.md` |
| UI review | 仅 UI 任务：截图、响应式、可访问性 | P0=0，合理 P1 已处理 | `references/ui-review.md` |
| Code review | 独立、挑战式 review | 无未处理的 P0/P1 | `references/code-review.md` |
| Fix | 修 review 与测试发现的问题 | 针对性验证重跑通过 | `references/workflow.md` |
| Regression | 按风险选覆盖面 | 无非预期回归 | `references/regression.md` |
| Acceptance | 对照原始请求逐条判定 | 给出明确结论 | `references/final-acceptance.md` |
| Report | 写 `.ai-runs/<run>/` | 日志是工程证据，不是脑内过程 | `references/execution-log.md` |

各阶段的详细写法只在需要时读对应 reference，不要一次性全读。

## 任务路由

v0.1 支持六种类型，路由细节见 `references/task-routing.md`。

| 类型 | 典型输入 | 阶段集 | 条件门禁 |
| --- | --- | --- | --- |
| `bug-fix` | 修一下这个报错、为什么这里失败 | analyze → reproduce → fix → targeted test → regression → code review → acceptance | 无 UI review |
| `new-feature` | 增加搜索功能、新增模块 | requirements → architecture review → plan → implement → functional test → code review → regression → acceptance | 触达 UI 时加 UI review |
| `ui-feature` | 增加筛选弹窗、新卡片、新交互 | requirements → UI context → design guidance → implement → functional test → UI review → fix → regression → final review | UI review 必做 |
| `ui-redesign` | 重新设计这个页面、优化整个 UI | UI audit → design direction →（大范围时 golden sample）→ implement → functional test → independent UI review → fix → re-review → code review → responsive validation → regression → final UI review | UI review + 响应式必做 |
| `refactor` | 重构这个模块、整理架构 | understand behavior → identify goal → safety tests → refactor → regression → code review → acceptance | 行为不变是硬约束 |
| `maintenance` | 升级依赖、整理配置、改 CI、修 lint | inspect → plan → change → validation → compatibility check → review | 兼容性检查必做 |

类型拿不准时：改动目标是"修对"→ bug-fix；"新增能力"→ new-feature；产物主要落在视觉/交互层 → ui-feature 或 ui-redesign；外部行为不变、只改内部结构 → refactor；依赖/配置/工具链 → maintenance。一个请求同时命中多种时，选**风险最高**的那一类（例如后端 bug 顺手改了页面 → ui-feature）。

## 规模与仪式强度

先估规模，再决定流程重量：

- **small**：单文件、行为局部、无设计决策。轻量留痕（`00-request.md`、`01-analysis.md`、`09-final-report.md`），review 只看改动本身。
- **standard**：默认。完整阶段集 + 对应日志文件。
- **large**：跨模块/跨页面/迁移类任务。先切 milestone（analysis → foundation → implementation → validation → review），每个 milestone 记录状态，但**不要每步都回头问用户是否继续**；UI 大改先做 golden sample，评审通过再扩散。

判断不清时往 small 侧压；只有确定跨模块或跨页面才升级到 large。

## Subagent 策略

当前环境支持 subagent 时，main agent 保持编排者角色，按需派生，**不要每次全开**：

- Requirements / Analysis agent：需求或影响面很宽时，先并行摸清相关模块。
- Implementation agent：可切分的独立实现片段。
- Functional Test agent：测试与验证可与实现并行准备。
- UI Review agent：仅 UI 任务，与实现者分离。
- Code Review agent：始终与实现者分离。
- Regression agent：改动面大时独立跑回归。

独立性是硬要求：review 类 agent 必须独立于实现过程，prompt 用挑战式措辞，例如：

```text
Find concrete reasons this implementation should not be accepted yet.
```

```text
Find concrete reasons this UI should not be accepted yet.
```

不要让实现者自己给自己的代码写"看起来没问题"的结论。环境不支持 subagent 时，串行执行同样流程，但 review 阶段显式切换视角重新读一遍改动。

## Skill 组合与发现安全

需要设计能力时主动发现并调用，不要等用户点名：

```text
project-delivery → classify: ui-redesign → 载入 ui-ux-pro-max（若存在）→ 设计方向 → 实现 → UI review
```

规则：

- 若相关 skill 存在（UI 设计、文档、测试框架等），就用它，不要复制它的内容进本 skill。
- **不要假设某个 skill 一定存在**：不存在时用内置能力继续，并在最终报告里记一句"专用 skill 不可用"。
- 可选 skill 缺失绝不能导致任务失败。

## 仓库与工具链发现

先看项目，再动手，不要假设技术栈：

- 仓库指令优先：`AGENTS.md`、`CLAUDE.md`、`CONTRIBUTING.md`、`README`、项目规则、lint/test 配置。它们优先于本 skill 中可调整的通用流程。
- 检测真实工具链：`pyproject.toml`、`package.json`、`Cargo.toml`、`go.mod`、`pom.xml` 等。
- 使用仓库已有的测试 / lint / build 命令，不在流程里硬编码 `pytest` 或 `npm test`。

## 硬性规则

- **保护已有工作**：任何任务开始前先 `git status`。存在无关改动就保护它们，存在相关改动先读懂再改。绝不覆盖用户工作。
- **不强制提交**：默认不 commit、不 push。只有用户明确要求，或仓库指令明确要求时才提交；最终报告必须给出 `git status` 现状。
- **不泄露密钥**：不打印 secret、不把凭据写进日志、不 dump 环境变量。日志里的命令必须 redact，例如 `TOKEN=***`。
- **不记录隐式推理**：`.ai-runs/` 只记观察、决策、证据、命令、改动文件、测试结果、review 发现、修复与遗留风险。
- **用户改需求**：记为 Scope Change，调整后续计划，不要继续执行旧目标。
- **不过度澄清**：能从仓库、测试、文档、代码推断的先自行推断；只有真正影响目标且无法合理推断时才问。禁止问"要继续吗""要不要 review""要不要测试"。
- **BLOCKED 有严格定义**：仅限真实阻塞（缺凭据、外部系统不可用、必需依赖不可得、环境不可恢复）。任务复杂不等于 BLOCKED。
- **停止条件**：`P0 = 0`、合理 `P1 = 0`、测试通过、验收标准满足即停。P2 不驱动无限打磨。
- **修复循环**：失败 → 分析 → 修 → 重跑针对性验证 → 再回归，不允许第一次失败就收工。

## 执行留痕

用脚本做确定性的目录准备，不手搓目录结构：

```bash
python scripts/init_run_log.py --task-type ui-redesign --title "history redesign"
```

输出 `.ai-runs/2026-09-29-history-redesign/`。同一天同名会自动追加 `-2`，绝不覆盖既有 run。

- 极小任务可用 `--scale small`；极小且不需要持久记录可用 `--single-file` 生成单个 `run.md`。
- 脚本只做文件系统准备，不负责写业务内容。
- `.ai-runs/` 是否入库由项目决定：本 skill **不自动改 `.gitignore`**，只在最终报告里指出日志位置。
- 文件字段、命名规则、留痕强度分级见 `references/execution-log.md`。

## 验收结论

统一三档，不使用"差不多好了""看起来可以"：

- `PASS`：请求的行为已完成，门禁全过，无遗留阻断项。
- `PASS_WITH_NOTES`：功能可用，但有已记录的遗留项或已知限制。
- `BLOCKED`：真实阻塞，需要外部条件才能继续。

## References

- `references/workflow.md`：各阶段详解、失败修复循环、大型任务 milestone、golden sample、Scope Change。
- `references/task-routing.md`：六类任务的判定信号、阶段集与门禁细则。
- `references/requirements-analysis.md`：需求分析规则与验收标准写法。
- `references/development.md`：实现阶段的硬性约束。
- `references/functional-testing.md`：测试优先级与验证要求。
- `references/ui-review.md`：UI review 维度、P0/P1/P2 分级与 review loop。
- `references/code-review.md`：独立 review 的维度与挑战式 prompt。
- `references/regression.md`：按改动风险选择回归范围。
- `references/final-acceptance.md`：验收清单与三档结论定义。
- `references/execution-log.md`：`.ai-runs/` 目录结构、各文件字段、命名与留痕强度。

## scripts

- `scripts/init_run_log.py`：创建 run 目录与日志骨架，防止覆盖，支持 dry-run 与测试用 `--date`。
