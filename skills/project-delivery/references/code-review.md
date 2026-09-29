# Code Review

每次任务都要做，且必须**独立于实现过程**。

## 独立性要求

- 环境支持 subagent 时，review 由独立 agent 执行，实现者不看结论先自评。
- prompt 用挑战式措辞，逼迫 reviewer 找问题：

```text
Find concrete reasons this implementation should not be accepted yet.
```

- 不接受"看起来没问题"、"格式良好"、"已经加了注释"这类结论。
- 没有 subagent 时，串行执行，但 review 阶段要显式切换视角：重新读 diff，而不是回忆刚才写了什么。

## 检查维度

- **Correctness**：逻辑是否正确，边界与异常路径是否成立。
- **Behavior changes**：实际行为有没有超出请求范围。
- **Edge cases**：空值、边界值、并发、重复调用、失败重试。
- **Error handling**：错误是否被正确传播；有没有吞异常、静默失败、宽泛 catch。
- **Duplication**：是否复制了仓库里已有的能力。
- **Complexity**：是否引入了不必要的抽象层或状态。
- **Maintainability**：半年后的人能不能读懂；命名、注释与结构是否一致。
- **Test coverage**：新增逻辑有没有对应验证，bug 有没有被锁住。
- **API compatibility**：签名、返回值、异常契约、序列化格式有没有被破坏。
- **Security-sensitive behavior**：鉴权、输入校验、注入、路径处理、密钥处理。

## Reviewer 不该做的事

- 只看格式不看逻辑。
- 要求与仓库约定无关的"更好写法"。
- 把个人风格偏好升格为阻断项。
- 在没读调用方的情况下断言兼容性安全。

## 分级与出口

- **P0**：功能错误、数据损坏、安全问题、破坏性变更。必须修。
- **P1**：真实缺陷、可维护性风险、测试缺口。应该修。
- **P2**：风格与偏好。记录，不阻断。

出口条件：`P0 = 0`，合理 `P1` 已修或在报告里说明为何保留。

## 记录位置

写进 `06-code-review.md`：正确性、可维护性、复杂度、重复、错误处理、兼容性、测试覆盖、问题清单。
