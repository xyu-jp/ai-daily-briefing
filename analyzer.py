"""
AI 分析模块
使用 ChatGPT API 对采集到的内容进行筛选、分析，并生成中文简报。
"""
import json
import urllib.request
import urllib.error
import config
from collector import Article


def call_chatgpt(system_prompt: str, user_prompt: str, max_tokens: int = 4096, model: str = None) -> str:
    """调用 OpenAI ChatGPT API"""
    use_model = model or config.OPENAI_MODEL
    payload = json.dumps({
        "model": use_model,
        "max_tokens": max_tokens,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {config.OPENAI_API_KEY}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return data["choices"][0]["message"]["content"]
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8", errors="replace")
        print(f"[API] {use_model} HTTP {e.code}: {error_body[:500]}")
        raise


def filter_articles(articles: list[Article]) -> list[Article]:
    """
    第一步: 用 ChatGPT 判断哪些文章具有创新性，值得纳入简报。
    """
    if not articles:
        return []

    system_prompt = """你是一位资深 AI 行业分析师，为一位 AI 产品负责人筛选每日信息。
你的目标是从大量内容中挑出真正值得花时间阅读的条目。

═══ 入选标准（满足任意一条即可入选）═══

1. 新架构/新方法: 提出了新的模型架构、训练方法或推理策略，且有明显的性能提升或效率改善
2. 重要产品发布: 主要 AI 公司的新模型上线、API 能力重大变化、定价策略调整
3. 降低门槛的工具: 新的 no-code/low-code AI 开发工具、框架，让非工程师也能构建 AI 应用
4. Agent/RAG/多模态进展: AI Agent 架构、检索增强生成、多模态能力的实质性突破
5. 落地案例与洞察: 有数据支撑的行业应用案例，或对 AI 产品策略有启发的深度分析
6. AI×医疗/认知症: AI 在医疗诊断、药物发现、认知症(dementia/Alzheimer's)检测与护理方面的进展
7. 政策与监管: 影响 AI 产品方向的重要政策、法规变化或安全研究

═══ 排除标准（满足任意一条即排除）═══

1. 微小改进: SOTA 提升不到 2%、已知方法的参数微调
2. 纯综述: 没有新见解的文献回顾
3. 营销内容: 产品宣传、客户案例故事、合作公告等没有技术实质的内容
4. 重复报道: 多个来源报道同一事件，只保留信息最丰富的那条
5. 常规更新: 版本号升级、bug修复、小功能迭代

═══ 多样性要求（非常重要，必须严格遵守）═══

1. 每个来源（source）最多选择 3 条
2. 必须覆盖以下全部类别（每个类别至少选 1 条，如果该类别有内容的话）：
   - 欧美 AI 公司动态（OpenAI, Google, Meta, NVIDIA 等）
   - 中国 AI 动态（量子位、机器之心等中文来源）
   - KOL/独立博客（Simon Willison, Jack Clark, Sebastian Raschka 等）
   - AI×医疗（STAT News, Eric Topol, Google Health, Nature Digital Medicine 等）
   - 学术论文（arXiv）
3. 如果某个类别没有值得入选的内容，可以跳过，但绝不能让某一类别完全占据结果

请返回 JSON，格式: {"selected": [0, 2, 5]}
只输出 JSON，不要其他文字。"""

    article_list = []
    for i, art in enumerate(articles):
        article_list.append(
            f"[{i}] 来源: {art.source} | 类型: {art.source_type}\n"
            f"    标题: {art.title}\n"
            f"    摘要: {art.summary[:300]}"
        )

    selected_indices = set()
    batch_size = 20

    for start in range(0, len(articles), batch_size):
        batch = article_list[start:start + batch_size]
        user_prompt = (
            f"以下是今天采集到的第 {start} 到 {start + len(batch) - 1} 条 AI 相关内容，"
            f"请按筛选标准选出值得关注的：\n\n" + "\n\n".join(batch)
        )

        try:
            result = call_chatgpt(system_prompt, user_prompt, max_tokens=500)
            result = result.strip()
            if result.startswith("```"):
                result = result.split("\n", 1)[-1].rsplit("```", 1)[0]
            parsed = json.loads(result)
            indices = parsed.get("selected", [])
            for idx in indices:
                global_idx = start + idx
                if 0 <= global_idx < len(articles):
                    selected_indices.add(global_idx)
        except Exception as e:
            print(f"[Analyzer] 筛选批次 {start} 失败: {e}")
            for idx in range(start, min(start + batch_size, len(articles))):
                selected_indices.add(idx)

    filtered = [articles[i] for i in sorted(selected_indices)]
    print(f"[Analyzer] 筛选结果: {len(articles)} → {len(filtered)} 条")
    return filtered


def generate_briefing(articles: list[Article]) -> str:
    """
    第二步: 基于筛选后的文章，生成中文简报。
    """
    if not articles:
        return "今日暂无值得关注的 AI 新进展。"

    system_prompt = """你是一位 AI 行业分析师，为一位在日本工作的中英双语技术产品负责人撰写每日简报。

语言规则：
- 标题：英文来源保留英文原标题；中文来源的文章标题翻译成日文
- 来源名称（Source名）：保持原样不翻译。量子位、36Kr、机器之心等是固有名词/品牌名
- 正文说明：用通俗易懂的中文撰写
- 专业术语：首次出现时保留英文并用中文括号解释，如 RAG（检索增强生成）、Agent（智能体）
- 今日概览：用中文

** 最重要的规则：
提供给你的所有文章都已经过预筛选，每一条都必须出现在简报中，不得遗漏任何一条。
你的任务是撰写说明，而不是再次筛选。

写作要求：
1. 每条内容要回答两个问题：「这是什么」和「为什么重要（对比过去有何创新/启示）」
2. 按重要性排序，最重要的放最前面
3. 每条末尾附上原文链接
4. 整体 3000 字以内
5. 开头一句话总结今天的整体趋势或亮点
6. 发布日期：只标注年月日（不需要具体时间），换算为日本时间(JST)的日期。格式如：2026/3/17 (JST)
7. 每条标注领域标签和地区标签

领域标签（选一个最匹配的）：
[AI研究] [产品发布] [Agent/自动化] [AI×医疗] [AI落地应用] [开源/工具] [安全/政策] [行业动态]

地区标签：
[美国] [中国] [欧洲] [全球/其他]

输出格式（纯文本，不使用任何表情符号或emoji）：

AI Daily Briefing - [日期]

[Today's Overview]
・Global: 全球AI动态一句话概述（如果当天无相关内容则写「特になし」）
・China: 中国AI动态一句话概述（同上）
・AI×Healthcare: AI医疗领域一句话概述（同上）
・KOL/Research: KOL观点或学术研究一句话概述（同上）

[1] [标题] | [产品发布] | [美国]
Source: [来源名] | [YYYY/M/D (JST)]
[2-3句中文说明 + 创新点/启示分析]
链接: URL

[2] [标题] | [AI×医疗] | [美国]
Source: [来源名] | [YYYY/M/D (JST)]
...

---
Generated by AI Daily Briefing"""

    article_details = []
    for art in articles:
        article_details.append(
            f"来源: {art.source} ({art.source_type})\n"
            f"标题: {art.title}\n"
            f"发布日期: {art.published}\n"
            f"作者: {art.authors}\n"
            f"链接: {art.url}\n"
            f"摘要: {art.summary}\n"
            f"标签: {', '.join(art.tags)}"
        )

    user_prompt = (
        f"以下是今天筛选出的 {len(articles)} 条 AI 相关内容，请为每一条都撰写简报说明（不得遗漏）：\n\n"
        + "\n---\n".join(article_details)
    )

    try:
        briefing = call_chatgpt(system_prompt, user_prompt, max_tokens=8000)
        return briefing
    except Exception as e:
        print(f"[Analyzer] 简报生成失败: {e}")
        lines = ["AI Daily Briefing (自动生成失败，以下为原始列表)\n"]
        for i, art in enumerate(articles, 1):
            lines.append(f"{i}. {art.title}\n   链接: {art.url}\n")
        return "\n".join(lines)


def _enforce_diversity(articles: list[Article], max_per_source: int = 5) -> list[Article]:
    """确保来源多样性：每个 source 最多保留 max_per_source 条"""
    source_count = {}
    result = []
    for art in articles:
        count = source_count.get(art.source, 0)
        if count < max_per_source:
            result.append(art)
            source_count[art.source] = count + 1
    return result


# 来源分类映射
_CATEGORY_MAP = {
    "中国AI": ["量子位", "36Kr", "Synced Review (机器之心英文版)", "InfoQ AI"],
    "AI医疗": ["Ground Truths (Eric Topol)", "Pranav Rajpurkar",
              "Google Health AI", "STAT News AI", "Nature Digital Medicine"],
    "KOL/博客": ["Simon Willison", "Import AI (Jack Clark)",
                "Ahead of AI (Sebastian Raschka)", "Interconnects (Nathan Lambert)",
                "Lilian Weng (OpenAI)", "Chip Huyen", "Jay Alammar",
                "Eugene Yan", "Andrej Karpathy"],
    "学术论文": ["arXiv", "Google Research", "Stanford AI Lab (SAIL)",
               "Fei-Fei Li (Substack)", "World Labs (Fei-Fei Li)"],
}


def _get_category(source: str) -> str:
    for cat, sources in _CATEGORY_MAP.items():
        if source in sources:
            return cat
    return "AI公司/综合"


def _ensure_category_coverage(all_articles: list[Article], filtered: list[Article]) -> list[Article]:
    """
    检查筛选结果是否覆盖了各个类别。
    如果某个类别完全缺失，从原始采集中补充该类别最新的 2 条。
    """
    # 统计筛选结果中各类别的覆盖
    covered_cats = set()
    for art in filtered:
        covered_cats.add(_get_category(art.source))

    # 找出缺失的类别
    missing_cats = set(_CATEGORY_MAP.keys()) - covered_cats

    if not missing_cats:
        return filtered

    # 从原始采集中补充缺失类别
    added = []
    for cat in missing_cats:
        cat_sources = _CATEGORY_MAP[cat]
        candidates = [a for a in all_articles if a.source in cat_sources]
        added.extend(candidates[:2])  # 每个缺失类别补 2 条
        if candidates:
            print(f"[Analyzer] 补充类别 [{cat}]: +{min(2, len(candidates))} 条")

    return filtered + added


def generate_briefing_ja(articles: list[Article]) -> str:
    """日本語版ブリーフィングを生成（JSON形式で返してもらいHTMLに変換）"""
    if not articles:
        return ""

    system_prompt = """あなたはAI業界アナリストです。日本で働く技術プロダクト責任者向けに、毎日のAIブリーフィングを作成してください。

言語ルール：
- タイトル：英語の原題をそのまま使用。中国語ソースの場合は記事タイトルを必ず日本語に翻訳する（中国語のまま残すのは禁止）
  例：
  ✕「寻找最强具身大脑！全球机器人顶会ICRA开启报名」（中国語のまま＝NG）
  ○「最強の具身知能を探せ！ロボット工学トップ国際会議ICRAが参加受付開始」（日本語に翻訳＝OK）
  ✕「元气森林在河南新设饮料公司」（中国語のまま＝NG）
  ○ このような非AI記事はそもそも含めないが、もし含まれていたら日本語に翻訳すること
- 本文：日本語で分かりやすく解説。中国語ソースの場合も必ず日本語に翻訳する（中国語のまま残すのは禁止）
- 重要：最終出力に中国語の文章が含まれていてはいけません。タイトルも本文もすべて日本語に翻訳してください。中国語が1文字でも残っていたら失格です。
- ソース名（Source名）：量子位、36Kr、机器之心などの媒体名・ブランド名は翻訳せずそのまま使用する（固有名詞のため）。ただし、日本人に馴染みのない固有名詞は初出時にカッコで簡潔に説明を付ける。例：
  量子位（中国大手AIメディア）
  36Kr（中国最大級のテック・スタートアップメディア）
  Synced Review（机器之心の英語版メディア）
  STAT News（米国の医療・バイオテック専門メディア）
  DAIR.AI（AI論文の週間まとめを発信するコミュニティ）
  Ground Truths（Eric Topol氏のAI×医療ニュースレター）
- 専門用語：初出時に英語と日本語の両方を記載（例：RAG（検索拡張生成））

重要なルール：
提供されたすべての記事は事前にフィルタリング済みです。すべての記事をブリーフィングに含めてください。一つも省略しないでください。

各記事について以下をJSON配列で返してください：
- title: 原題
- tag: AI研究 / 製品リリース / Agent・自動化 / AI×医療 / AI実用化 / OSS・ツール / 安全・政策 / 業界動向 のいずれか
- region: 米国 / 中国 / 欧州 / グローバル のいずれか
- source: ソース名
- date_jst: JST換算後の日付（年月日のみ、時刻不要。例：2026/3/17）
- body: 4-6文の詳しい日本語解説。以下を必ず含めること：(1)具体的に何が発表・発見されたか (2)従来の手法や製品と比べて何が新しいか (3)業界や実務にどのようなインパクトがあるか。技術的な内容も分かりやすく噛み砕いて説明する。
- url: 元記事のURL

以下の形式でJSONのみを返してください（他のテキストは不要）：
{"overview": {"global": "グローバルAI動向の一文要約（該当なしなら'特になし'）", "china": "中国AI動向の一文要約", "medical": "AI×医療の一文要約", "research": "KOL・学術研究の一文要約"}, "items": [...]}"""

    article_details = []
    for art in articles:
        article_details.append(
            f"Source: {art.source} ({art.source_type})\n"
            f"Title: {art.title}\n"
            f"Published: {art.published}\n"
            f"Authors: {art.authors}\n"
            f"URL: {art.url}\n"
            f"Summary: {art.summary}\n"
            f"Tags: {', '.join(art.tags)}"
        )

    user_prompt = (
        f"以下の{len(articles)}件のAI関連記事について、すべてブリーフィングを作成してください：\n\n"
        + "\n---\n".join(article_details)
    )

    try:
        # 日本語版は翻訳品質を確保するため gpt-4o を使用
        result = call_chatgpt(system_prompt, user_prompt, max_tokens=4096, model="gpt-4o")
        print("[Analyzer] 日本語版: gpt-4o を使用")
        # Clean JSON
        result = result.strip()
        if result.startswith("```"):
            result = result.split("\n", 1)[-1].rsplit("```", 1)[0]
        return result
    except Exception as e:
        print(f"[Analyzer] 日本語ブリーフィング生成失敗: {e}")
        return ""


def _contains_chinese(text: str) -> bool:
    """テキストに中国語の漢字が含まれているかチェック（日本語の漢字と区別）"""
    if not text:
        return False
    # 中国語特有の簡体字範囲 + よく使われる中国語表現のパターン
    import unicodedata
    chinese_chars = 0
    total_cjk = 0
    for ch in text:
        if '\u4e00' <= ch <= '\u9fff':
            total_cjk += 1
            # ひらがな・カタカナが同じ文に含まれていれば日本語と判定
        if '\u3040' <= ch <= '\u30ff':
            return False  # 日本語のかな文字があれば中国語ではない
    # CJK文字が多く、かな文字がゼロなら中国語の可能性が高い
    return total_cjk >= 3


def _force_translate_chinese(items: list[dict]) -> list[dict]:
    """中国語が残っているタイトル・本文を強制的に日本語に翻訳"""
    to_translate = []
    indices = []

    for i, item in enumerate(items):
        title = item.get("title", "")
        body = item.get("body", "")
        if _contains_chinese(title) or _contains_chinese(body):
            to_translate.append({"index": i, "title": title, "body": body})
            indices.append(i)

    if not to_translate:
        return items

    print(f"[Analyzer] 中国語検出: {len(to_translate)}件を強制翻訳中...")

    prompt = """以下のJSON配列の各要素のtitleとbodyを日本語に翻訳してください。
固有名詞（量子位、36Kr、InfoQ等の媒体名）はそのまま残してください。
JSONのみを返してください。"""

    user_msg = json.dumps(to_translate, ensure_ascii=False)

    try:
        result = call_chatgpt(prompt, user_msg, max_tokens=4000, model="gpt-4o")
        result = result.strip()
        if result.startswith("```"):
            result = result.split("\n", 1)[-1].rsplit("```", 1)[0]
        translated = json.loads(result)

        for t in translated:
            idx = t.get("index")
            if idx is not None and idx < len(items):
                if t.get("title") and not _contains_chinese(t["title"]):
                    items[idx]["title"] = t["title"]
                if t.get("body") and not _contains_chinese(t["body"]):
                    items[idx]["body"] = t["body"]

        print(f"[Analyzer] 強制翻訳完了")
    except Exception as e:
        print(f"[Analyzer] 強制翻訳失敗: {e}")

    return items


def render_html(ja_json: str, articles: list[Article]) -> str:
    """JSON形式の日本語ブリーフィングをHTMLに変換"""
    from datetime import datetime as dt

    today = dt.now().strftime("%Y年%m月%d日")

    # Parse JSON
    try:
        data = json.loads(ja_json)
        overview_raw = data.get("overview", "")
        items = data.get("items", [])
        # 中国語が残っている場合は強制翻訳
        items = _force_translate_chinese(items)
    except Exception:
        overview_raw = ""
        items = []
        for art in articles:
            items.append({
                "title": art.title,
                "tag": "業界動向",
                "region": "グローバル",
                "source": art.source,
                "date_jst": "",
                "body": art.summary[:200],
                "url": art.url,
            })

    # overview をHTML文字列に変換
    if isinstance(overview_raw, dict):
        overview_parts = []
        labels = {"global": "Global", "china": "China", "medical": "AI×Healthcare", "research": "KOL/Research"}
        for key, label in labels.items():
            text = overview_raw.get(key, "特になし")
            overview_parts.append(f"<b>{label}:</b> {_esc(text)}")
        overview_html = "<br>".join(overview_parts)
    elif overview_raw:
        overview_html = _esc(str(overview_raw))
    else:
        overview_html = "本日のAI動向まとめ"

    TAG_CLASSES = {
        "AI研究": "tag-research", "製品リリース": "tag-product",
        "Agent・自動化": "tag-agent", "Agent/自動化": "tag-agent",
        "AI×医療": "tag-medical", "AI実用化": "tag-app",
        "OSS・ツール": "tag-oss", "オープンソース/ツール": "tag-oss",
        "安全・政策": "tag-policy", "安全/ポリシー": "tag-policy",
        "業界動向": "tag-industry",
    }
    REGION_CLASSES = {
        "米国": "region-us", "中国": "region-cn",
        "欧州": "region-eu", "グローバル": "region-global",
    }

    cards_html = ""
    for i, item in enumerate(items, 1):
        tag = item.get("tag", "業界動向")
        region = item.get("region", "グローバル")
        tag_cls = TAG_CLASSES.get(tag, "tag-industry")
        region_cls = REGION_CLASSES.get(region, "region-global")
        url = item.get("url", "")
        # Fallback URL from articles list
        if not url and i <= len(articles):
            url = articles[i-1].url

        date_str = item.get("date_jst", "")

        cards_html += f"""
    <div class="card" style="animation-delay:{i*0.05}s">
      <div class="card-header">
        <span class="card-num">{i:02d}</span>
        <h2 class="card-title">{_esc(item.get("title", ""))}</h2>
      </div>
      <div class="card-meta">
        <span class="tag {tag_cls}">{_esc(tag)}</span>
        <span class="region {region_cls}">{_esc(region)}</span>
        <span class="card-source">{_esc(item.get("source", ""))}</span>
      </div>
      {"<div class='card-date'>" + _esc(date_str) + "</div>" if date_str else ""}
      <div class="card-body">{_esc(item.get("body", ""))}</div>
      {"<a class='card-link' href='" + _esc(url) + "' target='_blank'><svg viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2'><path d='M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6'/><polyline points='15 3 21 3 21 9'/><line x1='10' y1='14' x2='21' y2='3'/></svg>Read more</a>" if url else ""}
    </div>"""

    sources = sorted(set(item.get("source", "") for item in items))

    html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AI Daily Briefing - {today}</title>
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@300;400;500;700&family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
:root{{--bg:#0f1117;--surface:#1a1d27;--surface-hover:#222533;--border:#2a2d3a;--text:#e4e4e7;--text-muted:#8b8d98;--accent:#6c9cfc;--accent-dim:rgba(108,156,252,0.12)}}
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:'Noto Sans JP',sans-serif;background:var(--bg);color:var(--text);line-height:1.7;-webkit-font-smoothing:antialiased}}
.container{{max-width:780px;margin:0 auto;padding:40px 24px 80px}}
.header{{margin-bottom:40px;padding-bottom:32px;border-bottom:1px solid var(--border)}}
.header-date{{font-family:'IBM Plex Mono',monospace;font-size:13px;color:var(--accent);letter-spacing:2px;text-transform:uppercase;margin-bottom:12px}}
.header-title{{font-size:28px;font-weight:700;letter-spacing:-0.5px;margin-bottom:20px}}
.overview{{background:var(--accent-dim);border-left:3px solid var(--accent);padding:16px 20px;border-radius:0 8px 8px 0;font-size:15px}}
.overview-label{{font-family:'IBM Plex Mono',monospace;font-size:11px;color:var(--accent);letter-spacing:1px;text-transform:uppercase;margin-bottom:6px}}
.stats{{display:flex;gap:24px;margin-top:20px;flex-wrap:wrap}}
.stat{{font-family:'IBM Plex Mono',monospace;font-size:12px;color:var(--text-muted)}}
.stat strong{{color:var(--text);font-size:18px;display:block;margin-bottom:2px}}
.card{{background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:24px;margin-bottom:16px;transition:border-color .2s,background .2s;animation:fadeUp .4s ease both}}
.card:hover{{border-color:var(--accent);background:var(--surface-hover)}}
@keyframes fadeUp{{from{{opacity:0;transform:translateY(12px)}}to{{opacity:1;transform:translateY(0)}}}}
.card-header{{display:flex;align-items:flex-start;gap:12px;margin-bottom:12px}}
.card-num{{font-family:'IBM Plex Mono',monospace;font-size:13px;font-weight:500;color:var(--accent);background:var(--accent-dim);min-width:32px;height:32px;display:flex;align-items:center;justify-content:center;border-radius:8px;flex-shrink:0}}
.card-title{{font-size:16px;font-weight:700;flex:1;line-height:1.5}}
.card-meta{{display:flex;align-items:center;gap:8px;margin-bottom:12px;flex-wrap:wrap}}
.tag{{font-family:'IBM Plex Mono',monospace;font-size:11px;font-weight:500;padding:3px 10px;border-radius:100px;letter-spacing:.3px}}
.tag-research{{background:rgba(167,139,250,.15);color:#a78bfa}}.tag-product{{background:rgba(52,211,153,.15);color:#34d399}}.tag-agent{{background:rgba(249,115,22,.15);color:#f97316}}.tag-medical{{background:rgba(244,114,182,.15);color:#f472b6}}.tag-app{{background:rgba(250,204,21,.15);color:#facc15}}.tag-oss{{background:rgba(56,189,248,.15);color:#38bdf8}}.tag-policy{{background:rgba(239,68,68,.15);color:#ef4444}}.tag-industry{{background:rgba(148,163,184,.15);color:#94a3b8}}
.region{{font-family:'IBM Plex Mono',monospace;font-size:11px;font-weight:500;padding:3px 10px;border-radius:100px;border:1px solid}}
.region-us{{border-color:rgba(108,156,252,.3);color:#6c9cfc}}.region-cn{{border-color:rgba(239,68,68,.3);color:#ef4444}}.region-eu{{border-color:rgba(167,139,250,.3);color:#a78bfa}}.region-global{{border-color:rgba(52,211,153,.3);color:#34d399}}
.card-source{{font-family:'IBM Plex Mono',monospace;font-size:12px;color:var(--text-muted)}}
.card-body{{font-size:14px;line-height:1.8;margin-bottom:14px}}
.card-date{{font-family:'IBM Plex Mono',monospace;font-size:11px;color:var(--text-muted);margin-bottom:14px}}
.card-link{{display:inline-flex;align-items:center;gap:6px;font-family:'IBM Plex Mono',monospace;font-size:13px;color:var(--accent);text-decoration:none;padding:6px 14px;border:1px solid rgba(108,156,252,.3);border-radius:6px;transition:all .2s}}
.card-link:hover{{background:var(--accent-dim);border-color:var(--accent)}}
.card-link svg{{width:14px;height:14px}}
.footer{{margin-top:48px;padding-top:24px;border-top:1px solid var(--border);text-align:center}}
.footer p{{font-family:'IBM Plex Mono',monospace;font-size:12px;color:var(--text-muted)}}
@media(max-width:600px){{.container{{padding:24px 16px 60px}}.header-title{{font-size:22px}}.card{{padding:18px}}}}
</style>
</head>
<body>
<div class="container">
  <header class="header">
    <div class="header-date">{today}</div>
    <h1 class="header-title">AI Daily Briefing</h1>
    <div class="overview">
      <div class="overview-label">Today's Overview</div>
      {overview_html}
    </div>
    <div class="stats">
      <div class="stat"><strong>{len(items)}</strong>記事</div>
      <div class="stat"><strong>{len(sources)}</strong>ソース</div>
    </div>
  </header>
  <main>{cards_html}</main>
  <footer class="footer">
    <p>Generated by AI Daily Briefing</p>
    <p style="margin-top:4px">Sources: {' / '.join(sources)}</p>
  </footer>
</div>
</body>
</html>"""
    return html


def _esc(text: str) -> str:
    """HTML escape"""
    return (text or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def analyze(articles: list[Article]) -> tuple[list[Article], str, str]:
    """完整分析流程：筛选 + 多样性控制 + 类别覆盖 + 生成中文简报 + 日本語HTML"""
    print("\n[Analyzer] 开始 AI 筛选（ChatGPT）...")
    filtered = filter_articles(articles)

    # 1. 每个源最多 5 条
    filtered = _enforce_diversity(filtered, max_per_source=5)

    # 2. 确保各类别都有覆盖
    filtered = _ensure_category_coverage(articles, filtered)

    sources = {}
    categories = {}
    for art in filtered:
        sources[art.source] = sources.get(art.source, 0) + 1
        cat = _get_category(art.source)
        categories[cat] = categories.get(cat, 0) + 1
    print(f"[Analyzer] 来源分布: {sources}")
    print(f"[Analyzer] 类别分布: {categories}")

    # 3. 生成中文简报
    print("[Analyzer] 开始生成中文简报...")
    briefing = generate_briefing(filtered)
    print(f"[Analyzer] 中文简报完成 ({len(briefing)} 字符)")

    # 4. 生成日本語HTMLブリーフィング
    print("[Analyzer] 日本語HTMLブリーフィング生成中...")
    ja_json = generate_briefing_ja(filtered)
    html = ""
    if ja_json:
        html = render_html(ja_json, filtered)
        print(f"[Analyzer] 日本語HTML完成 ({len(html)} 字符)")
    else:
        print("[Analyzer] 日本語版生成失敗、スキップ")

    return filtered, briefing, html
