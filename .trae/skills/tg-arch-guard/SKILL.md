---
name: "tg-arch-guard"
description: "Enforces project architecture conventions when adding new features. Invoke after adding new code to verify correct file placement, or when creating new models/APIs/services/repositories."
---

# TG Arch Guard

This skill enforces the architectural conventions of the auto_analysis_tg project. When new code is added, it verifies that each piece is placed in the correct layer and follows the established patterns.

## Project Architecture

```
backend/
├── api/v1/           # HTTP 路由层 — 只做参数校验、调用 service、返回响应
├── chains/           # LLM 相关 — 提示词、分析器、嵌入模型
│   ├── prompts.py    # 所有 LLM 提示词模板（唯一位置）
│   ├── langchain_analysis.py  # LangChain 分析器实现
│   └── models/       # 本地嵌入模型文件
├── core/             # 核心配置 — 常量、数据库连接、路由注册
│   ├── constants.py  # 全局常量（唯一位置）
│   ├── database.py   # SQLAlchemy 引擎和 Session
│   └── router.py     # FastAPI 路由注册（新 API 模块必须在此注册）
├── db/               # SQL 建表脚本
├── libs/             # 第三方库封装（如 ChromaDB）
├── models/           # SQLAlchemy ORM 模型定义
├── repository/       # 数据库 CRUD 操作（纯数据访问，不含业务逻辑）
├── schemas/          # Pydantic 请求/响应模型
├── services/         # 业务逻辑层 — 编排 repository + chains + 外部调用
├── utils/            # 工具函数 — 日志、解析等纯函数
└── vector_db/        # ChromaDB 持久化存储（运行时生成）
```

## Layer Responsibilities & Rules

### 1. `models/` — ORM 模型

**职责**：定义 SQLAlchemy 模型类，映射数据库表结构

**规则**：
- 每个表一个文件，文件名与表名对应（如 `message.py` → `Message` 类）
- 只包含 Column 定义和简单的 `__tablename__`
- 不包含任何业务逻辑或数据库操作
- 新模型必须在 `models/__init__.py` 中 import 并加入 `__all__`

**示例**：
```python
# models/message.py
from sqlalchemy import Column, Integer, String, Text, DateTime
from core.database import Base

class Message(Base):
    __tablename__ = "message"
    id = Column(Integer, primary_key=True)
    content = Column(Text, nullable=False)
    # ...
```

### 2. `repository/` — 数据访问层

**职责**：纯数据库 CRUD 操作

**规则**：
- 每个模型对应一个 repository 文件（如 `message_repository.py`）
- 函数签名第一参数为 `db: Session`
- 只做 `db.query()` / `db.add()` / `db.commit()` 等数据库操作
- **禁止**：调用 service、调用 LLM、包含业务逻辑
- 新 repository 函数必须在 `repository/__init__.py` 中 re-export

**示例**：
```python
# repository/message_repository.py
def get_messages_by_task(db: Session, task_id: int) -> List[Message]:
    return db.query(Message).filter(Message.task_id == task_id).all()
```

### 3. `services/` — 业务逻辑层

**职责**：编排 repository + chains + 外部调用，实现业务逻辑

**规则**：
- 每个功能模块一个 service 文件
- 通过 `import repository` 调用数据访问
- 通过 `from chains.xxx` 调用 LLM 相关功能
- 包含异步任务管理（threading、状态追踪）
- **禁止**：直接写 SQL / db.query()，应调用 repository

**示例**：
```python
# services/analysis_service.py
import repository
from chains.langchain_analysis import create_analyzer

def start_analysis(db, task_id, task_status):
    messages = repository.get_messages_for_analysis(db, task_id, ...)
    analyzer = create_analyzer()
    # ...
```

### 4. `api/v1/` — HTTP 路由层

**职责**：定义 API 端点，参数校验，调用 service，返回响应

**规则**：
- 每个功能模块一个路由文件
- 使用 `APIRouter()` 创建路由
- 通过 `Depends(get_db)` 注入数据库会话
- **禁止**：包含业务逻辑、直接调用 repository
- 只做：参数校验 → 调用 service → 构造响应
- 新路由文件必须在 `core/router.py` 中 import 并 `include_router`

**示例**：
```python
# api/v1/analysis.py
from fastapi import APIRouter, Depends
from core.database import get_db
import services.analysis_service as analysis_service

router = APIRouter()

@router.post("/tasks/{task_id}/analyze")
def analyze_chat(task_id: int, db: Session = Depends(get_db)):
    success, error = analysis_service.start_analysis(db, task_id, ...)
    # ...
```

### 5. `schemas/` — Pydantic 模型

**职责**：定义 API 请求/响应的数据结构

**规则**：
- 每个功能模块一个 schema 文件
- 使用 `BaseModel` 定义
- 配置 `model_config = {"from_attributes": True}` 以支持 ORM 转换
- **禁止**：包含业务逻辑

### 6. `chains/` — LLM 相关

**职责**：LLM 提示词、分析器、嵌入模型

**规则**：
- `chains/prompts.py` — **所有提示词的唯一位置**，不允许在其他文件中硬编码 prompt
- `chains/langchain_analysis.py` — LangChain 分析器实现
- `chains/models/` — 本地嵌入模型文件（不手动修改）
- **禁止**：在 service 或 api 中直接写 prompt 字符串

### 7. `core/` — 核心配置

**职责**：全局常量、数据库连接、路由注册

**规则**：
- `core/constants.py` — **所有常量的唯一位置**（模型名、分块大小、正则模式等）
- `core/database.py` — SQLAlchemy 引擎和 Session 工厂
- `core/router.py` — 路由注册中心，新增 API 模块必须在此注册
- **禁止**：在其他文件中定义全局常量或硬编码配置值

### 8. `libs/` — 第三方库封装

**职责**：封装第三方库的客户端接口

**规则**：
- 每个第三方库一个文件（如 `chromadb_lib.py`）
- 在 `libs/__init__.py` 中 re-export
- 提供统一的接口，隐藏底层实现细节

### 9. `utils/` — 工具函数

**职责**：纯函数工具（日志、解析等）

**规则**：
- 无副作用的纯函数
- 不依赖 service 或 repository
- 可被任何层调用

## Checklist for New Features

When adding a new feature, verify each item:

### 新增数据库表
- [ ] `models/xxx.py` — 创建 ORM 模型
- [ ] `models/__init__.py` — import 并加入 `__all__`
- [ ] `repository/xxx_repository.py` — 创建 CRUD 函数
- [ ] `repository/__init__.py` — re-export 新函数
- [ ] `db/db.sql` — 添加建表 SQL
- [ ] `schemas/xxx_schema.py` — 创建 Pydantic 模型（如需要 API）

### 新增 API 端点
- [ ] `schemas/xxx_schema.py` — 定义请求/响应模型
- [ ] `services/xxx_service.py` — 实现业务逻辑
- [ ] `api/v1/xxx.py` — 定义路由端点
- [ ] `core/router.py` — 注册新路由

### 新增 LLM 分析维度
- [ ] `core/constants.py` — 在 `RESULT_TYPES` 中添加维度 key
- [ ] `chains/prompts.py` — 在 `SYSTEM_PROMPTS`、`REDUCE_PROMPTS`、`SUB_REDUCE_PROMPTS`、`GLOBAL_REDUCE_PROMPTS` 中添加对应条目
- [ ] `chains/prompts.py` — 更新 `COMBINED_SYSTEM_PROMPT` 中的维度说明和 JSON 示例

### 新增配置常量
- [ ] `core/constants.py` — 在此文件中定义
- [ ] 其他文件通过 `from core.constants import XXX` 引用

## Common Violations

| 错误做法 | 正确位置 |
|---------|---------|
| 在 service 中写 `db.query()` | 放到 `repository/` |
| 在 api 中包含业务逻辑 | 移到 `services/` |
| 在 service 中硬编码 prompt 字符串 | 放到 `chains/prompts.py` |
| 在 service 中定义常量 | 放到 `core/constants.py` |
| 新增路由但未注册 | 在 `core/router.py` 中注册 |
| 新增模型但未导出 | 在 `models/__init__.py` 和 `repository/__init__.py` 中导出 |
| 在 repository 中包含业务逻辑 | 移到 `services/` |

## When to Invoke

- After adding new code files or functions
- When creating new models, APIs, services, or repositories
- When adding new LLM analysis dimensions
- When the user asks "这个代码应该放在哪里"
- When reviewing code placement after a feature is implemented
