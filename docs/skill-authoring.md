# 个人 Skill 开发规范

本文件是 self-skills 仓库中 **个人 skill** 的开发规范。本仓库是 source of truth：skill 的唯一副本在 `skills/`，各 Agent 的全局目录只是同步落点。

`tools/validate_skills.py` 负责强制执行本文档中的硬性规则；未写在此处但被校验工具检查的规则同样以校验结果为准。

## 命名

- 只能使用小写 kebab-case：字母、数字、连字符，例如 `crawl-docs-to-markdown`。
- 不允许大写字母、下划线、空格。
- 长度上限 64 字符。
- 名字必须同时满足三处一致：
  1. 目录名 `skills/<name>/`；
  2. `SKILL.md` frontmatter 的 `name`；
  3. `registry/skills.yaml` 条目的 `name`。
- 名字是 skill 的对外标识，发布后不要随意重命名；需要改名时按"版本"一节的 MAJOR 规则处理。

## 目录

标准布局：

```text
skills/<skill-name>/
├── SKILL.md              # 必需
├── agents/openai.yaml    # 必需
├── references/           # 可选：被引用的文档
├── scripts/              # 可选：可执行代码
└── assets/               # 可选：静态文件
```

规则：

- `SKILL.md` 与 `agents/openai.yaml` 是必需项，缺一不可。
- **不含 `SKILL.md` 的目录不会被识别为 skill。** 例如只放了一个 `notes/` 的目录只是普通文件夹，既不会被校验发现，也不会被同步。
- 目录内不要放与 skill 无关的内容；每个 `skills/` 下的子目录都应该是一个完整可复用的 skill。
- 可选目录通过 `.gitkeep` 保留空目录，避免空目录在版本库里消失。

## SKILL.md

### frontmatter（必需）

文件开头是 `---` 包裹的 YAML frontmatter，必须包含 `name` 与 `description` 两个字段：

```markdown
---
name: my-skill
description: 一句话说明这个 skill 解决什么问题、什么时候该用它。
---
```

- `name`：小写 kebab-case，必须等于目录名。
- `description`：一行说明，模型据此判断是否调用该 skill，写清楚"做什么 + 何时用"。

### 正文结构（推荐）

正文分节不被校验强制，但起步模板 `templates/skill-starter/` 使用以下结构，保持一致便于阅读：

```markdown
# <Title>

## Overview

## Workflow

## Rules

## References
```

- `Overview`：目标与适用场景。
- `Workflow`：可执行的步骤流程。
- `Rules`：硬性约束、禁止事项。
- `References`：指向 `references/` 中文档的链接。

### 引用路径规则（强制）

SKILL.md 中出现的 `references/...`、`scripts/...`、`assets/...` 这类 skill 子目录路径（以文件扩展名结尾）**必须在磁盘上真实存在**，否则校验失败并报 `missing referenced file: <path>`。

- 写了链接就必须创建文件，或删掉链接。
- 不要引用 `__pycache__/`、`dist/` 下的产物。
- 引用脚本时给出可直接执行的相对命令，例如 `uv run python scripts/fetch.py --url <URL>`，不要写本机绝对路径。

## References

- `references/` 存放**按需加载**的详细文档：长参考、协议说明、字段清单、排错手册、示例数据集。
- 判断标准：正文里只需要"知道它存在、在什么时候读"的内容放 `references/`，正文里必须始终遵守的规则放 SKILL.md 正文。
- 每个 `references/*.md` 用一级标题作为文件名主题，正文开头一句话说明它解决什么问题。
- 不在 `references/` 放可执行代码，也不放与 skill 无关的通用资料。

## Scripts

- 可执行代码（Python、shell 等）一律放 `scripts/`。
- 脚本应能以相对 skill 目录的路径被调用，不要硬编码本机绝对路径。
- 需要被测试的脚本必须有确定性的行为，不依赖真实网络、真实用户目录或交互输入。
- `__pycache__/` 与 `dist/` 不会随同步分发，且已被 `.gitignore` 忽略，不要把它们当作 skill 内容引用。
- `scripts/` 中的代码是本仓库里该 skill 的**唯一实现**；不要在 `tools/` 下再放一份副本。测试通过仓库根目录 `conftest.py` 提供的 `load_skill_module(relative_path, module_name)` 按文件路径加载 `skills/` 下的这份实现。

## Assets

- 静态文件放 `assets/`：图片、模板文件、样例数据、字体等。
- 被 SKILL.md 或 `references/` 引用的 assets 路径同样受"必须存在"规则约束。
- 体积大、可重新生成的内容不要提交到 `assets/`。

## Agents 元数据

每个 skill 必须提供 `agents/openai.yaml`，用于声明 skill 在 Agent 侧如何被展示与调用。

模板形状：

```yaml
interface:
  display_name: "{{title}}"
  short_description: "{{short_description}}"
  default_prompt: "Use ${{name}}. 使用 ${{name}}。"
policy:
  allow_implicit_invocation: true
```

规则：

- 文件必须是合法 YAML，且**根节点是 mapping**；写成 list 会被拒绝（`agents/openai.yaml must be a mapping`）。
- `interface.default_prompt` 必须提及 `$<skill-name>`，否则报 `agents/openai.yaml: interface.default_prompt should mention $<name>`。
- `display_name` 是展示名，`short_description` 是一句话简介。
- `policy.allow_implicit_invocation` 决定模型是否可以不经显式点名就调用该 skill。

## 版本

版本号写在 `registry/skills.yaml` 的 `version` 字段，格式为 `MAJOR.MINOR.PATCH`。

| 变更类型 | 递增位 | 例子 |
| --- | --- | --- |
| 破坏性变更：删除或重命名了触发条件、删除了正文引用的必需文件、重写了脚本的命令行契约 | MAJOR | `1.2.0` → `2.0.0` |
| 向后兼容的能力新增：新增可选 flag、新增 `references/` 文档、正文补充新章节 | MINOR | `1.2.0` → `1.3.0` |
| 修复与措辞调整，不改变任何对外行为 | PATCH | `1.2.0` → `1.2.1` |

- 新建 skill 的默认版本是 `0.1.0`。
- 版本不写在 `SKILL.md` 里，只在 registry 中维护，避免两处不一致。

## 状态

生命周期状态同样只存在于 `registry/skills.yaml` 的 `status` 字段，取值共五个：

| status | 含义 |
| --- | --- |
| `experimental` | 试验中，接口可能随时改，不建议稳定依赖 |
| `beta` | 功能基本齐备，仍在调整 |
| `stable` | 接口稳定，可放心使用 |
| `deprecated` | 仍可用但不推荐使用，等待迁移 |
| `archived` | 不再维护，通常不再同步分发 |

- 默认状态是 `experimental`。
- 状态属于 registry 元数据，**不要写进 `SKILL.md`**。
- 合法取值之外的值会被校验拒绝。

## 测试

本仓库的测试约定：

- 使用 pytest，测试文件放在 `tests/`，命名为 `test_<feature>.py`。
- 仓库根目录的 `conftest.py` 会把仓库根加入 `sys.path`，并提供 `load_skill_module(relative_path, module_name)`。
- 需要测试 skill 自己的脚本时，用 `load_skill_module("skills/<name>/scripts/<file>.py", "<module_name>")` 加载，确保测的是 `skills/` 下的正式实现。
- 测试**绝不允许触碰真实用户目录**（`Path.home()`），一律使用 pytest 的 `tmp_path` 夹具。
- 需要指定仓库根、状态文件或路径覆盖时，调用工具函数并显式传入 `repo_root`、`state_path`、`override` 等参数，使其可在临时目录中运行。
- 测试应覆盖可观察的契约：成功路径、边界条件、真实报错信息，而不是实现细节。

## 编写流程

1. 创建骨架（先看计划，不落盘）：

   ```bash
   uv run python tools/new_skill.py my-skill --dry-run
   ```

2. 正式创建（默认 `version 0.1.0`、`status experimental`、`targets codex`，并自动追加 registry 条目）：

   ```bash
   uv run python tools/new_skill.py my-skill
   ```

   需要自定义时：

   ```bash
   uv run python tools/new_skill.py my-skill --description "一句话说明" --status beta --targets codex claude
   ```

3. 编写内容：
   - 填写 `SKILL.md` 的 `name` / `description` 与正文各节；
   - 把详细文档放进 `references/`，可执行代码放进 `scripts/`，静态文件放进 `assets/`；
   - 检查 `agents/openai.yaml` 是 mapping，且 `default_prompt` 含 `$my-skill`；
   - 确认 SKILL.md 里引用的每个 `references/...`、`scripts/...`、`assets/...` 路径都真实存在。
4. 校验：

   ```bash
   uv run python tools/validate_skills.py
   ```

   只校验单个 skill：

   ```bash
   uv run python tools/validate_skills.py my-skill
   ```

5. 跑测试：

   ```bash
   uv sync
   uv run pytest
   ```

6. 确认 registry 记录，并按需刷新索引：

   ```bash
   uv run python tools/list_skills.py
   uv run python tools/list_skills.py --status stable
   uv run python tools/list_skills.py --write-index
   ```

7. 同步到各 Agent（先看计划，再执行）：

   ```bash
   uv run python tools/sync_skills.py --target codex --dry-run
   uv run python tools/sync_skills.py --target codex
   ```

   所有目标一次同步，或只同步单个 skill：

   ```bash
   uv run python tools/sync_skills.py --all
   uv run python tools/sync_skills.py --target codex --skill my-skill
   ```

8. 需要排查环境问题时：

   ```bash
   uv run python tools/doctor.py
   ```

`tools/sync_skills.py` 会在仓库根维护 `.sync-state.json`，记录每个 skill 同步到了哪些目标、当时的版本与指纹，用于后续增量更新与 `--prune` 清理。
