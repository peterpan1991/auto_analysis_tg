import threading
import json
import os
import re
from datetime import datetime
from sqlalchemy.orm import Session

from models import User, Contact, Message, Task
import repository
from utils import get_import_logger
from core.constants import DEFAULT_USER_ID
from utils.parse_tg import (
    parse_telegram_date,
    parse_telegram_content,
    parse_user_info_from_html,
    parse_contacts_from_chats_html,
    parse_messages_from_html,
    is_valid_telegram_message,
    remove_emojis,
)

import_logger = get_import_logger()

import_tasks: dict[int, dict] = {}
import_lock = threading.Lock()

def log_import(task_id: int, message: str):
    log_msg = f"[Task {task_id}] {message}"
    import_logger.info(log_msg)
    with import_lock:
        if task_id in import_tasks:
            import_tasks[task_id]["logs"].append(log_msg)

def ensure_default_user(db: Session) -> int:
    user = repository.get_user_by_id(db, DEFAULT_USER_ID)
    if not user:
        user = User(
            id=DEFAULT_USER_ID,
            first_name="Default User",
            username="default_user",
            phone=None,
            chats_count=0
        )
        user = repository.create_user(db, user)
    return DEFAULT_USER_ID

def get_or_create_user(db: Session, user_info: dict) -> int:
    username = user_info.get("username")
    phone = user_info.get("phone")
    first_name = user_info.get("first_name", "")
    chats_count = user_info.get("chats_count", 0)

    if username:
        user = repository.get_user_by_username(db, username)
        if user:
            user.first_name = first_name
            user.phone = phone
            user.chats_count = chats_count
            repository.update_user(db, user)
            return user.id

    if phone:
        user = repository.get_user_by_phone(db, phone)
        if user:
            user.first_name = first_name
            user.username = username
            user.chats_count = chats_count
            repository.update_user(db, user)
            return user.id

    user = User(
        first_name=first_name,
        username=username,
        phone=phone,
        chats_count=chats_count
    )
    user = repository.create_user(db, user)
    return user.id

def start_import(db: Session, task_id: int, folder_path: str = None, file_content: str = None, file_name: str = None):
    with import_lock:
        import_tasks[task_id] = {
            "status": "running",
            "logs": [],
            "message_count": 0,
            "error": None
        }

    thread = threading.Thread(
        target=do_import_async,
        args=(task_id, folder_path, file_content, file_name)
    )
    thread.start()

def get_import_status(task_id: int) -> dict:
    with import_lock:
        if task_id not in import_tasks:
            return {
                "status": "not_found",
                "message_count": 0,
                "logs": [],
                "error": None
            }
        return import_tasks[task_id]

def get_import_logs(task_id: int) -> dict:
    with import_lock:
        if task_id not in import_tasks:
            return {"logs": []}
        return {"logs": import_tasks[task_id].get("logs", [])}

def cancel_import(task_id: int):
    with import_lock:
        if task_id in import_tasks:
            import_tasks[task_id]["status"] = "cancelled"

def get_messages_by_task(db: Session, task_id: int) -> list:
    return repository.get_messages_by_task(db, task_id)

def do_import_async(task_id: int, folder_path: str = None, file_content: str = None, file_name: str = None):
    from core.database import get_db

    db = next(get_db())
    try:
        message_count = 0

        if folder_path:
            result = import_from_folder(db, folder_path, task_id)
            message_count = result["message_count"]
        elif file_content and file_name:
            result = import_from_content(db, task_id, file_content, file_name)
            message_count = result["message_count"]

        if message_count == 0:
            with import_lock:
                import_tasks[task_id]["status"] = "failed"
                import_tasks[task_id]["error"] = "没有找到可导入的消息"
            return

        task = repository.get_task(db, task_id)
        if task:
            repository.update_task_message_count(db, task_id, message_count)
            repository.update_task_status(db, task_id, "imported")

        with import_lock:
            import_tasks[task_id]["status"] = "completed"
            import_tasks[task_id]["message_count"] = message_count

    except Exception as e:
        log_import(task_id, f"导入失败: {str(e)}")
        with import_lock:
            import_tasks[task_id]["status"] = "failed"
            import_tasks[task_id]["error"] = str(e)

    finally:
        db.close()

def import_from_folder(db: Session, folder_path: str, task_id: int) -> dict:
    log_import(task_id, f"开始导入文件夹: {folder_path}")

    is_new_format = os.path.exists(os.path.join(folder_path, "export_results.html")) or \
                    os.path.exists(os.path.join(folder_path, "lists", "chats.html"))

    user_info = parse_user_info_from_html(folder_path)
    if user_info:
        user_id = get_or_create_user(db, user_info)
        log_import(task_id, f"解析用户信息: {user_info.get('first_name', '未知')}")
    else:
        user_id = ensure_default_user(db)
        log_import(task_id, "未找到用户信息，使用默认用户")

    if is_new_format:
        return import_from_new_format(db, folder_path, task_id, user_id)

    json_files = []
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            if file == "messages.json":
                json_files.append(os.path.join(root, file))

    log_import(task_id, f"找到 {len(json_files)} 个 messages.json 文件")

    total_messages = 0

    for idx, json_file in enumerate(sorted(json_files)):
        try:
            log_import(task_id, f"处理文件 ({idx+1}/{len(json_files)}): {json_file}")
            result = process_messages_json(db, json_file, task_id, user_id)
            total_messages += result["message_count"]
            log_import(task_id, f"已导入 {result['message_count']} 条消息")
        except Exception as e:
            log_import(task_id, f"处理文件失败 {json_file}: {e}")
            continue

    log_import(task_id, f"导入完成，共 {total_messages} 条消息")
    return {"message_count": total_messages, "user_id": user_id}

def import_from_new_format(db: Session, folder_path: str, task_id: int, user_id: int) -> dict:
    log_import(task_id, "使用新格式导入")

    contacts = parse_contacts_from_chats_html(folder_path)
    log_import(task_id, f"找到 {len(contacts)} 个联系人/会话")

    total_messages = 0
    now = datetime.now()

    for idx, contact in enumerate(contacts):
        contact_obj = Contact(
            user_id=user_id,
            name=contact["name"],
            is_group=contact["is_group"],
            message_count=contact["message_count"]
        )
        contact_obj = repository.create_contact(db, contact_obj)
        contact_id = contact_obj.id

        chat_path = contact.get("chat_path", "")
        if chat_path and os.path.exists(chat_path):
            chat_dir = os.path.dirname(chat_path)

            all_messages_files = []
            if os.path.isdir(chat_dir):
                for f in os.listdir(chat_dir):
                    if f.startswith("messages") and f.endswith(".html"):
                        all_messages_files.append(f)

            all_messages_files.sort(key=lambda x: int(re.search(r'messages(\d+)\.html', x).group(1)) if re.search(r'messages(\d+)\.html', x) else (0 if x == "messages.html" else 999999))

            for msg_file in all_messages_files:
                msg_file_path = os.path.join(chat_dir, msg_file)
                messages = parse_messages_from_html(msg_file_path)

                msg_objects = []
                for msg in messages:
                    if not is_valid_telegram_message(msg, source="html"):
                        continue

                    sender = msg.get("sender", "Unknown")
                    content = msg.get("content", "")

                    clean_content = remove_emojis(content)
                    message = Message(
                        task_id=task_id,
                        user_id=user_id,
                        contact_id=contact_id,
                        sender=sender,
                        content=clean_content,
                        timestamp=parse_telegram_date(msg.get("timestamp")) if msg.get("timestamp") else now,
                        message_type="text",
                        raw_content=content,
                        clean_content=clean_content,
                        created_at=now
                    )
                    msg_objects.append(message)

                if msg_objects:
                    repository.create_messages_bulk(db, msg_objects)

            if (idx + 1) % 10 == 0:
                log_import(task_id, f"已处理 {idx + 1}/{len(contacts)} 个会话")

    total_messages = repository.count_messages_by_task(db, task_id)
    log_import(task_id, f"导入完成，共 {total_messages} 条消息")
    return {"message_count": total_messages, "user_id": user_id}

def import_from_content(db: Session, task_id: int, file_content: str, file_name: str) -> dict:
    parse_result = parse_telegram_content(file_content, file_name)
    messages = parse_result.get("messages", [])
    user_info = parse_result.get("user_info")
    contacts = parse_result.get("contacts", [])

    if not messages:
        log_import(task_id, "无法解析聊天记录")
        return {"message_count": 0}

    if user_info:
        user_id = get_or_create_user(db, user_info)
        log_import(task_id, f"导入用户信息: {user_info.get('first_name', '未知')}")
    else:
        user_id = ensure_default_user(db)

    now = datetime.now()

    contact_name_to_id = {}
    chat_contacts = [c for c in contacts if c.get("message_count", 0) > 0 and c.get("name")]

    if chat_contacts:
        for contact in chat_contacts:
            name = contact.get("name", "Unknown")
            is_group = contact.get("is_group", 0)
            msg_count = contact.get("message_count", 0)

            contact_obj = Contact(
                user_id=user_id,
                name=name,
                is_group=is_group,
                message_count=msg_count
            )
            contact_obj = repository.create_contact(db, contact_obj)
            contact_name_to_id[name] = contact_obj.id
        log_import(task_id, f"导入联系人: {len(chat_contacts)} 个")
    else:
        peer_name = file_name.replace('.json', '').replace('.txt', '').replace('.csv', '')
        contact_obj = Contact(
            user_id=user_id,
            name=peer_name,
            is_group=0,
            message_count=0
        )
        contact_obj = repository.create_contact(db, contact_obj)
        contact_name_to_id[peer_name] = contact_obj.id

    total = len(messages)
    valid_count = 0
    msg_objects = []

    for idx, msg in enumerate(messages):
        if not is_valid_telegram_message(msg, source="html"):
            continue

        sender = msg.get('sender', '').strip() if msg.get('sender') else ''
        content = msg.get('content', '')
        raw_content = content
        clean_content = remove_emojis(content)

        contact_name = msg.get('contact_name')
        msg_contact_id = contact_name_to_id.get(contact_name) if contact_name else list(contact_name_to_id.values())[0] if contact_name_to_id else None

        if msg_contact_id is None:
            msg_contact_id = list(contact_name_to_id.values())[0] if contact_name_to_id else 0

        try:
            timestamp = parse_telegram_date(msg.get('timestamp', ''))
        except:
            timestamp = now

        message = Message(
            task_id=task_id,
            user_id=user_id,
            contact_id=msg_contact_id,
            sender=sender,
            content=clean_content,
            timestamp=timestamp,
            message_type='text',
            raw_content=raw_content,
            clean_content=clean_content,
            created_at=now
        )
        msg_objects.append(message)
        valid_count += 1

        if (idx + 1) % 1000 == 0:
            log_import(task_id, f"导入进度: {idx + 1}/{total} 条消息")
            repository.create_messages_bulk(db, msg_objects)
            msg_objects = []

    if msg_objects:
        repository.create_messages_bulk(db, msg_objects)

    log_import(task_id, f"导入完成，共 {valid_count} 条消息")
    return {"message_count": valid_count}

def process_messages_json(db: Session, file_path: str, task_id: int, user_id: int) -> dict:
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    peer_name = data.get("peer_name", os.path.basename(os.path.dirname(file_path)))
    message_count = data.get("message_count", 0)
    messages_data = data.get("messages", [])

    if message_count <= 0 and len(messages_data) <= 0:
        return {"contact_id": None, "message_count": 0}

    is_group = 1 if message_count > 100 else 0

    contact_obj = Contact(
        user_id=user_id,
        name=peer_name,
        is_group=is_group,
        message_count=message_count
    )
    contact_obj = repository.create_contact(db, contact_obj)
    contact_id = contact_obj.id

    now = datetime.now()
    msg_count = 0
    total = len(messages_data)
    msg_objects = []

    for idx, msg in enumerate(messages_data):
        extra_info = {}
        if msg.get("id"):
            extra_info["msg_id"] = msg["id"]
        if "is_outgoing" in msg:
            extra_info["is_outgoing"] = msg["is_outgoing"]
        if msg.get("reply_to_msg_id"):
            extra_info["reply_to_msg_id"] = msg["reply_to_msg_id"]
        if msg.get("forward_from"):
            extra_info["forward_from"] = msg["forward_from"]
        if msg.get("file_name"):
            extra_info["file_name"] = msg["file_name"]

        extra_info_json = json.dumps(extra_info) if extra_info else None

        msg_type = "text"
        if msg.get("media_type"):
            if "Photo" in msg["media_type"]:
                msg_type = "image"
            elif "Video" in msg["media_type"]:
                msg_type = "video"
            elif "Document" in msg["media_type"]:
                msg_type = "document"
            elif "Audio" in msg["media_type"]:
                msg_type = "audio"

        try:
            send_time = parse_telegram_date(msg.get("date", ""))
        except:
            send_time = now

        if not is_valid_telegram_message(msg, source="json"):
            continue

        sender = msg.get("sender_name", peer_name)
        text = msg.get("text", "")
        if isinstance(text, list):
            text = ''.join([t.get("text", "") if isinstance(t, dict) else str(t) for t in text])

        message = Message(
            task_id=task_id,
            user_id=user_id,
            contact_id=contact_id,
            sender=sender,
            content=remove_emojis(text),
            timestamp=send_time,
            message_type=msg_type,
            raw_content=text,
            clean_content=remove_emojis(text),
            created_at=now
        )
        msg_objects.append(message)
        msg_count += 1

        if (idx + 1) % 1000 == 0:
            log_import(task_id, f"导入进度: {idx + 1}/{total} 条消息")
            repository.create_messages_bulk(db, msg_objects)
            msg_objects = []

    if msg_objects:
        repository.create_messages_bulk(db, msg_objects)

    return {"contact_id": contact_id, "message_count": msg_count}
