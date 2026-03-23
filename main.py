#!/usr/bin/env python3
"""
AI Daily Briefing - 主程序
每日自动采集 AI 领域最新进展，AI 筛选分析，生成中文简报 + 日本語HTML，推送并归档。

使用方法:
    python main.py              # 运行完整流程
    python main.py --collect    # 仅采集
    python main.py --dry-run    # 采集+分析，但不推送不归档
"""
import sys
import json
from datetime import datetime

from collector import collect_all
from analyzer import analyze
from notifier import notify
from archiver import archive_to_sheets
from history import filter_new_articles, mark_as_reported


def run(dry_run=False, collect_only=False):
    print("=" * 60)
    print(f"AI Daily Briefing - {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 60)

    # ── Step 1: 采集 ────────────────────────────────────────
    print("\n-- Step 1: 采集信息源...")
    articles = collect_all()

    if not articles:
        print("-- 今日未采集到任何内容，流程结束")
        return

    if collect_only:
        print(f"\n-- 采集完成，共 {len(articles)} 条内容")
        for a in articles[:10]:
            print(f"  - [{a.source}] {a.title[:60]}")
        return

    # ── Step 1.5: 去重 ──────────────────────────────────────
    print("\n-- Step 1.5: 去重（排除已报道内容）...")
    articles = filter_new_articles(articles)

    if not articles:
        print("-- 去重后没有新内容，流程结束")
        return

    # ── Step 2: AI 筛选 + 生成简报 ──────────────────────────
    print("\n-- Step 2: AI 分析与筛选...")
    filtered_articles, briefing, html_ja = analyze(articles)

    print("\n" + "-" * 40)
    print(briefing)
    print("-" * 40)

    if dry_run:
        print("\n-- Dry run 完成，不执行推送和归档")
        # dry-run 模式下也保存HTML供预览
        if html_ja:
            with open("briefing_ja.html", "w", encoding="utf-8") as f:
                f.write(html_ja)
            print("-- 日本語HTML已保存为 briefing_ja.html（可在浏览器中打开预览）")
        return

    # ── Step 3: 推送通知 ────────────────────────────────────
    print("\n-- Step 3: 推送简报...")
    notify_results = notify(briefing, filtered_articles, html_ja)
    for channel, ok in notify_results.items():
        status = "OK" if ok else "FAIL"
        print(f"  [{status}] {channel}")

    # ── Step 4: 归档到 Google Sheets ────────────────────────
    print("\n-- Step 4: 归档到 Google Sheets...")
    archive_ok = archive_to_sheets(filtered_articles, briefing)
    print(f"  {'OK' if archive_ok else 'SKIP'} Google Sheets")

    # ── Step 5: 标记为已报道 ────────────────────────────────
    print("\n-- Step 5: 更新历史记录...")
    mark_as_reported(filtered_articles)

    # ── 完成 ────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print(f"完成！筛选 {len(filtered_articles)}/{len(articles)} 条，已推送并归档")
    print("=" * 60)


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    collect_only = "--collect" in sys.argv
    run(dry_run=dry_run, collect_only=collect_only)
