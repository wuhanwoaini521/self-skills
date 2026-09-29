# Agent 支持矩阵

本仓库是 source of truth，下表列出各 Agent 的**部署目标**（同步落点）。目标定义集中在 `tools/sync_targets.py` 的 `TARGETS` 中，`sync_skills.py` 与 `doctor.py` 都从这里读取。

> **警告：未验证（NOT VERIFIED）的目标路径只是猜测。** 下表中标记为 NOT VERIFIED 的路径**未在本机实测确认**，可能随 Agent 版本或操作系统而变化。请勿把猜测路径当作事实对外陈述；在你自己的机器上确认之前，同步工具不会向这些目标写入任何内容。

## 支持矩阵

| Agent | target key | 支持状态 | 默认路径 | 已验证平台 | 备注 |
| --- | --- | --- | --- | --- | --- |
| Codex CLI | `codex` | 支持 | `~/.codex/skills` | 本机已确认（verified=True） | 默认 target；`new_skill.py` 默认 `targets: codex` |
| Claude Code | `claude` | 支持 | `~/.claude/skills` | 本机已确认（verified=True） | 可与 `codex` 同时同步 |
| OpenCode | `opencode` | **未验证（NOT VERIFIED）** | 猜测：`~/.config/opencode/skills` 或 `~/.config/opencode/skill` | 无（未实测） | 必须显式配置路径后才会写入 |
| Pi | `pi` | **未验证（NOT VERIFIED）** | 猜测：`~/.pi/skills` | 无（未实测） | 必须显式配置路径后才会写入 |

规则：

- `verified=True` 的目标可以直接同步。
- `verified=False` 的目标，只有在用户提供 `--target-path` 或配置了 `~/.config/self-skills/sync.json` 时才会被写入；同步工具不会擅自猜测并创建目录。
- 新增 Agent 时，只需在 `tools/sync_targets.py` 的 `TARGETS` 里追加一条 `SyncTarget`，同步与诊断工具会自动识别。

## 为未验证的 Agent 登记真实路径

### 方式一：`--target-path` 一次性指定

```bash
uv run python tools/sync_skills.py --target opencode --target-path D:/tools/opencode-skills
```

注意：

- `--target-path` 只在指定单个 `--target` 时有效。
- 只对本次命令生效，下次同步需要重新提供。
- 建议先加 `--dry-run` 确认写入计划。

### 方式二：写入持久化配置（推荐）

配置文件路径：`~/.config/self-skills/sync.json`

内容是一个 JSON 对象，把 target key 映射到绝对路径：

```json
{
  "opencode": "D:/tools/opencode-skills",
  "pi": "D:/tools/pi-skills"
}
```

配置后，`--target opencode` 无需再带 `--target-path`：

```bash
uv run python tools/sync_skills.py --target opencode --dry-run
uv run python tools/sync_skills.py --target opencode
```

- 只写需要覆盖的 target；未出现的 target 继续使用 `TARGETS` 中的默认定义。
- 路径必须是绝对路径。
- 不要把个人路径提交进仓库，该文件位于用户目录，不属于仓库内容。

## 确认后把目标标记为已验证

在某台机器上确认目录约定真实存在、且同步后 Agent 确实能加载 skill 之后：

1. 打开 `tools/sync_targets.py`，找到 `TARGETS` 中对应的 `SyncTarget`。
2. 把 `verified=False` 改为 `verified=True`。
3. 确认该条目上的路径与实际生效路径一致。
4. 运行诊断确认工具侧识别正常：

   ```bash
   uv run python tools/doctor.py
   ```

5. 同步更新本文件（见下节）。

在改为 `verified=True` 之前，请如实保留未验证状态，不要仅因为"看起来应该在那儿"就标记为已验证。

## 维护约定

- **本表是 target 支持情况发生变化时的唯一更新位置。** 任何一项变更——新增 Agent、路径调整、验证状态翻转——都必须同步修改 `docs/compatibility.md` 中的矩阵。
- 修改 `tools/sync_targets.py` 的 `TARGETS` 时，target key、默认路径与 `verified` 状态要同本文档保持一致。
- 表述要求：
  - 未在本机实测确认的路径必须明确标注为"猜测"或 NOT VERIFIED；
  - 不得把未验证路径写成确定结论；
  - 一旦在任一平台确认，更新"已验证平台"列而不是笼统地写"已支持"。
