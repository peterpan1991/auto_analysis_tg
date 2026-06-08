from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate, HumanMessagePromptTemplate
from langchain_core.messages import HumanMessage, SystemMessage
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Optional, Callable
import json
import re
import logging

from chains.prompts import (
    SUB_REDUCE_PROMPTS,
    GLOBAL_REDUCE_PROMPTS,
    REDUCE_PROMPTS,
    SYSTEM_PROMPTS,
)
from core.constants import MAX_ITEMS_PER_SUB_REDUCE, MAX_CHARS_PER_ITEM

logger = logging.getLogger(__name__)


class LangChainAnalyzer:
    def __init__(self, model: str = "qwen2.5:7b", max_workers: int = 2):
        self.model = model
        self.max_workers = max_workers
        self.llm = ChatOllama(
            model=model,
            temperature=0,
            num_ctx=8192,
            num_predict=1024,
            timeout=120,
        )
        self.reduce_llm = ChatOllama(
            model=model,
            temperature=0,
            num_ctx=8192,
            num_predict=2048,
            timeout=180,
        )

    def _format_messages(self, messages_chunk: List) -> str:
        content_parts = [f"[{getattr(msg, 'sender', str(msg))}]: {getattr(msg, 'content', str(msg))}" for msg in messages_chunk]
        return "\n".join(content_parts)

    INVOKE_TIMEOUT = 180

    def _safe_invoke(self, chain, inp: dict, timeout: int = 0) -> str:
        actual_timeout = timeout or self.INVOKE_TIMEOUT
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(self._do_invoke, chain, inp)
            try:
                return future.result(timeout=actual_timeout)
            except Exception as e:
                logger.error(f"LLM invoke timeout or failed ({actual_timeout}s): {e}")
                future.cancel()
                return ""

    def _do_invoke(self, chain, inp: dict) -> str:
        try:
            result = chain.invoke(inp)
            return result.content if hasattr(result, 'content') else str(result)
        except Exception as e:
            logger.error(f"LLM invoke failed: {e}")
            return ""

    def _run_parallel(
        self,
        chain,
        inputs: List[dict],
        log_callback: Optional[Callable[[str], None]] = None
    ) -> List[Optional[str]]:
        results: List[Optional[str]] = [None] * len(inputs)
        total = len(inputs)
        completed_count = 0

        if log_callback:
            log_callback(f"开始处理 {total} 个分块，并发数={self.max_workers}")

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_idx = {
                executor.submit(self._safe_invoke, chain, inp): idx
                for idx, inp in enumerate(inputs)
            }

            for future in as_completed(future_to_idx):
                idx = future_to_idx[future]
                try:
                    results[idx] = future.result()
                except Exception as e:
                    logger.error(f"Chunk {idx} failed: {e}")
                    results[idx] = ""

                completed_count += 1
                if log_callback:
                    log_callback(f"Map 进度: {completed_count}/{total} 完成")

        return results

    def parallel_map(
        self,
        message_chunks: List[List[Dict]],
        system_prompt: str,
        map_prompt: str,
        progress_callback: Optional[callable] = None,
        log_callback: Optional[Callable[[str], None]] = None
    ) -> List[str]:
        formatted_chunks = [self._format_messages(chunk) for chunk in message_chunks]
        prompts = [f"{map_prompt}\n{chunk}" for chunk in formatted_chunks]

        prompt_template = ChatPromptTemplate.from_messages([
            SystemMessage(content=system_prompt),
            HumanMessagePromptTemplate.from_template("{text}")
        ])
        chain = prompt_template | self.llm

        inputs = [{"text": p} for p in prompts]
        results = self._run_parallel(chain, inputs, log_callback=log_callback)

        if progress_callback:
            progress_callback(len(message_chunks))

        return [r if r is not None else "" for r in results]

    def parallel_combined_map(
        self,
        message_chunks: List[List[Dict]],
        system_prompt: str,
        map_prompt: str,
        result_types: List[str],
        progress_callback: Optional[callable] = None,
        log_callback: Optional[Callable[[str], None]] = None
    ) -> Dict[str, List[str]]:
        formatted_chunks = [self._format_messages(chunk) for chunk in message_chunks]
        prompts = [f"{map_prompt}\n{chunk}" for chunk in formatted_chunks]

        prompt_template = ChatPromptTemplate.from_messages([
            SystemMessage(content=system_prompt),
            HumanMessagePromptTemplate.from_template("{text}")
        ])
        chain = prompt_template | self.llm

        inputs = [{"text": p} for p in prompts]
        raw_results = self._run_parallel(chain, inputs, log_callback=log_callback)

        if progress_callback:
            progress_callback(len(message_chunks))

        parsed: Dict[str, List[str]] = {rt: [] for rt in result_types}

        for content in raw_results:
            if content is None or not content:
                for rt in result_types:
                    parsed[rt].append("")
                continue

            extracted = self._extract_json_fields(content, result_types)

            for rt in result_types:
                val = extracted.get(rt, "").strip()
                parsed[rt].append(val)

        return parsed

    def _extract_json_fields(self, content: str, fields: List[str]) -> Dict[str, str]:
        result = {f: "" for f in fields}

        json_str = self._find_json(content)
        if not json_str:
            for f in fields:
                result[f] = self._extract_field_by_regex(content, f)
            return result

        try:
            data = json.loads(json_str)
            if isinstance(data, dict):
                for f in fields:
                    val = str(data.get(f, "")).strip()
                    result[f] = val
                return result
        except json.JSONDecodeError:
            pass

        for f in fields:
            result[f] = self._extract_field_by_regex(content, f)
        return result

    def _find_json(self, content: str) -> Optional[str]:
        brace_count = 0
        start = -1
        for i, ch in enumerate(content):
            if ch == '{':
                if brace_count == 0:
                    start = i
                brace_count += 1
            elif ch == '}':
                brace_count -= 1
                if brace_count == 0 and start >= 0:
                    return content[start:i + 1]
        return None

    def _extract_field_by_regex(self, content: str, field: str) -> str:
        pattern = rf'"{field}"\s*:\s*"((?:[^"\\]|\\.)*)\"'
        match = re.search(pattern, content)
        if match:
            return match.group(1).strip()
        return ""

    def reduce(
        self,
        map_results: List[str],
        system_prompt: str,
        reduce_prompt_template: str
    ) -> str:
        if not map_results:
            return ""

        filtered_results = [r for r in map_results if r]
        all_summary = "\n\n".join([f"分段{i+1}: {r}" for i, r in enumerate(filtered_results)])
        prompt_text = reduce_prompt_template.format(summary=all_summary)

        prompt_template = ChatPromptTemplate.from_messages([
            SystemMessage(content=system_prompt),
            HumanMessagePromptTemplate.from_template("{text}")
        ])
        chain = prompt_template | self.reduce_llm
        return self._safe_invoke(chain, {"text": prompt_text}, timeout=180)

    def parallel_reduce(
        self,
        map_results_by_type: Dict[str, List[str]],
        system_prompts: Dict[str, str],
        reduce_prompts: Dict[str, str],
        log_callback: Optional[Callable[[str], None]] = None
    ) -> Dict[str, str]:
        valid_types = {rt: mr for rt, mr in map_results_by_type.items() if any(r and r.strip() for r in mr)}
        if not valid_types:
            return {}

        results = {}
        total = len(valid_types)
        completed = 0

        for rt, mr in valid_types.items():
            try:
                msg = f"Reduce 进度: 开始处理 {rt} ({completed+1}/{total})"
                if log_callback:
                    log_callback(msg)
                rt_key, content = self._tiered_reduce(rt, mr, system_prompts, reduce_prompts, log_callback)
                results[rt_key] = content
                completed += 1
                msg = f"Reduce 进度: {completed}/{total} 完成 ({rt})"
                if log_callback:
                    log_callback(msg)
            except Exception as e:
                logger.error(f"Reduce for {rt} failed: {e}")
                results[rt] = ""
                completed += 1

        return results

    def _tiered_reduce(
        self,
        result_type: str,
        items: List[str],
        system_prompts: Dict[str, str],
        reduce_prompts: Dict[str, str],
        log_callback: Optional[Callable[[str], None]] = None
    ) -> tuple:
        filtered = [r.strip() for r in items if r and r.strip()]
        if not filtered:
            return (result_type, "")

        if len(filtered) <= MAX_ITEMS_PER_SUB_REDUCE:
            msg = f"  [{result_type}] 共 {len(filtered)} 条，直接合并"
            if log_callback:
                log_callback(msg)
            return self._single_reduce(result_type, filtered, system_prompts[result_type], reduce_prompts[result_type])

        groups = self._split_groups(filtered, MAX_ITEMS_PER_SUB_REDUCE)
        msg = f"  [{result_type}] 共 {len(filtered)} 条，分 {len(groups)} 组进行小合并"
        if log_callback:
            log_callback(msg)

        sub_results = []
        for i, group in enumerate(groups):
            sub_text = self._single_reduce(
                result_type,
                group,
                system_prompts[result_type],
                SUB_REDUCE_PROMPTS[result_type]
            )
            sub_content = sub_text[1] if isinstance(sub_text, tuple) else sub_text
            if sub_content and sub_content.strip():
                sub_results.append(sub_content.strip())
            msg = f"  [{result_type}] 第 {i+1}/{len(groups)} 组小合并完成"
            if log_callback:
                log_callback(msg)

        if len(sub_results) == 1:
            return (result_type, sub_results[0])

        msg = f"  [{result_type}] 开始全局合并 {len(sub_results)} 个子结果"
        if log_callback:
            log_callback(msg)
        return self._single_reduce(result_type, sub_results, system_prompts[result_type], GLOBAL_REDUCE_PROMPTS[result_type])

    def _split_groups(self, items: List[str], max_size: int) -> List[List[str]]:
        groups = []
        for i in range(0, len(items), max_size):
            groups.append(items[i:i + max_size])
        return groups

    def _single_reduce(self, result_type: str, items: List[str], system_prompt: str, reduce_prompt_template: str) -> tuple:
        truncated = [item[:MAX_CHARS_PER_ITEM] for item in items]
        summary = "\n\n".join([f"分段{i+1}: {r}" for i, r in enumerate(truncated)])
        prompt_text = reduce_prompt_template.format(summary=summary)

        prompt_template = ChatPromptTemplate.from_messages([
            SystemMessage(content=system_prompt),
            HumanMessagePromptTemplate.from_template("{text}")
        ])
        chain = prompt_template | self.reduce_llm
        content = self._safe_invoke(chain, {"text": prompt_text}, timeout=180)
        return (result_type, content)


def create_analyzer(model: str = "qwen2.5:7b", max_workers: int = 2, timeout: int = 0) -> LangChainAnalyzer:
    return LangChainAnalyzer(model=model, max_workers=max_workers)
