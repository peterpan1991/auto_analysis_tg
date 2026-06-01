import json
import re
import os
from datetime import datetime, timedelta
from typing import Optional, List

from core.constants import WATER_PATTERNS

EMOJI_PATTERN = re.compile(
    "["
        "\U0001F600-\U0001F64F"  # 表情脸
        "\U0001F300-\U0001F5FF"  # 符号、物品
        "\U0001F680-\U0001F6FF"  # 交通、地图
        "\U0001F1E0-\U0001F1FF"  # 旗帜
        "\U0001F900-\U0001F9FF"  # 补充表情
        "\U0001FA00-\U0001FAFF"  # 新版表情
        "\U00002600-\U000026FF"  # 杂项符号
        "\U00002700-\U000027BF"  # 装饰符号
        "\U0001F700-\U0001F77F"  # 几何符号扩展
        "\U0001F780-\U0001F7FF"  # 游戏符号
        "\U0001F800-\U0001F8FF"  # 补充符号
    "]|[\uFE0F\u200D]"
)

def remove_emojis(text: str) -> str:
    return EMOJI_PATTERN.sub('', text).strip()

def is_numeric_water(content: str) -> bool:
    if content.strip().isdigit():
        return len(content.strip()) < 5
    return False

def contains_only_emoji(text: str) -> bool:
    cleaned = EMOJI_PATTERN.sub('', text).strip()
    return len(cleaned) == 0 and len(text.strip()) > 0

def is_content_too_short(content: str) -> bool:
    stripped = content.strip()
    if not stripped:
        return True

    chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', stripped))
    english_chars = len(re.findall(r'[a-zA-Z]', stripped))
    other_chars = len(stripped) - chinese_chars - english_chars

    if chinese_chars >= 3:
        return False

    if english_chars >= 10:
        return False

    if other_chars >= 4:
        return False

    return True

def is_valid_message(sender: str, content: str) -> bool:
    if not sender or sender.strip() == "":
        return False
    if sender == "Telegram":
        return False
    if not content or not content.strip():
        return False
    if is_content_too_short(content):
        return False
    stripped = content.strip()
    if stripped.isdigit() and len(stripped) <= 3:
        return False
    return True

def is_valid_telegram_message(msg: dict, source: str = "json") -> bool:
    if source == "json":
        msg_type = msg.get("type", "")
        if msg_type == "service":
            return False

        media_type = msg.get("media_type", "")
        if media_type in ("sticker", "video_file", "audio_file", "voice_file", "photo"):
            text = msg.get("text", "")
            if not text or not text.strip():
                return False

        action = msg.get("action", "")
        if action:
            return False

        date_str = msg.get("date", "")
        if date_str:
            msg_date = parse_telegram_date(date_str)
            one_year_ago = datetime.now() - timedelta(days=365)
            if msg_date < one_year_ago:
                return False

        text = msg.get("text", "")
        if isinstance(text, list):
            text = "".join([t.get("text", "") if isinstance(t, dict) else str(t) for t in text])

        if not text or not text.strip():
            return False

        if is_content_too_short(text):
            return False

        sender = msg.get("from", msg.get("sender_name", ""))
        if not sender or sender.strip() == "":
            return False
        if sender == "Telegram":
            return False

        for pattern in WATER_PATTERNS:
            if re.match(pattern, text.strip()):
                return False

        if is_numeric_water(text):
            return False

        if contains_only_emoji(text):
            return False

    elif source == "html":
        sender = msg.get("sender", "")
        content = msg.get("content", "")

        if not is_valid_message(sender, content):
            return False

        timestamp = msg.get("timestamp", "")
        if timestamp:
            msg_date = parse_telegram_date(timestamp)
            one_year_ago = datetime.now() - timedelta(days=365)
            if msg_date < one_year_ago:
                return False

        for pattern in WATER_PATTERNS:
            if re.match(pattern, content.strip()):
                return False

        if is_numeric_water(content):
            return False

        if contains_only_emoji(content):
            return False

    return True

def parse_telegram_date(date_str: str) -> datetime:
    if not date_str:
        return datetime.now()

    date_str = date_str.strip()

    formats = [
        "%d.%m.%Y %H:%M:%S %Z%z",
        "%d.%m.%Y %H:%M:%S UTC%z",
        "%d.%m.%Y %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%d.%m.%Y %H:%M",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue

    try:
        return datetime.fromisoformat(date_str.replace(" UTC", "+0000"))
    except:
        pass

    try:
        cleaned = re.sub(r'UTC([+-]\d{2}:\d{2})', r'\1', date_str)
        return datetime.fromisoformat(cleaned)
    except:
        pass

    return datetime.now()

def parse_json_format(content: str) -> dict:
    try:
        data = json.loads(content)
        messages = []
        user_info = None
        contacts = []

        if isinstance(data, dict) and 'personal_information' in data:
            return parse_telegram_export_format(data)

        if isinstance(data, dict) and 'messages' in data:
            peer_name = data.get('peer_name', 'Unknown')
            for msg in data['messages']:
                sender = msg.get('sender_name', peer_name)
                text = msg.get('text', '')
                if isinstance(text, list):
                    text = ''.join([t.get('text', '') if isinstance(t, dict) else str(t) for t in text])

                date_str = msg.get('date', datetime.now().isoformat())
                messages.append({
                    'sender': sender,
                    'content': text,
                    'timestamp': date_str,
                })
        elif isinstance(data, list):
            for msg in data:
                sender = msg.get('sender_name', msg.get('from', 'Unknown'))
                text = msg.get('text', '')
                if isinstance(text, list):
                    text = ''.join([t.get('text', '') if isinstance(t, dict) else str(t) for t in text])

                date_str = msg.get('date', datetime.now().isoformat())
                messages.append({
                    'sender': sender,
                    'content': text,
                    'timestamp': date_str,
                })

        return {
            "messages": messages,
            "user_info": user_info,
            "contacts": contacts
        }
    except json.JSONDecodeError:
        return {"messages": [], "user_info": None, "contacts": []}

def parse_telegram_export_format(data: dict) -> dict:
    messages = []
    user_info = None
    contacts = []

    if "personal_information" in data:
        personal = data["personal_information"]
        user_info = {
            "first_name": personal.get("first_name", ""),
            "username": personal.get("username", ""),
            "phone": personal.get("phone_number", ""),
            "chats_count": 0
        }

    if "contacts" in data and "list" in data["contacts"]:
        contacts = data["contacts"]["list"]

    if "chats" in data and "list" in data["chats"]:
        for chat in data["chats"]["list"]:
            chat_name = chat.get("name", "Unknown")
            chat_id = chat.get("id", 0)
            chat_type = chat.get("type", "")
            is_group = 1 if chat_type in ["group", "supergroup"] else 0

            chat_messages = []
            if "messages" in chat:
                for msg in chat["messages"]:
                    text_field = msg.get("text")

                    raw_content = json.dumps(text_field, ensure_ascii=False) if text_field else ""
                    content = extract_text_content(text_field)
                    content = remove_emojis(content)
                    clean_content = content.strip()

                    chat_messages.append({
                        'sender': msg.get('from', msg.get('from_id', 'Unknown')),
                        'content': content,
                        'timestamp': msg.get('date', datetime.now().isoformat()),
                        'raw_content': raw_content,
                        'clean_content': clean_content,
                        'contact_name': chat_name,
                        'contact_id': chat_id,
                        'is_group': is_group
                    })

            messages.extend(chat_messages)

            contacts.append({
                "name": chat_name,
                "message_count": len(chat_messages),
                "is_group": is_group
            })

    return {
        "messages": messages,
        "user_info": user_info,
        "contacts": contacts
    }

def parse_telegram_content(content: str, file_name: str) -> dict:
    messages = []
    user_info = None
    contacts = []
    lines = content.split('\n')

    if file_name.endswith('.json'):
        return parse_json_format(content)

    current_sender = None
    current_time = None
    current_content = []

    for line in lines:
        line = line.strip()
        if not line:
            continue

        match = re.match(r'^(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\s*[-–]\s*(.+?)\s*[-–]\s*(.+)$', line)
        if match:
            if current_sender and current_content:
                messages.append({
                    'sender': current_sender,
                    'content': '\n'.join(current_content),
                    'timestamp': current_time,
                })

            current_time = match.group(1).strip()
            current_sender = match.group(2).strip()
            current_content = [match.group(3).strip()]
        else:
            if current_sender:
                current_content.append(line)

    if current_sender and current_content:
        messages.append({
            'sender': current_sender,
            'content': '\n'.join(current_content),
            'timestamp': current_time,
        })

    if not messages:
        for line in lines:
            line = line.strip()
            if not line:
                continue

            simple_match = re.match(r'^(.+?):\s*(.+)$', line)
            if simple_match:
                messages.append({
                    'sender': simple_match.group(1).strip(),
                    'content': simple_match.group(2).strip(),
                    'timestamp': datetime.now().isoformat(),
                })
            elif line:
                messages.append({
                    'sender': 'Unknown',
                    'content': line,
                    'timestamp': datetime.now().isoformat(),
                })

    return {
        "messages": messages,
        "user_info": user_info,
        "contacts": contacts
    }

def extract_text_content(text_field):
    if isinstance(text_field, str):
        return text_field

    if isinstance(text_field, list):
        result_parts = []
        for item in text_field:
            if isinstance(item, str):
                result_parts.append(item)
            elif isinstance(item, dict) and "text" in item:
                result_parts.append(item["text"])
        return "".join(result_parts)

    return str(text_field) if text_field else ""

def parse_user_info_from_html(folder_path: str) -> Optional[dict]:
    from bs4 import BeautifulSoup

    export_results_path = os.path.join(folder_path, "export_results.html")
    if os.path.exists(export_results_path):
        return _parse_user_info_from_export_results(export_results_path)

    html_path = os.path.join(folder_path, "messages.html")
    if not os.path.exists(html_path):
        return None

    with open(html_path, "r", encoding="utf-8") as f:
        html_content = f.read()

    soup = BeautifulSoup(html_content, "html.parser")

    personal_info = soup.find("div", class_="personal_info")
    if not personal_info:
        return None

    user_info = {"first_name": "", "username": "", "phone": "", "chats_count": 0}

    rows = personal_info.find_all("div", class_="row")
    for row in rows:
        label_elem = row.find("div", class_="label")
        value_elem = row.find("div", class_="value")

        if not label_elem or not value_elem:
            continue

        label = label_elem.get_text(strip=True)
        value = value_elem.get_text(strip=True)

        if label == "Name":
            user_info["first_name"] = value
        elif label == "Username":
            user_info["username"] = value.lstrip("@")
        elif label == "Phone":
            user_info["phone"] = value

    if not user_info["first_name"]:
        return None

    chats_section = soup.find("div", class_="sections")
    if chats_section:
        counter = chats_section.find("div", class_="counter")
        if counter:
            try:
                user_info["chats_count"] = int(counter.get_text(strip=True))
            except:
                user_info["chats_count"] = 0

    return user_info

def _parse_user_info_from_export_results(html_path: str) -> Optional[dict]:
    from bs4 import BeautifulSoup

    with open(html_path, "r", encoding="utf-8") as f:
        html_content = f.read()

    soup = BeautifulSoup(html_content, "html.parser")

    user_info = {"first_name": "", "username": "", "phone": "", "chats_count": 0}

    rows = soup.find_all("div", class_="row")
    for row in rows:
        label_elem = row.find("div", class_="label")
        value_elem = row.find("div", class_="value")

        if not label_elem or not value_elem:
            continue

        label = label_elem.get_text(strip=True)
        value = value_elem.get_text(strip=True)

        if label == "First name":
            user_info["first_name"] = value
        elif label == "Username":
            user_info["username"] = value.lstrip("@")
        elif label == "Phone number":
            user_info["phone"] = value

    if not user_info["first_name"]:
        return None

    return user_info

def parse_contacts_from_chats_html(folder_path: str) -> list:
    from bs4 import BeautifulSoup

    chats_list_path = os.path.join(folder_path, "lists", "chats.html")
    if not os.path.exists(chats_list_path):
        return []

    with open(chats_list_path, "r", encoding="utf-8") as f:
        html_content = f.read()

    soup = BeautifulSoup(html_content, "html.parser")

    contacts = []
    entries = soup.find_all("a", class_="entry")

    lists_dir = os.path.dirname(chats_list_path)

    for entry in entries:
        name_elem = entry.find("div", class_="name")
        details_elem = entry.find("div", class_="details_entry")
        href = entry.get("href", "")

        if not name_elem:
            continue

        name = name_elem.get_text(strip=True)
        msg_count = 0
        if details_elem:
            text = details_elem.get_text(strip=True)
            match = re.search(r"(\d+)\s+messages?", text)
            if match:
                msg_count = int(match.group(1))

        chat_path = ""
        if href:
            href_without_fragment = href.split("#")[0]
            chat_path = os.path.normpath(os.path.join(lists_dir, href_without_fragment))

        contacts.append({
            "name": name,
            "message_count": msg_count,
            "chat_path": chat_path,
            "is_group": 0
        })

    return contacts

def parse_messages_from_html(html_path: str) -> list:
    from bs4 import BeautifulSoup

    if not os.path.exists(html_path):
        return []

    with open(html_path, "r", encoding="utf-8") as f:
        html_content = f.read()

    soup = BeautifulSoup(html_content, "html.parser")

    messages = []
    message_divs = soup.find_all("div", class_=lambda x: x and "message" in x)

    last_sender = ""

    for msg_div in message_divs:
        msg_classes = msg_div.get("class", [])
        if "service" in msg_classes:
            continue

        from_name_elem = msg_div.find("div", class_="from_name")
        date_elem = msg_div.find("div", class_="date")
        text_elem = msg_div.find("div", class_="text")

        is_joined = "joined" in msg_classes

        sender = ""
        if from_name_elem:
            sender = from_name_elem.get_text(strip=True)
            last_sender = sender
        elif is_joined and last_sender:
            sender = last_sender

        date_text = ""
        if date_elem:
            date_text = date_elem.get("title", "")

        text_content = ""
        if text_elem:
            text_content = text_elem.get_text(strip=True)

        if text_content and sender:
            messages.append({
                "content": text_content,
                "timestamp": date_text,
                "sender": sender
            })

    return messages
