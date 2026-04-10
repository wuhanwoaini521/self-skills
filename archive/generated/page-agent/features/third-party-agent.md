# 接入第三方 Agent

- Source: [https://alibaba.github.io/page-agent/docs/features/third-party-agent](https://alibaba.github.io/page-agent/docs/features/third-party-agent)
- Section: 功能特性

## Outline Mermaid

```mermaid
graph TD
  n_cca6a46780e5["接入第三方 Agent"]
  n_cca6a46780e5 --> n_21a468f98c07["集成方式"]
  n_21a468f98c07 --> n_3e37812c828b["1. Function Calling"]
  n_cca6a46780e5 --> n_f0b325012a8b["应用场景"]
  n_f0b325012a8b --> n_f4c343d951f1["🤖 智能客服系统"]
  n_f0b325012a8b --> n_2330f3f41d4d["📋 业务流程助手"]
  n_f0b325012a8b --> n_8e442418a45e["🎯 个人效率助手"]
  n_f0b325012a8b --> n_e2ef73b0743c["🔧 运维自动化"]
```

## Outline

- 集成方式
  - 1. Function Calling
- 应用场景
    - 🤖 智能客服系统
    - 📋 业务流程助手
    - 🎯 个人效率助手
    - 🔧 运维自动化

## Content

将 pageAgent 作为工具接入你的答疑助手或 Agent 系统，成为你 Agent 的眼和手。

## 集成方式

### 1. Function Calling

```javascript
// 定义工具
const pageAgentTool = {
  name: "page_agent",
  description: "执行网页操作",
  parameters: {
    type: "object",
    properties: {
      instruction: { type: "string", description: "操作指令" }
    },
    required: ["instruction"]
  },
  execute: async (params) => {
    const result = await pageAgent.execute(params.instruction)
    return { success: result.success, message: result.data }
  }
}

// 注册到你的 agent 中
```

## 应用场景

#### 🤖 智能客服系统

客服机器人帮用户直接操作系统，如"帮我提交工单"

#### 📋 业务流程助手

引导新员工完成复杂流程，如"完成客户入职"

#### 🎯 个人效率助手

跨网站帮你完成任务，如"预订会议室"

#### 🔧 运维自动化

通过自然语言操作管理后台，如"重启服务器"

## Internal Links

- [https://alibaba.github.io/page-agent/docs/features/third-party-agent](https://alibaba.github.io/page-agent/docs/features/third-party-agent)
