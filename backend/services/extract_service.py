import re
from datetime import datetime
from typing import List, Tuple
from sqlalchemy.orm import Session

from models import ExtractedInfo, Task
import repository
from core.constants import INFO_PATTERNS, ADDRESS_KEYWORDS

def luhn_check(card_number: str) -> bool:
    digits = [int(d) for d in card_number if d.isdigit()]
    if len(digits) < 13 or len(digits) > 19:
        return False

    checksum = 0
    reverse_digits = digits[::-1]
    for i, digit in enumerate(reverse_digits):
        if i % 2 == 1:
            digit *= 2
            if digit > 9:
                digit -= 9
        checksum += digit

    return checksum % 10 == 0

def extract_info_from_content(content: str) -> List[dict]:
    results = []

    for info_type, patterns in INFO_PATTERNS.items():
        for pattern in patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                value = match.group(0)
                if info_type == 'bank_card':
                    if not luhn_check(value):
                        continue

                start = max(0, match.start() - 20)
                end = min(len(content), match.end() + 20)
                context = content[start:end]

                results.append({
                    'info_type': info_type,
                    'value': value,
                    'context': f'...{context}...',
                    'confidence': 0.8 if info_type != 'password' else 0.5,
                })

    for keyword in ADDRESS_KEYWORDS:
        if keyword in content:
            idx = content.find(keyword)
            start = max(0, idx - 30)
            end = min(len(content), idx + 30)
            address = content[start:end]

            has_result = any(r['info_type'] == 'address' and r['value'] == address for r in results)
            if not has_result and len(address) > 5:
                results.append({
                    'info_type': 'address',
                    'value': address,
                    'context': address,
                    'confidence': 0.6,
                })
            break

    return results

def extract_info(db: Session, task_id: int) -> Tuple[int, str]:
    task = repository.get_task(db, task_id)
    if not task:
        return 0, "任务不存在"

    if task.status not in ['imported', 'extracted', 'pending', 'analyzing', 'completed']:
        return 0, "任务状态不允许提取"

    messages = repository.get_messages_for_extraction(db, task_id)

    if not messages:
        return 0, "没有消息可提取"

    repository.delete_by_task(db, task_id)

    all_extracted = []
    for msg in messages:
        extracted = extract_info_from_content(msg.content)
        for item in extracted:
            item['message_id'] = msg.id
            item['contact_id'] = msg.contact_id
        all_extracted.extend(extracted)

    seen = set()
    unique_extracted = []
    for item in all_extracted:
        key = (item['info_type'], item['value'])
        if key not in seen:
            seen.add(key)
            unique_extracted.append(item)

    now = datetime.now()
    info_objects = [
        ExtractedInfo(
            task_id=task_id,
            message_id=item['message_id'],
            contact_id=item['contact_id'],
            info_type=item['info_type'],
            value=item['value'],
            context=item['context'],
            confidence=item['confidence'],
            created_at=now,
        )
        for item in unique_extracted
    ]

    repository.create_extracted_info_batch(db, info_objects)

    repository.update_task_status(db, task_id, 'extracted')

    return len(unique_extracted), ""

def get_extracted_info(db: Session, task_id: int) -> List[dict]:
    return repository.get_extracted_info_by_task(db, task_id)
