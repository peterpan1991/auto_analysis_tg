import json
from pathlib import Path
import sys
from services.vectorize_service import search_relevant_messages


CASES_FILE = Path(__file__).with_name("retrieval_cases.json")


def load_cases() -> list[dict]:
    with CASES_FILE.open("r", encoding="utf-8") as file:
        return json.load(file)

def is_case_passed(case: dict, results: list[dict]) -> bool:
    if case["expect_empty"]:
        return len(results) == 0

    expected_keyword_groups = case.get("expected_keyword_groups")

    if expected_keyword_groups:
        return all(
            any(
                all(
                    keyword in result.get("content", "")
                    for keyword in keyword_group
                )
                for result in results
            )
            for keyword_group in expected_keyword_groups
        )

    expected_keywords = case["expected_keywords"]

    return any(
        all(
            keyword in result.get("content", "")
            for keyword in expected_keywords
        )
        for result in results
    )


def main():
    passed_count = 0

    if len(sys.argv) != 2:
        raise SystemExit(
            "用法：python -m evals.run_retrieval_eval <task_id>"
        )
    
    task_id = int(sys.argv[1])
    cases = load_cases()

    for case in cases:
        results = search_relevant_messages(
            task_id=task_id,
            query=case["query"],
        )

        top_similarity = (
            results[0]["similarity"]
            if results
            else None
        )

        passed = is_case_passed(case, results)

        if passed:
            passed_count += 1

        status = "PASS" if passed else "FAIL"

        print(
            f"[{status}] {case['name']}，"
            f"召回数量：{len(results)}，"
            f"最高相似度：{top_similarity}"
        )

    total_count = len(cases)

    print(f"\n评估结果：{passed_count}/{total_count} 通过")

    if passed_count != total_count:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
