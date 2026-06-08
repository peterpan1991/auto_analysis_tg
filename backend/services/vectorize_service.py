import json
import re
import hashlib
import threading
import time
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Callable
from sqlalchemy.orm import Session
from langchain_ollama import OllamaEmbeddings, ChatOllama

from models import Message
import repository.message_repository as message_repo

from core.constants import (
    DEFAULT_MODEL, EMBEDDING_MODEL, VECTOR_DB_PATH,
    EMBEDDING_CHUNK_SIZE, EMBEDDING_OVERLAP_SIZE, EMBEDDING_MAX_CHARS,
    EMBEDDING_TIME_GAP_SECONDS, EMBEDDING_BATCH_SIZE,
    EMBEDDING_DB_BATCH_SIZE, EMBEDDING_CHROMA_BATCH_SIZE,
    MULTI_QUERY_COUNT, MULTI_QUERY_TOP_K,
    ABSTRACT_QUERY_KEYWORDS,
)
from utils import get_vectorize_logger
from libs import ChromaDBClient

vectorize_logger = get_vectorize_logger()
chroma_client = ChromaDBClient()

ollama_embeddings = OllamaEmbeddings(model=EMBEDDING_MODEL)
ollama_chat = ChatOllama(model=DEFAULT_MODEL, temperature=0, num_ctx=8192)

vectorize_tasks: dict[int, dict] = {}
vectorize_lock = threading.Lock()


def log_vectorize(task_id: int, message: str):
    log_msg = f"[Task {task_id}] {message}"
    with vectorize_lock:
        if task_id in vectorize_tasks:
            vectorize_tasks[task_id]["logs"].append(log_msg)
    vectorize_logger.info(log_msg)


def get_embedding(text: str, retries: int = 3) -> Optional[List[float]]:
    for attempt in range(retries):
        try:
            embedding = ollama_embeddings.embed_query(text[:EMBEDDING_MAX_CHARS])
            return embedding
        except Exception as e:
            log_vectorize(0, f"Embedding attempt {attempt + 1} failed: {str(e)}")
            if attempt < retries - 1:
                time.sleep(1)
    return None


def get_embeddings_batch(texts: List[str], retries: int = 3) -> Optional[List[List[float]]]:
    truncated = [t[:EMBEDDING_MAX_CHARS] for t in texts]
    for attempt in range(retries):
        try:
            embeddings = ollama_embeddings.embed_documents(truncated)
            return embeddings
        except Exception as e:
            log_vectorize(0, f"Batch embedding attempt {attempt + 1} failed: {str(e)}")
            if attempt < retries - 1:
                time.sleep(2)
    return None


def cosine_similarity(a: List[float], b: List[float]) -> float:
    import numpy as np
    a_np = np.array(a)
    b_np = np.array(b)
    norm_a = np.linalg.norm(a_np)
    norm_b = np.linalg.norm(b_np)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a_np, b_np) / (norm_a * norm_b))


def get_vectorization_status(db: Session, task_id: int) -> dict:
    try:
        chunk_count = chroma_client.count(task_id)

        total_result = db.query(Message).filter(Message.task_id == task_id).count()

        with vectorize_lock:
            task_info = vectorize_tasks.get(task_id, {})
            task_status = task_info.get("status", "not_found")
            task_progress = task_info.get("progress", 0)
            messages_processed = task_info.get("messages_processed", 0)

        if task_status == "completed":
            is_vectorized = True
            progress = 100
        elif task_status == "failed":
            is_vectorized = False
            progress = task_progress
        elif task_status == "running":
            is_vectorized = messages_processed > 0
            progress = task_progress
        else:
            if chunk_count > 0 and total_result > 0:
                is_vectorized = True
                progress = 100
            else:
                is_vectorized = messages_processed > 0 and messages_processed >= total_result * 0.9
                progress = task_progress if task_progress > 0 else round(messages_processed / total_result * 100, 2) if total_result > 0 else 0

        return {
            "task_id": task_id,
            "message_count": total_result,
            "messages_processed": messages_processed if task_status != "not_found" else total_result if is_vectorized else 0,
            "chunk_count": chunk_count,
            "is_vectorized": is_vectorized,
            "progress": progress
        }
    except Exception as e:
        log_vectorize(task_id, f"获取向量化状态失败: {str(e)}")
        return {
            "task_id": task_id,
            "message_count": 0,
            "messages_processed": 0,
            "chunk_count": 0,
            "is_vectorized": False,
            "progress": 0
        }


def start_vectorization(db: Session, task_id: int, log_callback: Optional[Callable[[str], None]] = None):
    with vectorize_lock:
        vectorize_tasks[task_id] = {
            "status": "running",
            "logs": [],
            "progress": 0,
            "error": None,
            "messages_processed": 0
        }

    total_result = message_repo.get_message_count(db, task_id)
    log_vectorize(task_id, f"开始向量化 {total_result} 条消息")

    if total_result == 0:
        log_vectorize(task_id, "没有消息需要向量化")
        update_status(task_id, "completed", progress=100)
        return

    thread = threading.Thread(
        target=do_vectorization_async,
        args=(task_id, total_result, log_callback)
    )
    thread.start()


def _split_by_time_gap(messages: List[Message], time_gap: int) -> List[List[Message]]:
    """基于时间间隔将消息分成语义段落，同一时间段内的连续对话归为一组"""
    if not messages:
        return []

    segments = []
    current_segment = [messages[0]]

    for i in range(1, len(messages)):
        prev_ts = messages[i - 1].timestamp
        curr_ts = messages[i].timestamp
        if prev_ts and curr_ts and (curr_ts - prev_ts).total_seconds() > time_gap:
            if len(current_segment) >= 2:
                segments.append(current_segment)
            current_segment = [messages[i]]
        else:
            current_segment.append(messages[i])

    if len(current_segment) >= 2:
        segments.append(current_segment)

    return segments


def _build_chunk_text(chunk_messages: List[Message]) -> str:
    """构建 chunk 文本，确保总长度不超过 embedding 模型的 context length"""
    max_total_chars = EMBEDDING_MAX_CHARS
    chunk_text_parts = []
    current_len = 0

    for msg in chunk_messages:
        sender = msg.sender or "Unknown"
        content = (msg.content or "").strip()
        if not content:
            continue

        line = f"[{sender}]: {content}"
        line_len = len(line)

        # 如果单条消息就超限，截断该消息
        if line_len > max_total_chars - 5:
            line = line[:max_total_chars - 5] + "..."
            line_len = len(line)

        # 如果加上这条消息会超限，停止添加
        if current_len + line_len + 1 > max_total_chars:
            break

        chunk_text_parts.append(line)
        current_len += line_len + 1  # +1 for newline

    return "\n".join(chunk_text_parts)


def _flush_to_chroma(task_id: int, ids, embeddings, metadatas, documents):
    if not ids:
        return True
    try:
        chroma_client.upsert_embeddings(
            task_id=task_id,
            ids=ids,
            embeddings=embeddings,
            metadatas=metadatas,
            documents=documents
        )
        return True
    except Exception as e:
        log_vectorize(task_id, f"ChromaDB 存储失败: {str(e)}, 跳过此批次")
        return False


def do_vectorization_async(task_id: int, total_result: int, log_callback: Optional[Callable[[str], None]] = None):
    from core.database import get_db
    db = next(get_db())

    try:
        os.makedirs(VECTOR_DB_PATH, exist_ok=True)

        existing_count = chroma_client.count(task_id)
        if existing_count > 0:
            log_vectorize(task_id, f"发现已有 {existing_count} 条向量，清除旧数据后重新向量化")
            try:
                chroma_client.delete_collection(task_id)
            except:
                pass

        log_vectorize(task_id, f"开始向量化 {total_result} 条消息，使用时间语义分块 + 滑动窗口")

        # 分批加载：先获取所有 contact_id，再按 contact 加载消息
        contact_ids = message_repo.get_contact_ids_by_task(db, task_id)
        if not contact_ids:
            log_vectorize(task_id, "没有消息需要向量化")
            update_status(task_id, "completed", progress=100)
            return

        # 预估总 chunk 数用于进度显示
        total_messages_loaded = 0
        estimated_chunks = 0
        for cid in contact_ids:
            count = db.query(Message).filter(
                Message.task_id == task_id,
                Message.contact_id == cid
            ).count()
            total_messages_loaded += count
            # 粗略估算：每个时间语义段约 chunk_size 条消息
            estimated_chunks += max(count // (EMBEDDING_CHUNK_SIZE // 2), 1)

        log_vectorize(task_id, f"共 {len(contact_ids)} 个联系人, {total_messages_loaded} 条消息, 预估 {estimated_chunks} 个 chunks")

        # 收集所有 chunk 数据
        all_chunk_texts = []
        all_chunk_meta = []

        messages_processed = 0
        total_chunks = 0
        last_progress = 0

        for contact_id in contact_ids:
            # 按联系人分批加载消息
            contact_messages = message_repo.get_messages_by_contact_ordered(db, task_id, contact_id)
            if not contact_messages:
                continue

            # 第一步：基于时间间隔做语义分段
            time_segments = _split_by_time_gap(contact_messages, EMBEDDING_TIME_GAP_SECONDS)

            # 第二步：对每个语义段用滑动窗口分 chunk
            chunk_size = EMBEDDING_CHUNK_SIZE
            overlap_size = EMBEDDING_OVERLAP_SIZE
            step_size = chunk_size - overlap_size

            for segment in time_segments:
                seg_len = len(segment)

                # 语义段小于 chunk_size，直接作为一个 chunk
                if seg_len <= chunk_size:
                    chunk_text = _build_chunk_text(segment)
                    if chunk_text.strip():
                        content_hash = hashlib.md5(chunk_text.encode()).hexdigest()
                        all_chunk_texts.append(chunk_text)
                        all_chunk_meta.append({
                            "contact_id": contact_id,
                            "messages": segment,
                            "chunk_id": f"{contact_id}_{segment[0].id}",
                            "content_hash": content_hash,
                        })
                        total_chunks += 1
                else:
                    # 滑动窗口分块
                    for i in range(0, seg_len, step_size):
                        chunk_messages = segment[i:i + chunk_size]
                        if len(chunk_messages) < 2:
                            continue

                        chunk_text = _build_chunk_text(chunk_messages)
                        if not chunk_text.strip():
                            continue

                        content_hash = hashlib.md5(chunk_text.encode()).hexdigest()
                        all_chunk_texts.append(chunk_text)
                        all_chunk_meta.append({
                            "contact_id": contact_id,
                            "messages": chunk_messages,
                            "chunk_id": f"{contact_id}_{segment[0].id}_{i}",
                            "content_hash": content_hash,
                        })
                        total_chunks += 1

            messages_processed += len(contact_messages)

            # 批量 embedding + 写入 ChromaDB
            if len(all_chunk_texts) >= EMBEDDING_BATCH_SIZE:
                _process_and_flush_chunks(task_id, all_chunk_texts, all_chunk_meta)

                progress = round(messages_processed / total_messages_loaded * 100, 2) if total_messages_loaded > 0 else 0
                if progress > last_progress:
                    last_progress = progress
                    log_vectorize(task_id, f"进度: {messages_processed}/{total_messages_loaded} 消息, {total_chunks} chunks ({progress}%)")
                    update_status(task_id, "running", progress=progress, messages_processed=messages_processed)

                all_chunk_texts = []
                all_chunk_meta = []

        # 处理剩余的 chunks
        if all_chunk_texts:
            _process_and_flush_chunks(task_id, all_chunk_texts, all_chunk_meta)

        log_vectorize(task_id, f"向量化完成，共生成 {total_chunks} 个 chunks")
        update_status(task_id, "completed", progress=100, messages_processed=total_messages_loaded)

    except Exception as e:
        log_vectorize(task_id, f"向量化失败: {str(e)}")
        update_status(task_id, "failed", error=str(e))
    finally:
        db.close()


def _process_and_flush_chunks(task_id: int, chunk_texts: List[str], chunk_meta: List[dict]):
    """批量获取 embedding 并写入 ChromaDB"""
    chroma_ids = []
    chroma_embeddings = []
    chroma_metadatas = []
    chroma_documents = []

    # 分批调用 embed_documents
    batch_size = EMBEDDING_BATCH_SIZE
    for batch_start in range(0, len(chunk_texts), batch_size):
        batch_end = min(batch_start + batch_size, len(chunk_texts))
        batch_texts = chunk_texts[batch_start:batch_end]
        batch_meta = chunk_meta[batch_start:batch_end]

        embeddings = get_embeddings_batch(batch_texts)
        if embeddings is None:
            log_vectorize(task_id, f"Batch embedding 失败 (batch {batch_start}-{batch_end})，尝试逐条 embedding")
            # 降级为逐条 embedding
            for idx, text in enumerate(batch_texts):
                embedding = get_embedding(text)
                if embedding is None:
                    log_vectorize(task_id, f"单条 embedding 也失败，跳过该 chunk")
                    continue
                meta = batch_meta[idx]
                chroma_ids.append(meta["chunk_id"])
                chroma_embeddings.append(embedding)
                chroma_metadatas.append(_build_metadata(meta))
                chroma_documents.append(text)
        else:
            for idx, (embedding, text) in enumerate(zip(embeddings, batch_texts)):
                meta = batch_meta[idx]
                chroma_ids.append(meta["chunk_id"])
                chroma_embeddings.append(embedding)
                chroma_metadatas.append(_build_metadata(meta))
                chroma_documents.append(text)

        # 达到 ChromaDB 批量写入阈值时写入
        if len(chroma_ids) >= EMBEDDING_CHROMA_BATCH_SIZE:
            _flush_to_chroma(task_id, chroma_ids, chroma_embeddings, chroma_metadatas, chroma_documents)
            chroma_ids = []
            chroma_embeddings = []
            chroma_metadatas = []
            chroma_documents = []

    # 写入剩余数据
    _flush_to_chroma(task_id, chroma_ids, chroma_embeddings, chroma_metadatas, chroma_documents)


def _build_metadata(meta: dict) -> dict:
    messages = meta["messages"]
    chunk_text_parts = []
    for msg in messages:
        sender = msg.sender or "Unknown"
        content = (msg.content or "").strip()
        if content:
            chunk_text_parts.append(f"[{sender}]: {content[:100]}")
    content_preview = "\n".join(chunk_text_parts)[:500]

    return {
        "contact_id": meta["contact_id"],
        "start_message_id": messages[0].id,
        "end_message_id": messages[-1].id,
        "message_count": len(messages),
        "sender": messages[0].sender or "Unknown",
        "timestamp": messages[0].timestamp.isoformat() if messages[0].timestamp else "",
        "content": content_preview,
        "content_hash": meta["content_hash"],
    }


def update_status(task_id: int, status: str, progress: float = 0, error: str = None, messages_processed: int = None):
    with vectorize_lock:
        if task_id in vectorize_tasks:
            vectorize_tasks[task_id]["status"] = status
            vectorize_tasks[task_id]["progress"] = progress
            if error:
                vectorize_tasks[task_id]["error"] = error
            if messages_processed is not None:
                vectorize_tasks[task_id]["messages_processed"] = messages_processed


def get_vectorize_status(task_id: int) -> dict:
    with vectorize_lock:
        if task_id not in vectorize_tasks:
            return {
                "status": "not_found",
                "progress": 0,
                "logs": [],
                "error": None,
                "embedding_count": 0
            }
        return {
            "status": vectorize_tasks[task_id]["status"],
            "progress": vectorize_tasks[task_id]["progress"],
            "logs": vectorize_tasks[task_id]["logs"][-50:],
            "error": vectorize_tasks[task_id].get("error"),
            "embedding_count": chroma_client.count(task_id)
        }


def cancel_vectorization(task_id: int):
    with vectorize_lock:
        if task_id in vectorize_tasks:
            vectorize_tasks[task_id]["status"] = "cancelled"


def _detect_abstract_topics(query: str) -> List[str]:
    """检测查询是否包含抽象主题，返回匹配到的 topic key 列表"""
    matched = []
    for topic, keywords in ABSTRACT_QUERY_KEYWORDS.items():
        for kw in keywords:
            if kw in query:
                matched.append(topic)
                break
    return matched


def _build_keyword_queries(topic: str) -> List[str]:
    """根据抽象主题生成关键词查询，用空格拼接关键词作为检索文本"""
    keywords = ABSTRACT_QUERY_KEYWORDS.get(topic, [])
    if not keywords:
        return []
    # 将关键词分成 2-3 个一组，生成多个查询
    queries = []
    chunk_size = 3
    for i in range(0, len(keywords), chunk_size):
        group = keywords[i:i + chunk_size]
        queries.append(" ".join(group))
    return queries[:2]  # 最多 2 个关键词查询


def expand_query_for_search(query: str) -> List[str]:
    """生成多个检索查询：LLM 改写 + 抽象查询关键词补充"""
    queries = []

    # 1. 检测抽象主题，补充关键词查询
    abstract_topics = _detect_abstract_topics(query)
    for topic in abstract_topics:
        keyword_queries = _build_keyword_queries(topic)
        queries.extend(keyword_queries)

    # 2. LLM 改写：生成与原问题同义的检索查询
    expand_prompt = f"""你是一个聊天记录检索专家。请将用户问题改写成 {MULTI_QUERY_COUNT} 个检索查询。

规则：
- 查询必须能匹配到聊天记录中的原文内容，不是对问题的回答
- 只改写表述方式，禁止添加原问题中不存在的具体人名、地名
- 可以变换同义词、口语/书面语、提问角度

原问题: {query}

直接输出 {MULTI_QUERY_COUNT} 个查询，每行一个："""

    try:
        result = ollama_chat.invoke(expand_prompt)
        content = result.content if hasattr(result, 'content') else str(result)
        content = content.strip()

        for line in content.split('\n'):
            line = line.strip()
            if not line:
                continue
            cleaned = re.sub(r'^(查询|Query|Search)\s*[:：]?\s*', '', line, flags=re.IGNORECASE)
            cleaned = re.sub(r'^\d+[\.\)、、]\s*', '', cleaned)
            if cleaned:
                queries.append(cleaned)
    except Exception as e:
        vectorize_logger.error(f"查询扩展失败: {str(e)}")

    # 3. 确保原问题本身也在查询列表中
    if query not in queries:
        queries.insert(0, query)

    queries = queries[:MULTI_QUERY_COUNT + 2]  # 关键词查询 + LLM 查询，略多留余量
    vectorize_logger.info(f"多查询扩展: '{query}' -> {queries}")
    return queries


def search_relevant_messages(db: Session, task_id: int, query: str, queries: List[str] = None) -> List[Dict]:
    """多查询检索：对每个查询分别搜索，合并去重后按相似度排序"""
    if queries is None:
        queries = [query]

    all_results = []
    seen_ids = set()

    for q in queries:
        query_embedding = get_embedding(q[:500])
        if query_embedding is None:
            continue

        try:
            results = chroma_client.query(
                task_id=task_id,
                query_embedding=query_embedding,
                n_results=MULTI_QUERY_TOP_K,
            )

            from libs.chromadb_lib import format_query_results
            formatted = format_query_results(results)

            for item in formatted:
                chunk_id = item.get("chunk_id", "")
                if chunk_id not in seen_ids:
                    seen_ids.add(chunk_id)
                    all_results.append(item)

        except Exception as e:
            log_vectorize(task_id, f"搜索失败 (query='{q[:30]}'): {str(e)}")

    # 按相似度降序排序
    all_results.sort(key=lambda x: x.get("similarity", 0), reverse=True)

    return all_results


def chat_with_context(db: Session, task_id: int, prompt: str) -> Dict:
    queries = expand_query_for_search(prompt)
    relevant_messages = search_relevant_messages(db, task_id, prompt, queries=queries)

    context = ""
    if relevant_messages:
        context = "以下是相关的聊天记录：\n"
        for i, msg in enumerate(relevant_messages, 1):
            sender = msg.get("sender", "Unknown")
            content = msg.get("content", "")
            context += f"{i}. [{sender}]: {content}\n"

    system_prompt = f"""你是一个 Telegram 聊天记录分析助手。用户会询问关于聊天记录的问题。
请基于提供的聊天记录上下文来回答问题。
回答要简洁明了，突出重点。
如果上下文中没有相关信息，请说明"根据提供的聊天记录，我无法回答这个问题"。"""

    full_prompt = f"{system_prompt}\n\n{context}\n\n用户问题: {prompt}\n\n请回答:"

    try:
        result = ollama_chat.invoke(full_prompt)
        return {
            "response": result.content if hasattr(result, 'content') else str(result),
            "context_messages": len(relevant_messages),
            "expanded_queries": queries
        }
    except Exception as e:
        vectorize_logger.error(f"Chat error: {str(e)}")

    return {
        "response": "抱歉，AI 服务暂时不可用，请稍后重试。",
        "context_messages": 0,
        "expanded_queries": queries
    }
