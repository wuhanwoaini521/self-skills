# Workflow

各阶段的执行细则。SKILL.md 已经给出主干，这里只写"具体怎么做、什么时候停"。

## Understand

1. `git status`（含未跟踪文件）与当前分支。
2. 读仓库指令：`AGENTS.md`、`CLAUDE.md`、`CONTRIBUTING.md`、`README`、lint/test 配置。仓库指令优先于本流程中可调整的部分。
3. 检测真实工具链：看 `pyproject.toml` / `package.json` / `Cargo.toml` / `go.mod` / `pom.xml` 等，得出真实的测试、lint、build、运行命令。
4. 定位受影响模块：入口、调用方、共享组件、公共 API。

产出：写进 `01-analysis.md` 的"当前架构 / 相关文件 / 约束"。

## Classify

按 `task-routing.md` 判定唯一任务类型与规模（small / standard / large）。拿不准或同时命中多类时，选风险最高的一类。

产出：`00-request.md` 里的 Task Type 与 Scale。

## Analyze

按 `requirements-analysis.md` 得到：目标、验收标准、约束、影响模块、兼容性要求、未知点。

硬性要求：

- 验收标准必须可判定真假（"搜索 300ms 内返回"优于"搜索体验更好"）。
- 用户一句话**不要**被扩写成大型 PRD。只写到能指导实现与验收的粒度。
- 未知点如果能从仓库里查到，就去查，别写成问题丢回给用户。

## Plan

产出 `02-plan.md`：实施步骤、预期改动文件、测试策略、review 策略、验收标准。

计划的质量标准：**用户不需要额外确认就能开工**。计划里如果出现"要不要先问用户"，说明需求分析没做完。

## Develop

按 `development.md` 执行。实现阶段不改验收标准；如果发现原计划错了，更新 `02-plan.md` 并说明原因，而不是默默改方向。

## Functional test

按 `functional-testing.md` 执行：先跑仓库已有的针对性测试，再补新测试，再做集成与关键手工验证。

失败时进入修复循环，不要第一次失败就收工。

## Review

- Code review：始终执行，见 `code-review.md`。
- UI review：仅 UI 任务（`ui-feature`、`ui-redesign`、视觉回归、前端交互改动），见 `ui-review.md`。
- 环境支持 subagent 时，review 必须由独立 agent 执行；review prompt 用挑战式措辞。

## Fix

修复循环：

```text
Failure
   ↓
Analyze     —— 根因是什么，为什么之前没发现
   ↓
Fix         —— 改源码，不改测试来迁就实现
   ↓
Re-run      —— 重跑针对性验证
   ↓
Regression  —— 按风险选回归面
```

修完把 review 发现与对应修复记进 `07-fixes.md`（问题 / 修复 / 文件 / 验证）。

停止条件：`P0 = 0`、合理 `P1 = 0`、测试通过、验收标准满足。P2 记录但不驱动继续打磨。

## Regression

按 `regression.md` 选覆盖面：bug fix 看受影响的流程与相邻行为；共享组件看主要消费者；API 变更看调用方兼容；UI 壳层变更看主要路由与响应式断点。

## Final acceptance

按 `final-acceptance.md` 对照原始请求逐条判定，给出 `PASS` / `PASS_WITH_NOTES` / `BLOCKED`，写进 `09-final-report.md`。

## 大型任务：milestone

明显大型的任务（跨模块、跨页面、迁移类）先切 milestone：

```text
Phase 1 analysis
Phase 2 foundation
Phase 3 implementation
Phase 4 validation
Phase 5 review
```

每个 milestone 完成后在 `02-plan.md` 或 `09-final-report.md` 记录状态（done / blocked / notes）。**不要每一步都回头问用户是否继续**，除非遇到需要改目标或需要外部决策的真实分叉。

## 大型 UI 任务：golden sample

当范围是整站重做、设计系统迁移、多页面统一时：

1. 先选一个最有代表性的页面/组件做 golden sample。
2. golden sample 通过独立 UI review 后，再扩散到其余页面。
3. 目的：避免全仓改完才发现设计方向错误。

## Scope Change（用户中途改需求）

1. 在对应日志文件追加 `Scope Change` 小节：新的要求、来自谁、什么时候。
2. 更新 `02-plan.md` 剩余步骤。
3. 明确说明被放弃的旧目标，不要静默继续执行旧目标。
4. 已经完成的旧工作保留，不做无意义回滚。

## 中断与恢复

任务被中断后，恢复时先读 `.ai-runs/<run>/` 里的最新记录，而不是从记忆重建；`09-final-report.md` 未写出结论前，任务都算未完成。
