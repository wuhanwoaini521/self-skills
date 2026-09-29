# Skill 生命周期

每个 Skill 在 `registry/skills.yaml` 中都有一个 `status` 字段，它同时决定：这个 Skill 意味着什么、是否算"已可用"、以及默认是否被同步到各 Agent 的全局目录。

## 1. 状态机

```text
                Create
                  |
                  v
             [ experimental ]  刚创建，不保证稳定
                  |
                  v
                [ beta ]      已可使用，但仍在迭代
                  |
                  v
               [ stable ]     默认推荐
                  |
                  v
             [ deprecated ]   仍存在，但不再推荐新使用
                  |
                  v
              [ archived ]    停止维护（默认不同步）
```

- 状态是**顺序推进**的：Create → experimental → beta → stable → deprecated → archived。
- 状态可以停留在中间环节（例如长期停在 `beta`），也可以因为问题暴露而回退（例如从 `beta` 回到 `experimental`）。
- `deprecated` 与 `archived` 仍然**同步**（`archived` 需要显式 `--include-archived`），区别在于是否还在维护、是否推荐新使用。

## 2. 状态总表

| 状态 | 含义 | 默认同步 | 进入条件 |
| --- | --- | --- | --- |
| `experimental` | 刚创建，不保证稳定 | 是 | Skill 目录、`SKILL.md`、frontmatter（`name` / `description`）、`agents/openai.yaml` 齐备；已在 `registry/skills.yaml` 登记并通过 `tools/validate_skills.py` 校验。此时只需"能跑通"，不要求好用。 |
| `beta` | 已可使用，但仍在迭代 | 是 | 实际使用过，确认主流程可用；已知问题被记录或已修复到不阻塞；仍可能有破坏性调整。 |
| `stable` | 默认推荐 | 是 | 主流程稳定；`SKILL.md` 的使用说明、引用文件、脚本已对齐实际行为；`agents/openai.yaml` 的 `interface.default_prompt` 可直接使用；不再预期频繁破坏性变更。 |
| `deprecated` | 仍存在，但不再推荐新使用 | 是 | 已确定有更好的替代方案（或上游已废弃），并在 `notes` 中说明替代物与迁移方式。目录与内容继续保留，保证既有使用者不被突然打断。 |
| `archived` | 停止维护 | 否（需 `--include-archived`） | 已确认不再维护，内容迁往 `archive/`；默认不再作为活动 Skill 被校验、同步或列出。 |

## 3. 同步行为

`tools/sync_skills.py` 默认部署以下状态的 Skill：

```text
experimental, beta, stable, deprecated
```

`archived` 默认**不**部署。只有显式加上 `--include-archived` 才会参与：

```bash
uv run python tools/sync_skills.py --all --include-archived
```

同样的规则也适用于 `tools/list_skills.py`：默认列表与 `--status` 过滤都排除 `archived`，需要加 `--include-archived` 才能看到（`--status archived` 的过滤也受该开关约束）。

## 4. 变更状态的操作步骤

1. 编辑 `registry/skills.yaml`，修改对应条目的 `status`。
2. 重新校验：

   ```bash
   uv run python tools/validate_skills.py
   ```

3. 重新生成索引（`skills-index.md` 是生成产物，不能手改）：

   ```bash
   uv run python tools/list_skills.py --write-index
   ```

4. 如需让本地 Agent 目录跟上最新状态，再执行一次同步：

   ```bash
   uv run python tools/sync_skills.py --all
   ```

进入 `deprecated` 时，务必在同一条目中填写 `notes`，写清替代方案；进入 `archived` 时，把 Skill 的历史内容归入 `archive/`。

## 5. `archived` 与 `archive/` 目录

- 归档后，该 Skill **不再作为活动 Skill 被校验**：`tools/validate_skills.py` 不会把它的内容当作活动 Skill 要求。
- 归档后**默认不参与同步**，只有 `--include-archived` 才会被复制到 Agent 全局目录。
- 归档后**不出现在默认的 Skill 列表**里（`tools/list_skills.py` 与生成的 `skills-index.md` 都默认排除它）。
- 归档内容的历史产物归入 `archive/`；该目录默认被排除在活动校验与同步之外。`archive/generated/` 与 `dist/` 是被 gitignore 的构建输出。
