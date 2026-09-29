# Final Acceptance

验收不是"测试变绿"，而是"用户要的这件事真的做完了"。

## 验收清单

逐条对照，缺一条就不能给 `PASS`：

1. **Requested behavior completed**：原始请求里的每一条验收标准都成立，而不是只完成了主要那条。
2. **Review blockers resolved**：code review / UI review 的 P0 已清零，合理 P1 已处理或明确记为遗留。
3. **No unexpected regressions**：无非预期回归；已知的无关失败标注为 pre-existing。
4. **Tests actually run**：跑过与改动直接相关的验证，并留下真实命令与结果；没有"打算验证"。
5. **git diff reasonable**：改动范围与请求匹配，没有无关文件、没有调试残留、没有凭据。
6. **Remaining issues documented**：未解决项、已知限制、无法验证项都写进报告。
7. **No forced commit**：没有未经授权的 commit / push。

## 三档结论

只允许这三种，不允许"差不多好了"、"看起来可以"、"大部分完成"：

- `PASS`：验收清单全部成立，无遗留阻断项。
- `PASS_WITH_NOTES`：请求的功能可用，但存在已记录的遗留项、已知限制或未覆盖的验证面。
- `BLOCKED`：真实阻塞，任务无法在当前条件下完成。

## BLOCKED 的严格定义

只有下列情况可以给 `BLOCKED`：

- 缺少凭据或密钥。
- 必需的外部系统 / 服务不可用。
- 必需依赖无法获取或无法构建。
- 不可恢复的环境失败。

以下情况**不是** `BLOCKED`：

- 任务复杂。
- 有多种实现方案需要选。
- review 发现了 P0/P1（那是修复循环的事）。
- 测试难写。
- 不确定用户是否满意（按验收标准判定即可）。

`BLOCKED` 必须在报告里写清：阻塞点、已尝试的手段、需要什么才能继续。

## 记录位置

写进 `09-final-report.md`：总结、完成项、测试、review 结论、遗留问题、`git status`、验收结论。
