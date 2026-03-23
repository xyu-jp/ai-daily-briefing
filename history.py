"""
历史记录模块
跟踪已报道的文章 URL，避免跨天重复。
"""
import json
import os
from datetime import datetime, timezone, timedelta
import config


def load_history() -> dict:
    """加载历史记录。格式: {"url": "YYYY-MM-DD", ...}"""
    if not os.path.exists(config.HISTORY_FILE):
        return {}
    try:
        with open(config.HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[History] 加载失败: {e}")
        return {}


def save_history(history: dict):
    """保存历史记录，同时清理超过 HISTORY_DAYS 天的旧记录。"""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=config.HISTORY_DAYS)).strftime("%Y-%m-%d")
    # 只保留最近的记录
    cleaned = {url: date for url, date in history.items() if date >= cutoff}
    try:
        with open(config.HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(cleaned, f, ensure_ascii=False, indent=2)
        print(f"[History] 已保存 {len(cleaned)} 条记录（清理了 {len(history) - len(cleaned)} 条旧记录）")
    except Exception as e:
        print(f"[History] 保存失败: {e}")


def filter_new_articles(articles: list) -> list:
    """过滤掉已报道过的文章，只保留新内容。"""
    history = load_history()
    new_articles = []
    skipped = 0

    for art in articles:
        if art.url and art.url in history:
            skipped += 1
        else:
            new_articles.append(art)

    if skipped > 0:
        print(f"[History] 去重: 跳过 {skipped} 条已报道内容，保留 {len(new_articles)} 条新内容")
    else:
        print(f"[History] 全部 {len(new_articles)} 条都是新内容")

    return new_articles


def mark_as_reported(articles: list):
    """将文章标记为已报道。"""
    history = load_history()
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    for art in articles:
        if art.url:
            history[art.url] = today
    save_history(history)
