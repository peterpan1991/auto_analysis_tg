# Telegram 聊天记录智能分析系统

基于 FastAPI + Ant Design + Ollama 的 Telegram 聊天记录分析工具，支持多维度信息提取、智能分析和可视化展示。

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | React 18 + TypeScript + Ant Design 5 + React Router 6 + Vite |
| 后端 | FastAPI + SQLAlchemy + Pydantic |
| 数据库 | MySQL |
| AI 引擎 | Ollama (qwen2.5:7b) + LangChain |
| 日志 | Python logging |

## 项目结构

```
auto_analysis_tg/
├── backend/                          # 后端服务
│   ├── main.py                       # FastAPI 入口
│   ├── .env                          # 环境变量配置
│   ├── api/v1/                       # API 路由层
│   │   ├── tasks.py                  # 任务管理 API
│   │   ├── chat.py                   # 聊天记录 API
│   │   ├── analysis.py               # 分析结果 API
│   │   └── extract.py                # 信息提取 API
│   ├── core/                         # 核心配置
│   │   ├── constants.py              # 常量定义（模型、分块大小、正则等）
│   │   ├── database.py               # 数据库连接
│   │   └── router.py                 # 路由注册
│   ├── models/                       # SQLAlchemy 数据模型
│   │   ├── task.py                   # 任务模型
│   │   ├── message.py                # 消息模型
│   │   ├── contact.py                # 联系人模型
│   │   ├── analysis_result.py        # 分析结果模型
│   │   └── extracted_info.py         # 提取信息模型
│   ├── repository/                   # 数据访问层
│   │   └── *                          # 各模型的 CRUD 操作
│   ├── schemas/                      # Pydantic 请求/响应模型
│   │   ├── task_schema.py
│   │   ├── chat_schema.py
│   │   ├── analysis_schema.py
│   │   └── extract_schema.py
│   ├── services/                     # 业务逻辑层
│   │   ├── task_service.py           # 任务管理服务
│   │   ├── chat_service.py           # 聊天记录服务
│   │   ├── extract_service.py        # 信息提取服务
│   │   └── analysis_service.py        # AI 分析服务（核心）
│   ├── chains/                       # AI 分析链
│   │   ├── langchain_analysis.py      # LangChain 分析器（Map-Reduce）
│   │   └── prompts.py                # AI 提示词模板
│   ├── utils/                        # 工具函数
│   │   ├── logger.py                 # 日志配置
│   │   └── parse_tg.py               # Telegram 聊天解析
│   └── db/
│       └── db.sql                     # SQLite 数据库文件
├── frontend/                         # 前端应用
│   ├── src/
│   │   ├── api/
│   │   │   └── index.ts              # Axios API 封装
│   │   ├── pages/
│   │   │   ├── TaskList.tsx          # 任务列表页
│   │   │   ├── ChatImport.tsx        # 聊天导入页
│   │   │   └── AnalysisResult.tsx    # 分析结果页
│   │   ├── types/
│   │   │   └── index.ts              # TypeScript 类型定义
│   │   ├── App.tsx                   # 根组件
│   │   └── main.tsx                  # React 入口
│   ├── index.html
│   ├── package.json
│   └── vite.config.ts
└── README.md
```

## 核心功能

### 1. 聊天导入
- 支持导入 Telegram 聊天记录
- 自动清洗系统消息、短词（嗯嗯、好的）、重复内容
- 自动解析消息结构（发送者、时间、内容）
- 批量处理大规模聊天数据

### 2. 信息提取
基于正则模式从聊天记录中自动提取敏感信息：

| 信息类型 | 正则模式 |
|----------|----------|
| 手机号 | `1[3-9]\d{9}` |
| 身份证 | 18位身份证格式 |
| 车牌号 | 武京沪渝等 + 字母数字 |
| 银行卡 | 62/4/5/9 开头卡号 |
| 快递单号 | SF/顺丰/YTO/圆通 等 |
| 邮箱 | 标准邮箱格式 |
| 虚拟账号 | QQ/微信/TG 等 |
| URL/Domain | HTTP(S) URL + 域名 |

### 3. AI 智能分析（Ollama + LangChain）

采用 **Map-Reduce** 架构对聊天记录进行多维度深度分析：

```
聊天记录 (1373 条)
       │
       ▼
┌─────────────┐
│  Map 阶段   │  ← 7 个分块并行处理，每个块 200 条消息
│ 5维度联合   │     person_info / org_structure /
│  提取 JSON  │     fund_flow / chat_topics / location_info
└─────────────┘
       │
       ▼
┌─────────────┐
│ Reduce 阶段 │  ← 5 个维度顺序整合
│ 5维度并行   │     每个维度独立生成完整分析报告
│   整合      │
└─────────────┘
```

**5 个分析维度：**

| 维度 | 说明 |
|------|------|
| person_info | 人物识别：姓名、身份角色、联系方式 |
| org_structure | 组织架构：层级关系、分工协作 |
| fund_flow | 资金流向：金额、交易双方、用途 |
| chat_topics | 话题分析：讨论主题及关键细节 |
| location_info | 位置信息：地点及活动目的 |

**性能优化：**
- 并发数控制：Map 阶段 2 并发，Reduce 阶段顺序执行
- 上下文窗口：8192 tokens
- 输出 token 限制：Map 1024，Reduce 2048
- 请求超时保护：180 秒强制超时
- 提示词前缀复用：利用 Ollama KV Cache 加速

## 快速开始

### 环境要求

- Python 3.10+
- Node.js 18+
- Ollama 已安装并运行（模型：qwen2.5:7b）

### 1. 启动 Ollama

```bash
ollama run qwen2.5:7b
```

### 2. 启动后端

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### 3. 启动前端

```bash
cd frontend
npm install
npm run dev
```

访问 `http://localhost:3000` 即可使用。

## API 概览

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/tasks` | 获取任务列表 |
| POST | `/api/v1/tasks` | 创建新任务 |
| DELETE | `/api/v1/tasks/{id}` | 删除任务 |
| POST | `/api/v1/chat/import/{task_id}` | 导入聊天记录 |
| GET | `/api/v1/chat/messages/{task_id}` | 获取消息列表 |
| POST | `/api/v1/extract/{task_id}` | 提取信息 |
| GET | `/api/v1/extract/results/{task_id}` | 获取提取结果 |
| POST | `/api/v1/analysis/start/{task_id}` | 启动 AI 分析 |
| GET | `/api/v1/analysis/status/{task_id}` | 获取分析状态 |
| GET | `/api/v1/analysis/results/{task_id}` | 获取分析结果 |
| POST | `/api/v1/analysis/cancel/{task_id}` | 取消分析 |

## 数据库模型

```
Task (任务)
├── id, name, status, created_at, updated_at
└── messages (一对多)

Message (消息)
├── id, task_id, sender, content, timestamp
├── date (消息日期)
└── extracted_infos (一对多)

ExtractedInfo (提取的信息)
├── id, message_id, info_type, content
└── info_type: phone/id_card/bank_card/express/...

AnalysisResult (分析结果)
├── id, task_id, contact_id, result_type
├── content, analysis_type (global/per_contact)
└── result_type: person_info/org_structure/fund_flow/...
```

### AI模型
```
# 语义模型
ollama pull qwen2.5:7b

# 向量模型
ollama pull shaw/dmeta-embedding-zh
```

## 任务状态流转

```
pending → imported → extracted → analyzing → completed
                  ↓
              analyzing → failed / cancelled
```

## 配置说明

后端配置通过 `backend/.env` 文件管理：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `DEFAULT_MODEL` | qwen2.5:7b | Ollama 模型名称 |
| `CHUNK_SIZE` | 200 | Map 阶段每个分块的消息数 |
| `MAX_WORKERS` | 2 | 最大并发数 |
| `MAX_CONTENT_LENGTH` | 200 | 单条消息最大字符数 |
