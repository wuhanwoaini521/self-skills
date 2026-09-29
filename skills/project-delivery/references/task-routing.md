# Task Routing

六类任务、判定信号、阶段集与门禁。

## 判定优先级

一个请求可能同时命中多类，按这个顺序取第一类：

1. 目标是"恢复正确行为" → `bug-fix`
2. 产物主要落在视觉 / 交互层，且是在已有页面里加东西 → `ui-feature`
3. 产物主要落在视觉 / 交互层，且是重做既有界面 → `ui-redesign`
4. 新增此前不存在的能力 → `new-feature`
5. 外部行为不变、只改内部结构 → `refactor`
6. 依赖 / 配置 / 工具链 / CI → `maintenance`

同时命中多类时选风险最高的一类：改后端 bug 但顺手重做了页面 → `ui-feature`（因为它必须过 UI review）。

## bug-fix

典型输入："修一下这个报错"、"这个方法有问题"、"为什么这里失败"、"修复分页 bug"。

阶段：

```text
Analyze
  ↓
Reproduce / Identify
  ↓
Fix
  ↓
Targeted Test
  ↓
Regression
  ↓
Code Review
  ↓
Final Validation
```

- **必须先复现或定位**，再改代码。无法复现时，至少给出可验证的根因证据（堆栈、日志、最小复现路径）。
- 修的是根因，不是症状；禁止通过吞异常、加特判、扩大 catch 范围来"消除报错"。
- 修复后必须有针对性测试锁住这个 bug；能顺手复现成自动化用例就写进去。
- 门禁：functional test + code review + regression + acceptance。**不启动 UI review**，除非修复本身改动了用户可见界面。

## new-feature

典型输入："增加搜索功能"、"增加导出功能"、"增加新的模块"。

阶段：

```text
Requirements
  ↓
Existing Architecture Review
  ↓
Plan
  ↓
Implementation
  ↓
Functional Test
  ↓
Code Review
  ↓
Regression
  ↓
Final Acceptance
```

- 先读现有架构，遵守既有分层、命名与接口风格；能复用就复用。
- 功能验收标准要在计划里写成可判定条目。
- 门禁：functional test + code review + regression + acceptance。
- 功能若包含新界面或新交互，追加 UI review + 响应式验证。

## ui-feature

典型输入："增加筛选弹窗"、"增加新的卡片"、"增加新的交互"。

阶段：

```text
Requirements
  ↓
UI Context
  ↓
Design Guidance
  ↓
Implementation
  ↓
Functional Test
  ↓
UI Review
  ↓
Fix
  ↓
Regression
  ↓
Final Review
```

- UI Context：先看周边页面与既有设计语言（间距、字体、色彩、组件库），不要引入第二套风格。
- Design Guidance：若环境存在 UI 设计 skill（例如 `ui-ux-pro-max`），主动载入；不存在就用内置判断并在报告中记录。
- 门禁：functional test + **UI review** + code review + regression + final review。

## ui-redesign

典型输入："重新设计这个页面"、"这个页面太丑了"、"优化整个 UI"。

阶段：

```text
UI Audit
  ↓
Load design Skill if available
  ↓
Design System / Design Direction
  ↓
Golden Sample if scope is large
  ↓
Implementation
  ↓
Functional Test
  ↓
Independent UI Review
  ↓
Fix
  ↓
Review Again
  ↓
Code Review
  ↓
Responsive Validation
  ↓
Regression
  ↓
Final UI Review
```

- UI Audit 要落到具体观察：层级、间距、排版、对比度、响应式断点、溢出、可访问性。
- 设计方向先定下来（色彩、字体、间距体系、组件规则），再写代码。
- 范围大时先做 golden sample，review 通过再扩散。
- **必须有 review again**：一轮 review 报告写完不等于任务完成，P0/P1 修完要重新看。
- 门禁：functional test + **UI review（至少两轮：初次 + 修复后）** + 响应式验证 + code review + regression + final UI review。

## refactor

典型输入："重构这个模块"、"整理这个架构"、"优化这段代码结构"。

阶段：

```text
Understand Current Behavior
  ↓
Identify Refactor Goal
  ↓
Establish Safety Tests
  ↓
Refactor
  ↓
Regression
  ↓
Code Review
  ↓
Final Validation
```

- **行为不变是硬约束**。用户没说改行为，就不能改行为；发现了值得改的行为问题，写成建议，不擅自改。
- 重构前先建立安全网：现有测试能覆盖就复用；覆盖不到就先补 characterization 测试。
- 门禁：safety tests + regression + code review + acceptance。

## maintenance

典型输入："升级依赖"、"整理配置"、"修改 CI"、"修 lint"、"更新工具链"。

阶段：

```text
Inspect
  ↓
Plan
  ↓
Change
  ↓
Validation
  ↓
Compatibility Check
  ↓
Review
```

- Inspect：先读当前版本、锁文件、构建配置与使用点，再决定升到哪个版本。
- Compatibility Check 是必做项：破坏性变更、API 迁移、废弃选项、运行时要求。
- 门禁：仓库既有测试 + lint/build + 兼容性核对 + code review。

## 不在 v0.1 范围

`architecture`、`migration`、`performance`、`release`、`security` 暂不作为独立类型。遇到时按最接近的既有类型执行（例如整体迁移按 `refactor` + 显式兼容性检查），并在 `09-final-report.md` 里记一笔，等 v0.2 再正式建模。
