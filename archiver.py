"""
Google Sheets 归档模块
将每日筛选的文章和简报写入 Google Spreadsheet。

需要:
1. Google Cloud 项目中启用 Google Sheets API
2. 创建 Service Account 并下载 JSON 密钥文件
3. 将 Service Account 的邮箱添加为目标 Spreadsheet 的编辑者
"""
import json
import urllib.request
import time
from datetime import datetime
from collector import Article
import config

# ── Google Auth (Service Account) ───────────────────────────
_cached_token = {"token": "", "expires": 0}


def _get_access_token() -> str:
    """通过 Service Account JSON 获取 OAuth2 access token"""
    now = time.time()
    if _cached_token["token"] and _cached_token["expires"] > now + 60:
        return _cached_token["token"]

    try:
        import google.auth
        from google.oauth2 import service_account

        creds = service_account.Credentials.from_service_account_file(
            config.GOOGLE_CREDENTIALS_FILE,
            scopes=["https://www.googleapis.com/auth/spreadsheets"],
        )
        creds.refresh(google.auth.transport.requests.Request())
        _cached_token["token"] = creds.token
        _cached_token["expires"] = now + 3500
        return creds.token
    except ImportError:
        print("[Archiver] 需要安装 google-auth: pip install google-auth")
        raise
    except Exception as e:
        print(f"[Archiver] 认证失败: {e}")
        raise


def _sheets_api(method: str, url: str, body: dict = None) -> dict:
    """调用 Google Sheets API"""
    token = _get_access_token()
    data = json.dumps(body).encode("utf-8") if body else None
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method=method,
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _ensure_sheet_exists(sheet_name: str):
    """确保工作表存在，不存在则创建"""
    url = f"https://sheets.googleapis.com/v4/spreadsheets/{config.GOOGLE_SHEET_ID}"
    try:
        info = _sheets_api("GET", url)
        existing = [s["properties"]["title"] for s in info.get("sheets", [])]
        if sheet_name not in existing:
            _sheets_api("POST", f"{url}:batchUpdate", {
                "requests": [{
                    "addSheet": {
                        "properties": {"title": sheet_name}
                    }
                }]
            })
            # 添加表头
            _append_rows(sheet_name, [[
                "日期", "来源", "类型", "标题", "链接", "摘要", "作者", "标签"
            ]])
    except Exception as e:
        print(f"[Archiver] 确保工作表存在失败: {e}")


def _append_rows(sheet_name: str, rows: list[list]):
    """向工作表追加行"""
    url = (
        f"https://sheets.googleapis.com/v4/spreadsheets/{config.GOOGLE_SHEET_ID}"
        f"/values/{sheet_name}!A:H:append"
        f"?valueInputOption=RAW&insertDataOption=INSERT_ROWS"
    )
    _sheets_api("POST", url, {"values": rows})


def archive_to_sheets(articles: list[Article], briefing: str) -> bool:
    """
    将筛选后的文章和简报写入 Google Sheets。
    - "Articles" 工作表: 每日筛选的文章详情
    - "Briefings" 工作表: 每日简报全文
    """
    if not config.GOOGLE_SHEET_ID:
        print("[Archiver] Google Sheet ID 未配置，跳过")
        return False

    today = datetime.utcnow().strftime("%Y-%m-%d")

    try:
        # 1. 写入文章列表
        _ensure_sheet_exists("Articles")
        rows = []
        for art in articles:
            rows.append([
                today,
                art.source,
                art.source_type,
                art.title,
                art.url,
                art.summary[:200],
                art.authors,
                ", ".join(art.tags),
            ])
        if rows:
            _append_rows("Articles", rows)
            print(f"[Archiver] 已写入 {len(rows)} 条文章到 Articles 工作表")

        # 2. 写入简报
        _ensure_sheet_exists("Briefings")
        _append_rows("Briefings", [[today, briefing]])
        print(f"[Archiver] 已写入简报到 Briefings 工作表")

        return True

    except Exception as e:
        print(f"[Archiver] Google Sheets 写入失败: {e}")
        return False
