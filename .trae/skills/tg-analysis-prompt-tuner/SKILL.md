---
name: "tg-analysis-prompt-tuner"
description: "Tunes and optimizes LLM analysis prompts for Telegram chat analysis. Invoke when user wants to improve analysis quality, add/modify analysis dimensions, or adjust prompt templates in prompts.py."
---

# TG Analysis Prompt Tuner

This skill helps tune and optimize the LLM analysis prompts used in the Telegram chat analysis pipeline. It focuses on the Map-Reduce prompt system defined in `backend/chains/prompts.py`.

## Core Files

- **`backend/chains/prompts.py`** — All prompt templates (SYSTEM_PROMPTS, REDUCE_PROMPTS, SUB_REDUCE_PROMPTS, GLOBAL_REDUCE_PROMPTS, COMBINED_SYSTEM_PROMPT, COMBINED_MAP_PROMPT)
- **`backend/chains/langchain_analysis.py`** — LangChain analyzer that uses the prompts (parallel_combined_map, parallel_reduce, _tiered_reduce)
- **`backend/core/constants.py`** — RESULT_TYPES defines the 5 analysis dimensions

## Current Analysis Dimensions

The system extracts 5 dimensions from chat messages via a combined Map-Reduce pipeline:

1. **person_info** — 人物信息（姓名、身份/角色、联系方式、相关活动）
2. **org_structure** — 组织架构（管理层、业务部门、层级关系、运作模式）
3. **fund_flow** — 资金流向（交易、规模、流转模式）
4. **chat_topics** — 聊天主题（话题名称、内容、涉及人物、关键信息）
5. **location_info** — 位置信息（地点名称、活动/目的、相关人物）

## Prompt Architecture

The analysis uses a 3-tier Reduce strategy:

1. **Combined Map** (`COMBINED_SYSTEM_PROMPT` + `COMBINED_MAP_PROMPT`): Extracts all 5 dimensions simultaneously from each message chunk in JSON format
2. **Sub-Reduce** (`SUB_REDUCE_PROMPTS`): When Map results exceed `MAX_ITEMS_PER_SUB_REDUCE`, groups are merged first
3. **Global Reduce** (`GLOBAL_REDUCE_PROMPTS`): Final merge of sub-reduce results
4. **Single Reduce** (`REDUCE_PROMPTS` + `SYSTEM_PROMPTS`): Direct merge when items are few enough

## When to Invoke This Skill

- User reports analysis results are empty, vague, or low quality
- User wants to add a new analysis dimension (e.g., "timeline", "risk_assessment")
- User wants to modify output format of an existing dimension
- User wants to adjust the balance between precision and recall in extraction
- User wants to change the JSON structure of Map output
- User asks about improving analysis effectiveness

## Tuning Guidelines

### Adding a New Analysis Dimension

1. Add the dimension key to `RESULT_TYPES` in `constants.py`
2. Add corresponding entries in all prompt dictionaries:
   - `SYSTEM_PROMPTS` — System prompt for the Reduce stage
   - `REDUCE_PROMPTS` — Reduce prompt template
   - `SUB_REDUCE_PROMPTS` — Sub-reduce prompt template
   - `GLOBAL_REDUCE_PROMPTS` — Global reduce prompt template
3. Update `COMBINED_SYSTEM_PROMPT` to include the new dimension in the JSON output spec
4. Ensure the JSON example in `COMBINED_SYSTEM_PROMPT` includes the new field

### Improving Extraction Quality

- **Too many empty results**: Relax the prompt constraints, add "如果分段中有信息则必须输出，不要返回空"
- **Hallucinated content**: Strengthen "只输出聊天记录中明确提到的信息，不要捏造、推断或创造"
- **Missing information**: Add explicit enumeration of what to look for, increase the character limit per dimension
- **Poor formatting**: Provide a more detailed output format example in the prompt
- **Inconsistent results across runs**: Lower temperature (already 0), add more specific constraints

### Adjusting Map Output

The `COMBINED_SYSTEM_PROMPT` controls the Map stage JSON extraction. Key tuning points:

- Character limit per dimension (currently 120 chars) — increase for more detail, decrease for conciseness
- JSON field names must match `RESULT_TYPES` exactly
- The regex fallback in `_extract_json_fields` handles malformed JSON — ensure field names are distinctive enough

### Adjusting Reduce Quality

Each dimension has 3 levels of Reduce prompts:

- **SUB_REDUCE_PROMPTS**: For merging small groups — focus on deduplication and consolidation
- **GLOBAL_REDUCE_PROMPTS**: For final merge of sub-results — focus on comprehensive integration
- **REDUCE_PROMPTS**: For direct single-pass merge — balance between detail and conciseness

## Important Constraints

- Map stage output must be valid JSON with fields matching `RESULT_TYPES`
- Each dimension's content in Map is limited (currently 120 chars) — this affects Reduce input quality
- The `_extract_json_fields` method has regex fallback — prompt changes should not break JSON parsing
- `MAX_ITEMS_PER_SUB_REDUCE` and `MAX_CHARS_PER_ITEM` in constants.py affect Reduce tier selection
- All prompts are in Chinese — maintain Chinese for consistency with the analysis target language
