# 同步指南

把 `self-skills` 里的 skill 部署到各个 Agent 的全局 skills 目录。

## 唯一事实源

GitHub 仓库里的 `self-skills/skills/` 是唯一事实源。Agent 的全局 skills 目录只是**部署目标**，不是编辑位置。

正确流程：

```
GitHub self-skills → 本地 clone → skills/* → 同步工具 → Agent 全局 skills 目录
```

> 警告：绝不要在某个 Agent 的全局 skills 目录里直接编辑 skill。那些改动不会被 GitHub 仓库记录，下次同步就会被覆盖回去。修改一律回到 `self-skills/skills/` 里做，然后重新同步。

## Targets

同步工具认识四个目标：

| 名称 | 对应 Agent | 候选目录 | 状态 |
| --- | --- | --- | --- |
| `codex` | Codex CLI | `~/.codex/skills` | 已验证 |
| `claude` | Claude Code | `~/.claude/skills` | 已验证 |
| `opencode` | OpenCode | `~/.config/opencode/skills`、`~/.config/opencode/skill` | **未验证（猜测）** |
| `pi` | Pi | `~/.pi/skills` | **未验证（猜测）** |

### Codex CLI（`codex`）

- 目录：`~/.codex/skills`
- 状态：已验证，该目录在本机确认存在。

```bash
uv run python tools/sync_skills.py --target codex
```

### Claude Code（`claude`）

- 目录：`~/.claude/skills`
- 状态：已验证，该目录在本机确认存在。

```bash
uv run python tools/sync_skills.py --target claude
```

### OpenCode（`opencode`）

- 候选目录：`~/.config/opencode/skills`、`~/.config/opencode/skill`
- 状态：**未验证**。这两个路径是猜测，不是从 OpenCode 官方确认的事实。

使用前必须显式指定路径，例如：

```bash
uv run python tools/sync_skills.py --target opencode --target-path ~/.config/opencode/skills
```

或者写进 `~/.config/self-skills/sync.json`（见下节）。在显式指定之前，同步工具只会报告 `unverified` 并给出提示，不会自己创建目录。

### Pi（`pi`）

- 候选目录：`~/.pi/skills`
- 状态：**未验证**。这是猜测路径。

使用前必须显式指定：

```bash
uv run python tools/sync_skills.py --target pi --target-path ~/.pi/skills
```

或者写进 `~/.config/self-skills/sync.json`。同样地，未显式指定前只会得到 `unverified` 提示，不会自动建目录。

## 配置目标目录

有两条路给一个目标指定路径：一次性覆盖，或者持久化配置。

### 一次性覆盖：`--target-path`

```bash
uv run python tools/sync_skills.py --target pi --target-path ~/.pi/skills
```

`--target-path` 只能和**恰好一个** `--target` 一起用，否则报错：

```text
--target-path requires exactly one --target
```

只有在你显式给出了路径（`--target-path` 或 `~/.config/self-skills/sync.json`）时，工具才会创建目标目录。自动探测到的候选目录本来就已存在。

### 持久化配置：`~/.config/self-skills/sync.json`

这是一个 JSON 对象，key 是目标名称，value 是绝对路径字符串：

```json
{
  "opencode": "D:/tools/opencode-skills",
  "pi": "C:/Users/me/.pi/skills"
}
```

未知的目标名称、空值、非字符串值都会直接报错，并给出可读的说明。

### 解析优先级

工具按下面的顺序决定用哪个目录：

1. `--target-path` 显式覆盖 → 状态 `explicit`
2. `~/.config/self-skills/sync.json` 里配置的路径 → 状态 `explicit`；若目录还不存在则状态 `missing`
3. 已检测到的候选目录存在 → 状态 `ready`
4. 都没有：
   - 已验证目标 → 状态 `missing`，并提示检测到的平台和期望路径
   - 未验证目标 → 状态 `unverified`，并提示你用 `--target-path` 或配置文件指定路径

工具**绝不会**静默创建一个猜测出来的目录。

## 同步模式

`--mode copy|symlink`，默认 `copy`。

| 模式 | 说明 |
| --- | --- |
| `copy`（默认） | 把 skill 目录复制一份到目标位置。自包含、可移植、不依赖开发者模式。 |
| `symlink` | 在目标位置创建指向仓库 `skills/` 的符号链接。改仓库即刻生效，但目标目录和仓库必须始终在一起。 |

```bash
uv run python tools/sync_skills.py --target codex --mode copy
uv run python tools/sync_skills.py --target codex --mode symlink
```

默认是 `copy`，因为符号链接在 Windows 上需要管理员权限或开启开发者模式，并且换一台机器就断掉了。

## 安全模型

- **只写托管集合。** 同步只创建/更新注册表里列出的那些 skill 目录，绝不对目标目录执行整体删除。
- **`.sync-state.json`。** 仓库根目录的这个文件记录每个目标的目标路径、模式，以及每个已部署 skill 的版本和内容指纹。
- **不动未托管的 skill。** 目标目录里已经存在的第三方、公司内部、手写的 skill 不会被读取、修改或删除。
- **`--prune` 只能删自己部署过的东西。** 有了 `.sync-state.json`，`--prune` 只会移除之前由 self-skills 部署、现在已从注册表里消失的 skill。
- **排除项。** `__pycache__`、`.git`、`.pytest_cache`、`.mypy_cache`、`.ruff_cache`、`dist` 目录，以及 `.pyc`/`.pyo` 文件，都不会被复制进目标目录。
- **幂等。** 比较基于内容指纹，内容没变时重复执行同步，每个 skill 都是 `SKIP`。

## 命令

同步工具：`tools/sync_skills.py`。

| 参数 | 说明 |
| --- | --- |
| `--target NAME` | 同步指定目标，可重复 |
| `--all` | 同步所有可检测的目标 |
| `--skill NAME` | 只同步指定 skill，可重复 |
| `--target-path PATH` | 显式指定 skills 目录，只允许配合恰好一个 `--target` |
| `--mode copy\|symlink` | 同步模式，默认 `copy` |
| `--dry-run` | 只打印计划，不写入任何文件 |
| `--prune` | 移除已从注册表离开的、之前同步过的 skill |
| `--include-archived` | 同时部署 `archived` 里的 skill |

用法示例：

```bash
# 先干跑，看看会做什么
uv run python tools/sync_skills.py --target codex --dry-run

# 真正同步
uv run python tools/sync_skills.py --target codex

# 同步到所有可检测目标
uv run python tools/sync_skills.py --all

# 只同步两个 skill
uv run python tools/sync_skills.py --target claude --skill my-skill --skill github-trending-report

# 显式指定目标目录
uv run python tools/sync_skills.py --target opencode --target-path ~/.config/opencode/skills

# 用符号链接
uv run python tools/sync_skills.py --target codex --mode symlink

# 清理已经从注册表移除的旧 skill
uv run python tools/sync_skills.py --target codex --prune

# 连归档 skill 一起部署
uv run python tools/sync_skills.py --target codex --include-archived
```

`--target` 和 `--all` 互斥。两者都不给时，工具以退出码 2 报错并列出可用目标。未知的目标名会被 argparse 当作非法取值直接拒绝。

### 动作名称

每个 skill 会报告四种动作之一：

- `ADD` —— 目标目录里还没有
- `UPDATE` —— 已存在且内容有变化
- `SKIP` —— 已存在且内容一致
- `PRUNE` —— 之前部署过，现在已从注册表移除（需要 `--prune`）

输出形如：

```text
Codex CLI (codex) → C:\Users\me\.codex\skills
  ADD     my-skill
  UPDATE  github-trending-report
  SKIP    crawl-docs-to-markdown
```

## 跨平台

工具面向 macOS、Linux 和 Windows：所有路径都用 `pathlib` 和 `Path.home()` 构造，没有硬编码的 `/home/user` 或 `C:\Users\...`。CI 在 ubuntu、windows、macos 上都跑测试，因为同步逻辑大量涉及路径处理。

## 相关命令

```bash
# 1. 同步前先校验 skill 结构
uv run python tools/validate_skills.py

# 2. 先看计划
uv run python tools/sync_skills.py --target codex --dry-run

# 3. 执行同步
uv run python tools/sync_skills.py --target codex

# 4. 验证结果
uv run python tools/doctor.py
```

## Troubleshooting

### 目标显示 not configured

`--all` 会把所有可检测目标跑一遍；没有配置的（没有 `--target-path`、配置文件里也没有、候选目录也不存在）只会打印 `not configured`，**不会**让整次运行失败。修法：用 `--target-path` 指定一次，或者写进 `~/.config/self-skills/sync.json`。

### 目录不存在

状态为 `missing` 时，说明已验证的目标检测到平台但期望路径不在。想让工具创建目录，必须由你显式给出路径（`--target-path` 或配置文件）。工具不会自己猜一个位置然后建出来。

### OpenCode / Pi 报 unverified

这是预期行为：`~/.config/opencode/skills`、`~/.config/opencode/skill`、`~/.pi/skills` 都是猜测路径，没有被验证过。请用 `--target-path` 指向你实际使用的那个目录，确认它能用之后写进 `~/.config/self-skills/sync.json`，以后就不用每次带参数了。

### 想确认同步真的生效了

```bash
uv run python tools/doctor.py
```

它会检查注册表结构、目标目录状态和同步状态，告诉你哪些目标就绪、哪些缺失或未验证。也可以重跑一次同步：如果输出全是 `SKIP`，说明指纹一致、同步是幂等的，目标内容就是最新的。
