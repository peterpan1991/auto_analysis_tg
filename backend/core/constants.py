from pathlib import Path

DEFAULT_MODEL = "qwen2.5:7b"
EMBEDDING_MODEL = "shaw/dmeta-embedding-zh"
CHUNK_SIZE = 200
MAX_WORKERS = 3
MAX_CONTENT_LENGTH = 200
DEFAULT_USER_ID = 1

MAX_ITEMS_PER_SUB_REDUCE = 30
MAX_CHARS_PER_ITEM = 200
MAX_DAYS_FOR_ANALYSIS = 365
LIMIT_MESSAGE_COUNT = 50

VECTOR_DB_PATH = str(Path(__file__).resolve().parents[1] / "vector_db")

EMBEDDING_CHUNK_SIZE = 20
EMBEDDING_OVERLAP_SIZE = 2
EMBEDDING_MAX_CHARS = 800
EMBEDDING_TIME_GAP_SECONDS = 7200
EMBEDDING_BATCH_SIZE = 32
EMBEDDING_CHROMA_BATCH_SIZE = 200

RAG_MIN_SIMILARITY = 0.5
RAG_FINAL_TOP_K = 3
RAG_CANDIDATE_TOP_K = 10

IGNORE_WORDS = ("好的", "嗯", "是的", "是", "好", "稍等", "对", "1", "OK", "收到")

RESULT_TYPES = ["person_info", "org_structure", "fund_flow", "chat_topics", "location_info"]

WATER_PATTERNS = [
    r'^(.)\1+$',
]

INFO_PATTERNS = {
    'phone': [
        r'(?<!\d)1[3-9]\d{9}(?!\d)',
        r'(?<!\d)\+86\s*1[3-9]\d{9}(?!\d)',
        r'(?<=[：:\s、,，])1[3-9]\d{9}(?=[：:\s、,，]|$)',
    ],
    'id_card': [
        r'[1-9]\d{5}(18|19|20)\d{2}(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])\d{3}[\dXx]',
    ],
    'car_plate': [
        r'[京津沪渝冀豫云辽黑湘皖鲁新苏浙赣鄂桂甘晋蒙陕吉闽贵粤青藏川宁琼使领][A-Z][A-Z0-9]{4,5}[A-Z0-9挂学警港澳]',
    ],
    'bank_card': [
        r'(?<!\d)(?:62[0-9]{14,17}|4[0-9]{12,15}|5[1-5][0-9]{14}|9[0-9]{15,18})(?!\d)',
    ],
    'express': [
        r'(?:SF|顺丰)[0-9]{12,15}',
        r'(?:YT|韵达)[0-9]{12,13}',
        r'(?:ZTO|中通)[0-9]{12}',
        r'(?:YTO|圆通)[0-9]{12,13}',
        r'(?:EMS)[0-9]{13}',
        r'(?:JD|京东)[0-9]{12,15}',
        r'(?:SF|顺丰|YT|韵达|ZTO|中通|YTO|圆通|EMS|JD|京东|天天|TT)[0-9]{10,15}',
        r'\d{10,15}(?:快件|单号|快递)',
    ],
    'email': [
        r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
    ],
    'virtual_account': [
        r'QQ[：:\s]*(\d{5,11})',
        r'微信[：:\s]*([\w-]{6,20})',
        r'TG[：:\s]*@(\w{5,32})',
        r' telegram[：:\s]*@(\w{5,32})',
    ],
    'password': [
        r'密码[：:\s]*([^\s]{6,20})',
        r'pwd[：:\s]*([^\s]{6,20})',
        r'pass[：:\s]*([^\s]{6,20})',
    ],
    'url': [
        r'https?://[^\s<>"{}|\\^`\[\]]+',
    ],
    'domain': [
        r'(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}',
    ],
}

ADDRESS_KEYWORDS = [
    '省', '市', '区', '县', '街道', '栋', '楼', '室',
    '村', '镇', '乡', '开发区', '园区', '大厦', '广场', '中心'
]

LOG_DIR = "logs"

RAG_RECENT_MESSAGE_LIMIT = 50
