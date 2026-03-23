"""
AI Daily Briefing - 配置文件
所有 API Key 和配置通过环境变量读取，不要硬编码。
"""
import os
from datetime import datetime, timedelta

# ── OpenAI API (ChatGPT) ───────────────────────────────────
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
# gpt-4o-mini: 最便宜，每天 < $0.01，质量够用（推荐日常使用）
# gpt-4o:      质量更高，每天约 $0.05-0.10

# ── 信息源配置 ──────────────────────────────────────────────
# arXiv 搜索关键词（用 OR 连接）
ARXIV_CATEGORIES = ["cs.AI", "cs.CL", "cs.LG", "cs.CV", "q-bio.NC"]
# q-bio.NC = 计算神经科学（覆盖AI+认知症/脑科学研究）
ARXIV_MAX_RESULTS = 30

# 每个信息源最多保留的条目数（防止某个源数量压倒其他源）
MAX_PER_SOURCE = 15

# AI 公司博客 RSS / Atom feeds
BLOG_FEEDS = {
    "OpenAI": "https://openai.com/blog/rss.xml",
    "Google DeepMind": "https://deepmind.google/blog/rss.xml",
    "Google AI Blog": "https://blog.google/technology/ai/rss/",
    "Meta AI Research": "https://engineering.fb.com/category/ml-applications/feed/",
    "Hugging Face": "https://huggingface.co/blog/feed.xml",
    "Microsoft AI": "https://blogs.microsoft.com/ai/feed/",
    "NVIDIA AI": "https://blogs.nvidia.com/feed/",
}
# 注: Anthropic, Mistral AI 的 RSS 已失效(404)，暂时移除
# 注: Anthropic, Mistral AI 的 RSS 已失效(404)，暂时移除

# AI KOL / Newsletter / 独立博客
KOL_FEEDS = {
    # ── Newsletter（稳定、高质量）──
    "Import AI (Jack Clark)": "https://jack-clark.net/feed/",
    "Ahead of AI (Sebastian Raschka)": "https://magazine.sebastianraschka.com/feed",
    "Interconnects (Nathan Lambert)": "https://www.interconnects.ai/feed",

    # ── 技术博客（深度分析）──
    "Simon Willison": "https://simonwillison.net/atom/everything/",
    "Lilian Weng (OpenAI)": "https://lilianweng.github.io/index.xml",
    "Chip Huyen": "https://huyenchip.com/feed.xml",
    "Jay Alammar": "https://jalammar.github.io/feed.xml",
    "Eugene Yan": "https://eugeneyan.com/rss/",
    "Andrej Karpathy": "https://karpathy.github.io/feed.xml",

    # ── 社区/聚合（间接覆盖 Jim Fan, Thariq 等 X-based KOL 的讨论）──
    "DAIR.AI (Elvis Saravia)": "https://github.com/dair-ai/ml-papers-of-the-week/commits/main.atom",
    "Hacker News AI": "https://hnrss.org/newest?q=AI+OR+LLM+OR+GPT+OR+Claude&points=50",
    "MIT Tech Review AI": "https://www.technologyreview.com/feed/",
    "The Verge AI": "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml",

    # ── 中国 AI 信息源 ──
    "量子位": "https://www.qbitai.com/feed",
    "36Kr": "https://36kr.com/feed",
    "Synced Review (机器之心英文版)": "https://syncedreview.com/feed",
    "InfoQ AI": "https://www.infoq.cn/feed/topic/AI",

    # ── AI × 医疗/认知症 ──
    "Ground Truths (Eric Topol)": "https://erictopol.substack.com/feed",
    "Pranav Rajpurkar": "https://pranavrajpurkar.substack.com/feed",
    "Google Health AI": "https://blog.google/technology/health/rss/",
    "STAT News AI": "https://www.statnews.com/feed/",
    "Nature Digital Medicine": "https://www.nature.com/npjdigitalmed.rss",

    # -- 学术机构 / 李飞飞 --
    "Fei-Fei Li (Substack)": "https://drfeifei.substack.com/feed",
    "World Labs (Fei-Fei Li)": "https://www.worldlabs.ai/blog/rss.xml",
    "Google Research": "https://research.google/blog/rss",
    "Stanford AI Lab (SAIL)": "https://ai.stanford.edu/blog/feed.xml",
}

# ── 推送配置 ──────────────────────────────────────────────
# Slack 中文版（Block Kit）
SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL", "")
SLACK_ENABLED = bool(SLACK_WEBHOOK_URL)

# Slack 日本語版（HTML）— 別チャンネルへ送信
SLACK_WEBHOOK_URL_JA = os.environ.get("SLACK_WEBHOOK_URL_JA", "")
SLACK_JA_ENABLED = bool(SLACK_WEBHOOK_URL_JA)

# Telegram Bot
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
TELEGRAM_ENABLED = bool(TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID)

# ── Google Sheets 归档 ─────────────────────────────────────
# 需要 Service Account JSON 文件路径
GOOGLE_CREDENTIALS_FILE = os.environ.get(
    "GOOGLE_CREDENTIALS_FILE", "credentials.json"
)
GOOGLE_SHEET_ID = os.environ.get("GOOGLE_SHEET_ID", "")

# ── 时间设置 ────────────────────────────────────────────────
LOOKBACK_HOURS = 28  # 稍多于24h，避免遗漏

# ── 去重设置 ────────────────────────────────────────────────
HISTORY_FILE = os.environ.get("HISTORY_FILE", "history.json")
HISTORY_DAYS = 14  # 保留最近14天的历史记录

def get_lookback_time():
    return datetime.utcnow() - timedelta(hours=LOOKBACK_HOURS)
