from datetime import datetime
from typing import List, Dict, Tuple, Callable, Optional
from sqlalchemy.orm import Session
import logging
import threading
from utils import get_analysis_logger

from models import AnalysisResult, Task
import repository
from chains.prompts import (
    REDUCE_PROMPTS,
    SYSTEM_PROMPTS,
    COMBINED_MAP_PROMPT,
    COMBINED_SYSTEM_PROMPT,
    RESULT_TYPES,
    CHUNK_SIZE,
    IGNORE_WORDS,
)
from core.constants import MAX_CONTENT_LENGTH, MAX_WORKERS  
from chains.langchain_analysis import create_analyzer

try:
    import ollama
except ImportError:
    ollama = None

logger = get_analysis_logger()

analysis_lock = threading.RLock()
cancel_flags: Dict[int, bool] = {}
analysis_tasks: Dict[int, dict] = {}

def split_messages(messages: List, chunk_size: int = CHUNK_SIZE) -> List[List]:
    chunks = []
    for i in range(0, len(messages), chunk_size):
        chunks.append(messages[i:i + chunk_size])
    return chunks

def log_analysis(task_id: int, message: str):
    log_msg = f"[Task {task_id}] {message}"
    logger.info(log_msg)
    with analysis_lock:
        if task_id in analysis_tasks:
            analysis_tasks[task_id]["logs"].append(log_msg)

def check_cancel(task_id: int) -> bool:
    return cancel_flags.get(task_id, False)

def get_task_status(db: Session, task_id: int) -> Tuple[str, Optional[str]]:
    task = repository.get_task(db, task_id)
    if not task:
        return "not_found", None
    return task.status, None

def get_analysis_status(task_id: int) -> dict:
    with analysis_lock:
        if task_id in analysis_tasks:
            return analysis_tasks[task_id]
    return {
        "status": "not_found",
        "result_count": 0,
        "logs": [],
        "error": None
    }

def get_analysis_logs(task_id: int) -> List[str]:
    with analysis_lock:
        if task_id not in analysis_tasks:
            return []
        return analysis_tasks[task_id].get("logs", [])

def cancel_analysis(task_id: int) -> bool:
    cancel_flags[task_id] = True
    with analysis_lock:
        if task_id in analysis_tasks:
            analysis_tasks[task_id]["status"] = "cancelled"
    return True

def analyze_async(task_id: int):
    from core.database import get_db
    db = next(get_db())
    
    try:
        log_analysis(task_id, f"开始分析任务 {task_id}")

        task = repository.get_task(db, task_id)
        if not task:
            log_analysis(task_id, "任务不存在")
            with analysis_lock:
                analysis_tasks[task_id]["status"] = "failed"
                analysis_tasks[task_id]["error"] = "任务不存在"
            return

        messages = repository.get_messages_for_analysis(db, task_id, IGNORE_WORDS, MAX_CONTENT_LENGTH)

        if not messages:
            log_analysis(task_id, "没有消息可分析")
            with analysis_lock:
                analysis_tasks[task_id]["status"] = "failed"
                analysis_tasks[task_id]["error"] = "没有消息可分析"
            return

        log_analysis(task_id, f"共 {len(messages)} 条消息待分析")

        cancel_flags[task_id] = False

        completed_types = repository.get_result_types_by_task(db, task_id)
        log_analysis(task_id, f"已完成的分析类型: {completed_types}")

        message_chunks = split_messages(messages, CHUNK_SIZE)
        log_analysis(task_id, f"消息分块完成，共 {len(message_chunks)} 块")

        for rt in completed_types:
            repository.delete_by_task_and_type(db, task_id, rt)

        def progress_callback(processed_count: int):
            msg = f"  已并行处理 {processed_count}/{len(message_chunks)} 块..."
            log_analysis(task_id, msg)
            print(f"[Task {task_id}] {msg}")

        log_analysis(task_id, f"  开始合并 Map 阶段 (5维度联合提取, max_workers={MAX_WORKERS})...")
        analyzer = create_analyzer(max_workers=MAX_WORKERS)
        map_results_by_type = analyzer.parallel_combined_map(
            message_chunks,
            COMBINED_SYSTEM_PROMPT,
            COMBINED_MAP_PROMPT,
            RESULT_TYPES,
            progress_callback=progress_callback,
            log_callback=lambda msg: log_analysis(task_id, msg)
        )

        for rt in RESULT_TYPES:
            filtered = [r for r in map_results_by_type.get(rt, []) if r and r.strip()]
            log_analysis(task_id, f"  {rt} Map 结果: {len(filtered)} 个有效分段")

        if check_cancel(task_id):
            log_analysis(task_id, "任务已取消")
            with analysis_lock:
                analysis_tasks[task_id]["status"] = "cancelled"
            repository.update_task_status(db, task_id, 'completed')
            return

        log_analysis(task_id, f"  开始顺序 Reduce 阶段 (5维度逐个整合)...")
        print(f"[Task {task_id}] 开始顺序 Reduce 阶段 (5维度逐个整合)...")
        reduce_results = analyzer.parallel_reduce(
            map_results_by_type,
            SYSTEM_PROMPTS,
            REDUCE_PROMPTS,
            log_callback=lambda msg: log_analysis(task_id, msg)
        )
        log_analysis(task_id, f"  Reduce 阶段完成")
        print(f"[Task {task_id}] Reduce 阶段完成")

        new_results_count = 0
        for rt, reduce_result in reduce_results.items():
            if reduce_result and len(reduce_result.strip()) > 5:
                result = AnalysisResult(
                    task_id=task_id,
                    contact_id=0,
                    result_type=rt,
                    analysis_type='global',
                    content=reduce_result[:2000],
                    created_at=datetime.now(),
                )
                repository.create_analysis_result(db, result)
                new_results_count += 1
                log_analysis(task_id, f"  已保存类型 {rt} 的分析结果")
            else:
                map_fallback = map_results_by_type.get(rt, [])
                map_fallback = [r for r in map_fallback if r and r.strip()]
                if map_fallback:
                    fallback_content = "\n\n".join([f"分段{i+1}: {r}" for i, r in enumerate(map_fallback)])
                    result = AnalysisResult(
                        task_id=task_id,
                        contact_id=0,
                        result_type=rt,
                        analysis_type='global',
                        content=fallback_content[:2000],
                        created_at=datetime.now(),
                    )
                    repository.create_analysis_result(db, result)
                    new_results_count += 1
                    log_analysis(task_id, f"  类型 {rt} Reduce为空，已保存Map分段结果({len(map_fallback)}段)")
                else:
                    log_analysis(task_id, f"  类型 {rt} 无有效分析结果")

        if task_id in cancel_flags:
            del cancel_flags[task_id]

        final_status = 'completed' if reduce_results else 'analyzing'

        logger.info(f"Task {task_id} analysis completed: final_status={final_status}")

        repository.update_task_status(db, task_id, final_status)

        with analysis_lock:
            analysis_tasks[task_id]["status"] = "completed"
            analysis_tasks[task_id]["result_count"] = new_results_count
            log_analysis(task_id, f"分析完成，共 {new_results_count} 项结果")

    except Exception as e:
        log_analysis(task_id, f"分析失败: {str(e)}")
        with analysis_lock:
            analysis_tasks[task_id]["status"] = "failed"
            analysis_tasks[task_id]["error"] = str(e)

        repository.update_task_status(db, task_id, 'failed')

    finally:
        db.close()

def start_analysis(db: Session, task_id: int, task_status: str) -> Tuple[bool, str]:
    from chains.prompts import RESULT_TYPES

    completed_types = repository.get_result_types_by_task(db, task_id)
    all_types = set(RESULT_TYPES)

    if completed_types == all_types:
        return True, ""

    with analysis_lock:
        if task_id in analysis_tasks and analysis_tasks[task_id]["status"] == "running":
            return False, "任务正在分析中"
        analysis_tasks[task_id] = {
            "status": "running",
            "logs": [],
            "result_count": 0,
            "error": None
        }

    messages = repository.get_messages_for_analysis(db, task_id, IGNORE_WORDS, MAX_CONTENT_LENGTH)

    if not messages:
        return False, "没有消息可分析"

    repository.update_task_status(db, task_id, 'analyzing')

    thread = threading.Thread(target=analyze_async, args=(task_id,))
    thread.start()

    return True, ""

def get_analysis_results(db: Session, task_id: int) -> List[dict]:
    results = repository.get_analysis_results_by_task(db, task_id)
    return [
        {
            "id": r.id,
            "task_id": r.task_id,
            "result_type": r.result_type,
            "content": r.content,
            "created_at": r.created_at,
        }
        for r in results
    ]

def is_task_analyzable(task: Task) -> bool:
    return task.status in ['imported', 'extracted', 'pending', 'analyzing', 'completed']
