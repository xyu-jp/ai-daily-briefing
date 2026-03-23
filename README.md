# 🤖 AI Daily Briefing - AI 每日简报自动化系统

每天自动采集 AI 领域最新论文、产品发布和行业观点，经 Claude AI 智能筛选后，生成中文简报推送到 Slack / Telegram，并归档至 Google Sheets。

## 系统架构

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌──────────┐
│  信息采集     │ →  │  AI 筛选     │ →  │  简报生成    │ →  │  推送     │
│  collector   │    │  analyzer   │    │  analyzer   │    │ notifier │
│              │    │             │    │             │    │          │
│ • arXiv API  │    │ Claude 判断  │    │ Claude 撰写  │    │ • Slack  │
│ • RSS feeds  │    │ 是否有创新性  │    │ 中文要点简报  │    │ • TG Bot │
│ • KOL feeds  │    │             │    │             │    │          │
└─────────────┘    └─────────────┘    └─────────────┘    └──────────┘
                                                              ↓
                                                    ┌──────────────┐
                                                    │  归档          │
                                                    │  archiver     │
                                                    │ Google Sheets │
                                                    └──────────────┘
```

## 快速开始

### 前置条件

- Python 3.9+
- Anthropic API Key（用于 Claude 智能分析）
- （可选）Slack Webhook / Telegram Bot
- （可选）Google Cloud Service Account

### 1. 获取 OpenAI API Key

1. 访问 https://platform.openai.com/api-keys
2. 创建 API Key，复制保存
3. 默认使用 `gpt-4o-mini`（最便宜），也可切换为 `gpt-4o`（更强）

### 2. 配置 Slack 推送（推荐）

1. 访问 https://api.slack.com/apps → "Create New App" → "From scratch"
2. 选择你的 Workspace
3. 左侧菜单 "Incoming Webhooks" → 开启 → "Add New Webhook to Workspace"
4. 选择要推送的频道，复制 Webhook URL

### 3. 配置 Telegram 推送（可选）

1. 在 Telegram 搜索 `@BotFather`，发送 `/newbot`，按提示创建 Bot
2. 记下 Bot Token（格式: `123456:ABC-DEF...`）
3. 给你的 Bot 发一条消息，然后访问:
   `https://api.telegram.org/bot<你的TOKEN>/getUpdates`
4. 找到 `chat.id` 字段，这就是你的 Chat ID

### 4. 配置 Google Sheets 归档（可选）

1. 访问 [Google Cloud Console](https://console.cloud.google.com/)
2. 创建项目 → 启用 "Google Sheets API"
3. "IAM 与管理" → "服务账号" → 创建服务账号 → 下载 JSON 密钥
4. 创建一个 Google Spreadsheet，记下 URL 中的 Sheet ID
   （`https://docs.google.com/spreadsheets/d/这里就是SHEET_ID/edit`）
5. 将服务账号邮箱（`xxx@xxx.iam.gserviceaccount.com`）添加为该表格的编辑者

### 5. 本地测试

```bash
# 安装依赖
pip install -r requirements.txt

# 设置环境变量
export OPENAI_API_KEY="sk-..."
export OPENAI_MODEL="gpt-4o-mini"                                  # 可选，默认就是这个
export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/..."    # 可选
export TELEGRAM_BOT_TOKEN="123456:ABC-DEF..."                      # 可选
export TELEGRAM_CHAT_ID="你的ChatID"                                # 可选
export GOOGLE_SHEET_ID="你的SheetID"                                # 可选

# 仅测试采集
python main.py --collect

# 测试采集+分析（不推送不归档）
python main.py --dry-run

# 运行完整流程
python main.py
```

### 6. 部署到 GitHub Actions（每日自动运行）

1. 在 GitHub 创建一个新的 private repo
2. 把本项目所有文件推送上去
3. 在 repo 的 Settings → Secrets and variables → Actions 中添加以下 Secrets:

| Secret 名称 | 说明 | 必须 |
|---|---|---|
| `OPENAI_API_KEY` | OpenAI API Key | ✅ |
| `OPENAI_MODEL` | 模型名（默认 gpt-4o-mini） | 否 |
| `SLACK_WEBHOOK_URL` | Slack Webhook URL | 按需 |
| `TELEGRAM_BOT_TOKEN` | Telegram Bot Token | 按需 |
| `TELEGRAM_CHAT_ID` | Telegram Chat ID | 按需 |
| `GOOGLE_SHEET_ID` | Google Spreadsheet ID | 按需 |
| `GOOGLE_CREDENTIALS_JSON` | 服务账号 JSON 密钥的**完整内容** | 按需 |

4. 默认每天 UTC 22:00（北京时间次日 6:00）自动运行
5. 也可在 Actions 页面手动点击 "Run workflow" 触发

修改运行时间：编辑 `.github/workflows/daily-briefing.yml` 中的 cron 表达式。

## 文件说明

```
ai-daily-briefing/
├── main.py          # 主程序，流程编排
├── config.py        # 配置文件（环境变量读取）
├── collector.py     # 信息采集（arXiv + RSS）
├── analyzer.py      # AI 筛选 + 简报生成（Claude API）
├── notifier.py      # 推送通知（Slack + Telegram）
├── archiver.py      # Google Sheets 归档
├── requirements.txt # Python 依赖
├── .env.example     # 环境变量模板
└── .github/
    └── workflows/
        └── daily-briefing.yml  # GitHub Actions 定时任务
```

## 自定义

### 调整信息源

编辑 `config.py` 中的:
- `ARXIV_CATEGORIES`: arXiv 分类（如添加 `cs.RO` 机器人学）
- `BLOG_FEEDS`: AI 公司博客 RSS 地址
- `KOL_FEEDS`: KOL/Newsletter RSS 地址

### 调整筛选标准

编辑 `analyzer.py` 中 `filter_articles()` 的 system prompt。

### 调整简报风格

编辑 `analyzer.py` 中 `generate_briefing()` 的 system prompt。

## 费用估算

- **ChatGPT API (gpt-4o-mini)**: 每日约 $0.005-0.01，非常便宜
- **GitHub Actions**: 免费（Private repo 每月 2000 分钟）
- **Google Sheets API**: 免费
- **Telegram Bot**: 免费
- **Slack Webhook**: 免费

**预计月费: < $0.5（gpt-4o-mini）或 < $3（gpt-4o）**

## 关于 X (Twitter) 信息源

X 的 API 目前对免费用户限制很严。替代方案:
1. 关注 KOL 的 Newsletter / Blog（很多大牛同时维护博客）
2. 使用公共 Nitter 实例的 RSS（不稳定，需定期更换实例）
3. 如果有 X API 付费账号，可在 `collector.py` 中添加 Twitter 采集器

## 后续扩展思路

- 添加更多信息源（GitHub Trending、HackerNews、TechCrunch）
- 简报内添加趋势分析（对比过去一周的热点变化）
- 多语言支持（日语版简报）
- 建立知识库，追踪特定研究方向的演进
