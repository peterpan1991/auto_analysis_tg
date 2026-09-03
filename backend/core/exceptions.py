class RetrievalServiceUnavailableError(RuntimeError):
    """Embedding 或向量数据库暂时不可用。"""


class LLMServiceUnavailableError(RuntimeError):
    """LLM 服务调用失败。"""


class LLMResponseError(RuntimeError):
    """LLM 调用成功，但返回内容无法作为有效回答使用。"""
