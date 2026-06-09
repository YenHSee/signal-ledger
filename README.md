# Stock Analyst 📈

这是一个基于 **pnpm Workspace + Turborepo** 搭建的金融量化分析辅助大盘。系统实现了计算隔离、高并发分发与类型安全。

## 📁 架构分层 (Monorepo)

- `packages/api-types`: **[核心契约]** 存放全局 TypeScript 类型定义与 JSON Schema，Python 与 Node.js 共同遵循。
- `packages/data-python`: **[数据引擎]** 由 Data Engineer 主导，负责 Alpha Vantage 真实金融 API 的 ETL 跑批、清洗与 ML 模型打分。
- `packages/backend-node`: **[实时网关]** Node.js BFF 层，管理 WebSockets 长连接，秒级分发计算信号，兼顾 Audit Log 审计。
- `packages/frontend-web`: **[高性能看板]** React 看板，专注于海量数据高性能渲染、极端情况防错决策视图。

## ⚙️ 快速开始

1. 安装依赖：
   ```bash
   pnpm install
   ```
