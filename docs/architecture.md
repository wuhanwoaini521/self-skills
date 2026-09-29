# 架构

本文说明 `self-skills` 仓库的整体结构、数据流、扩展点与依赖策略。

## 1. 唯一事实源原则

`self-skills` 仓库是个人 Skill 的唯一事实源（source of truth）。

- GitHub 上的 `self-skills` 仓库是权威副本。
- 仓库中的 `skills/` 是 Skill 内容的权威副本。
- Codex / Claude Code / OpenCode / Pi 的全局 skills 目录**只是部署目标（deploy target）**，永远不是事实源。

数据流是单向的：

```text
  GitHub 仓库
      |
      |  git clone / git pull
      v
  本地 clone
      |
      |  直接编辑
      v
  self-skills/skills/*
      |
      |  tools/sync_skills.py
      v
  各 Agent 的全局 skills 目录
  (Codex / Claude Code / OpenCode / Pi)
```

**铁律：绝对不要在某个 Agent 的全局 skills 目录里编辑 Skill。**
那里的内容随时会被下一次同步覆盖。正确做法是在仓库的 `skills/<name>/` 中修改，然后重新同步。

## 2. 分层结构

```text
  registry/skills.yaml        skills/
  （机器可读事实源）           （真正的 Skill 内容）
          \                     /
           \                   /
            v                 v
            +------- 检查 ----+
                    |
                    v
        tools/validate_skills.py   校验层
                    |
                    v
              tests/ (pytest)      测试层
                    |
                    v
   tools/sync_skills.py + tools/sync_targets.py   同步层
                    |
                    v
     Codex / Claude Code / OpenCode / Pi 全局目录
```

- `registry/skills.yaml` 与 `skills/` 一起构成事实源：前者记录"有哪些 Skill、什么版本、什么状态、部署到哪些 Agent"，后者存放"Skill 实际内容"。
- 校验层保证这两者不漂移（名字一致、路径存在、SKILL.md 合法、每个 Skill 目录都已登记）。
- 测试层覆盖工具逻辑与 Skill 自带的脚本。
- 同步层把登记过的 Skill 复制到各个 Agent 的全局目录。

## 3. 目录结构与职责

```text
self-skills/
├── skills/                     Skill 正本
├── templates/skill-starter/     新 Skill 脚手架（SKILL.md、agents/openai.yaml）
├── registry/skills.yaml         机器可读事实源
├── tools/                      全部脚本工具
├── docs/                       文档
├── tests/                      pytest 测试
├── archive/                    归档内容（默认不校验、不同步）
├── .github/workflows/          CI（校验 + 索引漂移检查 + 三平台 pytest）
├── conftest.py                 pytest 根配置：把仓库根加入 sys.path，提供 load_skill_module()
├── pyproject.toml              项目与依赖声明
├── skills-index.md             由 registry 生成的索引（只读产物）
└── README.md                   仓库入口
```

各顶层目录的职责：

| 目录 / 文件 | 职责 |
| --- | --- |
| `skills/` | Skill 正本。每个子目录是一个 Skill，含 `SKILL.md`、`agents/openai.yaml` 及可选的 `references/`、`scripts/`、`assets/`。 |
| `templates/skill-starter/` | 新建 Skill 时复制的脚手架模板。 |
| `registry/` | 保存 `skills.yaml`，即"有哪些 Skill、版本、状态、目标 Agent"的机器可读登记。 |
| `tools/` | 所有命令行工具与共享库，见下节。 |
| `docs/` | 人读文档。 |
| `tests/` | pytest 测试，用 `tmp_path` 隔离数据。 |
| `archive/` | 归档产物与历史内容；默认被排除在活动校验与同步之外。 |
| `.github/workflows/` | CI：`ci.yml` 在 ubuntu 上跑校验、索引漂移检查与 `doctor.py`，并在 ubuntu / windows / macos 三个平台跑 pytest。 |
| `conftest.py` | pytest 根配置：把仓库根加入 `sys.path`，并提供 `load_skill_module()`，让测试直接 import `skills/*/scripts/*.py` 中的正本，而不是 `tools/` 下的副本。 |
| `pyproject.toml` | 项目元数据与依赖（PyYAML、pytest）。 |
| `skills-index.md` | 生成产物，勿手改。 |
| `README.md` | 仓库入口说明。 |

`archive/generated/` 与 `dist/` 是被 gitignore 的构建输出。

## 4. tools/ 各工具职责

| 工具 | 一句话职责 |
| --- | --- |
| `tools/registry.py` | Skill 登记的数据层：定义 `SkillEntry` 字段与 `parse_registry` / `load_registry` 解析校验，以及 `discover_skill_dirs` 扫描磁盘上的 Skill 目录。 |
| `tools/console.py` | 共享输出层：集中定义 ✓ ✗ ○ ! 符号与颜色处理，负责 Windows 控制台 UTF-8 重配置。 |
| `tools/sync_targets.py` | 同步目标定义层：定义 `SyncTarget` 数据结构与全局 `TARGETS` 表，并提供 `resolve_target`、`load_config`。 |
| `tools/new_skill.py` | 从 `templates/skill-starter/` 创建新 Skill 目录，并自动在 `registry/skills.yaml` 中追加登记条目。 |
| `tools/validate_skills.py` | 校验层：检查 Skill 目录命名、`SKILL.md` 与 frontmatter、`agents/openai.yaml`、内部引用路径，以及 registry 的一致性。 |
| `tools/sync_skills.py` | 同步层：按 registry 选 Skill，按 `TARGETS` 解析目标目录，以 `copy`（默认）或 `symlink` 模式同步，并支持剪枝已退出 registry 的旧 Skill。 |
| `tools/list_skills.py` | 展示层：列出已登记的 Skill（人类可读或 `--json`），并可生成/校验 `skills-index.md`。 |
| `tools/doctor.py` | 环境体检：检查工具自身可运行性、目标目录可探测性、索引是否过期等。 |

## 5. 扩展点

### 5.1 新增一个 Agent

只需在 `tools/sync_targets.py` 的 `TARGETS` 中追加一个 `SyncTarget`：

```python
"myagent": SyncTarget(
    name="myagent",
    label="My Agent",
    candidates=(".myagent/skills",),
    verified=False,
    notes="目录约定未在本机确认；请用 --target-path 或配置文件指定。",
),
```

此后 `sync_skills.py` 与 `doctor.py` 会自动识别该目标，`validate_skills.py` 的 registry 校验也会接受 registry 中出现的 `myagent` 这个 `targets` 值。不需要改动其他文件。

`candidates` 列出候选目录名，`verified=True` 表示该目录约定已在本机确认；`verified=False` 的目标应通过 `--target-path` 或配置文件显式指定路径。

### 5.2 新增一个工具

在 `tools/` 下新建脚本。需要遵守的约定：

- 复用 `tools/console.py` 的符号与颜色，不要自己 print 特殊符号。
- 复用 `tools/registry.py` 读取 registry，不要重复解析 `skills.yaml`。
- 需要识别 Agent 目标时复用 `tools/sync_targets.py` 的 `SyncTarget` / `resolve_target` / `load_config`，不要自己维护目标路径表。
- 在 `tests/` 下补上对应测试，用 `conftest.py` 提供的 `load_skill_module()`。

## 6. 生成产物规则

`skills-index.md` 是由 `skills.yaml` 生成的人类可读视图：

```bash
uv run python tools/list_skills.py --write-index
```

**禁止手工编辑 `skills-index.md`。** 任何手改都会在下次生成时被覆盖，或被 `--check-index` 判定为过期。需要修改索引内容时，改 `registry/skills.yaml` 再重新生成。

## 7. 依赖策略

- 仅使用 Python 标准库 + PyYAML + pytest。
- 不引入 CLI 框架（不用 Typer / Rich / Click），命令行参数用 `argparse`。
- 输出符号与颜色集中在 `tools/console.py`；非 TTY 或设置了 `NO_COLOR` 时自动关闭颜色，并对 Windows 控制台做 UTF-8 重配置。
- 运行环境建议使用 `uv`（命令形式为 `uv run python tools/<name>.py`）。
