"""
信息采集模块
从 arXiv、AI 公司博客 RSS、KOL 信息源采集最新 AI 内容。
"""
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field, asdict
from email.utils import parsedate_to_datetime
import urllib.request
import urllib.parse
import json
import time
import re
import config


@dataclass
class Article:
    """统一的文章数据结构"""
    title: str
    summary: str
    url: str
    source: str          # "arXiv" / "OpenAI" / etc.
    source_type: str     # "paper" / "blog" / "kol"
    published: str       # ISO format string
    authors: str = ""
    tags: list = field(default_factory=list)

    def to_dict(self):
        return asdict(self)


def _parse_date(date_str: str) -> datetime | None:
    """尝试解析各种日期格式，返回 aware datetime 或 None"""
    if not date_str or not date_str.strip():
        return None
    date_str = date_str.strip()

    # RFC 2822 格式 (RSS pubDate): "Mon, 23 Mar 2026 10:00:00 GMT"
    try:
        return parsedate_to_datetime(date_str)
    except Exception:
        pass

    # ISO 8601 格式 (Atom): "2026-03-23T10:00:00Z"
    try:
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        pass

    return None


def _is_recent(date_str: str, max_days: int = 7) -> bool:
    """判断日期是否在最近 max_days 天内。无法解析时默认保留。"""
    dt = _parse_date(date_str)
    if dt is None:
        return True  # 无法解析日期时保留，交给 AI 筛选
    cutoff = datetime.now(timezone.utc) - timedelta(days=max_days)
    return dt >= cutoff


# AI 相关关键词（用于过滤综合性新闻源中的非 AI 内容）
_AI_KEYWORDS = [
    # English
    "ai", "artificial intelligence", "machine learning", "deep learning",
    "llm", "gpt", "claude", "gemini", "chatgpt", "openai", "anthropic",
    "neural", "transformer", "diffusion", "generative", "agent",
    "robot", "autonomous", "nlp", "computer vision", "rag",
    "fine-tune", "training", "inference", "model", "embedding",
    "deepmind", "hugging face", "nvidia", "gpu",
    # Chinese
    "人工智能", "大模型", "机器学习", "深度学习", "智能体",
    "具身智能", "机器人", "自动驾驶", "算力", "芯片",
    "大语言模型", "多模态", "生成式", "智能", "AI",
]

# 需要关键词过滤的综合性新闻源（专门的 AI 源不需要过滤）
_GENERAL_SOURCES = {"36Kr", "MIT Tech Review AI", "STAT News AI", "The Verge AI", "Hacker News AI", "InfoQ AI"}


def _is_ai_related(title: str, summary: str) -> bool:
    """判断文章是否与 AI 相关"""
    text = (title + " " + summary).lower()
    return any(kw in text for kw in _AI_KEYWORDS)


def fetch_arxiv_papers() -> list[Article]:
    """从 arXiv API 获取最新 AI 论文"""
    articles = []
    categories = " OR ".join(f"cat:{c}" for c in config.ARXIV_CATEGORIES)
    query = urllib.parse.quote(categories)
    url = (
        f"http://export.arxiv.org/api/query?"
        f"search_query={query}"
        f"&sortBy=submittedDate&sortOrder=descending"
        f"&max_results={config.ARXIV_MAX_RESULTS}"
    )

    try:
        print(f"[Collector] 正在获取 arXiv 论文...")
        req = urllib.request.Request(url, headers={"User-Agent": "AI-Daily-Briefing/1.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = resp.read().decode("utf-8")

        # arXiv 返回 Atom XML
        ns = {
            "atom": "http://www.w3.org/2005/Atom",
            "arxiv": "http://arxiv.org/schemas/atom",
        }
        root = ET.fromstring(data)
        cutoff = config.get_lookback_time()

        for entry in root.findall("atom:entry", ns):
            published_str = entry.findtext("atom:published", "", ns)
            if published_str:
                pub_dt = datetime.fromisoformat(published_str.replace("Z", "+00:00"))
                if pub_dt.replace(tzinfo=None) < cutoff:
                    continue

            title = entry.findtext("atom:title", "", ns).strip().replace("\n", " ")
            summary = entry.findtext("atom:summary", "", ns).strip().replace("\n", " ")
            link = ""
            for lnk in entry.findall("atom:link", ns):
                if lnk.get("type") == "text/html":
                    link = lnk.get("href", "")
                    break
            if not link:
                link = entry.findtext("atom:id", "", ns)

            authors = ", ".join(
                a.findtext("atom:name", "", ns)
                for a in entry.findall("atom:author", ns)
            )

            categories = [
                c.get("term", "")
                for c in entry.findall("atom:category", ns)
            ]

            articles.append(Article(
                title=title,
                summary=summary[:500],
                url=link,
                source="arXiv",
                source_type="paper",
                published=published_str,
                authors=authors,
                tags=categories,
            ))

        print(f"[Collector] arXiv: 获取到 {len(articles)} 篇论文")
    except Exception as e:
        print(f"[Collector] arXiv 获取失败: {e}")

    return articles


def fetch_rss_feed(name: str, feed_url: str, source_type: str) -> list[Article]:
    """通用 RSS/Atom feed 解析器（只保留最近7天的内容）"""
    articles = []
    try:
        req = urllib.request.Request(
            feed_url,
            headers={"User-Agent": "AI-Daily-Briefing/1.0"}
        )
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = resp.read().decode("utf-8", errors="replace")

        root = ET.fromstring(data)

        # --- RSS 2.0 ---
        for item in root.findall(".//item"):
            title = (item.findtext("title") or "").strip()
            link = (item.findtext("link") or "").strip()
            desc = (item.findtext("description") or "").strip()
            pub_date = item.findtext("pubDate") or ""

            # 日期过滤：只保留最近7天
            if not _is_recent(pub_date, max_days=7):
                continue

            desc = re.sub(r"<[^>]+>", "", desc)[:500]

            articles.append(Article(
                title=title,
                summary=desc,
                url=link,
                source=name,
                source_type=source_type,
                published=pub_date,
            ))

        # --- Atom ---
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        for entry in root.findall("atom:entry", ns):
            title = (entry.findtext("atom:title", "", ns)).strip()
            link = ""
            for lnk in entry.findall("atom:link", ns):
                href = lnk.get("href", "")
                if lnk.get("rel", "alternate") == "alternate" or not link:
                    link = href
            summary = (entry.findtext("atom:summary", "", ns) or
                       entry.findtext("atom:content", "", ns) or "").strip()
            summary = re.sub(r"<[^>]+>", "", summary)[:500]
            published = entry.findtext("atom:published", "", ns) or entry.findtext("atom:updated", "", ns) or ""

            # 日期过滤：只保留最近7天
            if not _is_recent(published, max_days=7):
                continue

            articles.append(Article(
                title=title,
                summary=summary,
                url=link,
                source=name,
                source_type=source_type,
                published=published,
            ))

    except Exception as e:
        print(f"[Collector] {name} RSS 获取失败: {e}")

    # 每个源最多保留 MAX_PER_SOURCE 条，取最新的
    if len(articles) > config.MAX_PER_SOURCE:
        articles = articles[:config.MAX_PER_SOURCE]

    print(f"[Collector] {name}: 获取到 {len(articles)} 条内容（最近7天）")
    return articles


def collect_all() -> list[Article]:
    """
    汇总所有信息源，返回统一格式的文章列表。
    """
    all_articles = []

    # 1. arXiv 论文
    all_articles.extend(fetch_arxiv_papers())

    # 2. AI 公司博客
    for name, url in config.BLOG_FEEDS.items():
        arts = fetch_rss_feed(name, url, "blog")
        all_articles.extend(arts)
        time.sleep(1)  # 礼貌延迟

    # 3. KOL 信息源
    for name, url in config.KOL_FEEDS.items():
        arts = fetch_rss_feed(name, url, "kol")
        all_articles.extend(arts)
        time.sleep(1)

    # 去重（按 URL）
    seen_urls = set()
    unique = []
    for art in all_articles:
        if art.url and art.url not in seen_urls:
            seen_urls.add(art.url)
            unique.append(art)

    # 综合性新闻源：过滤掉非 AI 相关内容
    filtered = []
    removed = 0
    for art in unique:
        if art.source in _GENERAL_SOURCES and not _is_ai_related(art.title, art.summary):
            removed += 1
        else:
            filtered.append(art)

    if removed > 0:
        print(f"[Collector] AI 关键词过滤: 移除 {removed} 条非 AI 内容")

    print(f"\n[Collector] 总计采集到 {len(filtered)} 条不重复内容")
    return filtered


if __name__ == "__main__":
    results = collect_all()
    for a in results[:5]:
        print(f"\n--- {a.source} ---")
        print(f"Title: {a.title}")
        print(f"URL: {a.url}")
        print(f"Summary: {a.summary[:100]}...")
