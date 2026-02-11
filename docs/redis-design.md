# Redis 键设计说明

本文档描述国家医保局爬虫（NHSA Spider）使用的 Redis 数据结构设计。

## 设计原则

- **减少键数量**：将相关数据合并到 Hash 表中
- **统一前缀**：所有键使用 `spider:{spider_type}` 作为前缀
- **清晰命名**：键名直观易懂，便于调试和维护

## Redis 键总览

| 键名 | 类型 | 用途 |
|------|------|------|
| `spider:nhsa:state` | Hash | 爬虫状态信息 |
| `spider:nhsa:progress` | Hash | 爬取进度信息 |
| `spider:nhsa:pagination` | Hash | 翻页进度信息 |
| `spider:nhsa:visited_urls` | Set | 已访问URL去重 |
| `spider:nhsa:crawled_urls` | Set | 已爬取详情页去重 |
| `spider:nhsa:url_queue` | ZSet | 通用URL队列（按优先级） |
| `spider:nhsa:errors` | List | 错误日志 |
| `spider:nhsa:links_queue` | List | 待爬取详情链接队列 |
| `spider:nhsa:checkpoint` | String | 检查点数据 |

---

## 详细说明

### 1. state 表 - 爬虫状态

**键名**：`spider:nhsa:state`

**类型**：Hash

**字段说明**：

| 字段 | 类型 | 说明 | 示例值 |
|------|------|------|--------|
| `status` | string | 爬虫状态 | `running`, `idle`, `completed`, `error`, `stopped`, `paused`, `stopping`, `starting` |
| `phase` | string | 当前阶段 | `idle`, `link_collection`, `detail_crawling`, `completed` |
| `pid` | int | 进程ID | `12345` |
| `started_at` | datetime | 启动时间 | `2026-01-20T21:00:00` |
| `stopped_at` | datetime | 停止时间 | `2026-01-20T22:30:00` |
| `completed_at` | datetime | 完成时间 | `2026-01-20T23:00:00` |
| `updated_at` | datetime | 状态更新时间 | `2026-01-20T21:05:00` |
| `phase_updated_at` | datetime | 阶段更新时间 | `2026-01-20T21:00:00` |
| `paused` | string | 是否暂停 | `1` 或不存在 |
| `current_category` | string | 当前处理的栏目 | `政策法规` |
| `links_collected` | int | 已收集链接数 | `150` |
| `details_crawled` | int | 已爬取详情数 | `45` |
| `error_count` | int | 错误数量 | `3` |
| `last_error` | string | 最后错误信息 | `Connection timeout` |

**获取状态示例**：
```python
# HGETALL spider:nhsa:state
{
    "status": "running",
    "phase": "link_collection",
    "pid": "12345",
    "started_at": "2026-01-20T21:00:00",
    "links_collected": "150",
    "details_crawled": "45",
    "error_count": "3"
}
```

---

### 2. progress 表 - 爬取进度

**键名**：`spider:nhsa:progress`

**类型**：Hash

**字段说明**：

| 字段 | 类型 | 说明 | 示例值 |
|------|------|------|--------|
| `crawled` | int | 已爬取数量 | `45` |
| `total` | int | 总数量 | `200` |
| `category` | string | 当前栏目 | `政策法规` |
| `errors` | int | 错误数 | `3` |
| `updated_at` | datetime | 更新时间 | `2026-01-20T21:05:00` |

---

### 3. pagination 表 - 翻页进度

**键名**：`spider:nhsa:pagination`

**类型**：Hash

**字段说明**：

| 字段 | 类型 | 说明 | 示例值 |
|------|------|------|--------|
| `{column_id}` | int | 栏目当前已爬取记录数 | `120`（表示已爬到第120条记录） |
| `{column_id}_complete` | int | 栏目是否完成 | `1`（已完成）或不存在（未完成） |

**字段命名规则**：
- 记录数字段：`{column_id}` → 例如 `104`, `105`, `109`, `110`
- 完成状态字段：`{column_id}_complete` → 例如 `104_complete`, `105_complete`

**数据示例**：
```
HSET spider:nhsa:pagination 104 120 104_complete 0 105 45 105_complete 1
```
表示：
- 栏目104（政策法规）已爬到第120条记录，未完成
- 栏目105（政策解读）已爬到第45条记录，已完成

**栏目ID对应关系**：
| 栏目ID | 栏目名称 | 总记录数 |
|--------|---------|---------|
| 104 | 政策法规 | 244 |
| 105 | 政策解读 | 105 |
| 109 | 通知公告 | 267 |
| 110 | 建议提案 | 783 |

**示例**：
```
HSET spider:nhsa:pagination 1 15 1_complete 0 2 8 2_complete 1
```

---

### 4. visited_urls - URL去重（链接收集阶段）

**键名**：`spider:nhsa:visited_urls`

**类型**：Set

**用途**：记录已收集过的URL，防止重复收集

**操作**：
- 添加：`SADD spider:nhsa:visited_urls {url}`
- 检查：`SISMEMBER spider:nhsa:visited_urls {url}`
- 数量：`SCARD spider:nhsa:visited_urls`

**示例**：
```
SADD spider:nhsa:visited_urls https://www.nhsa.gov.cn/art/2024/11/28/art_14_1234.html
```

---

### 5. crawled_urls - 详情页去重（详情爬取阶段）

**键名**：`spider:nhsa:crawled_urls`

**类型**：Set

**用途**：记录已爬取过的详情页URL，防止重复爬取

**操作**：
- 添加：`SADD spider:nhsa:crawled_urls {url}`
- 检查：`SISMEMBER spider:nhsa:crawled_urls {url}`
- 数量：`SCARD spider:nhsa:crawled_urls`

---

### 6. url_queue - 通用URL队列

**键名**：`spider:nhsa:url_queue`

**类型**：ZSet（有序集合）

**用途**：按优先级排序的URL队列

**分数**：优先级（数值越小优先级越高）

**操作**：
- 添加：`ZADD spider:nhsa:url_queue {priority} {url}`
- 取出：`ZPOPMIN spider:nhsa:url_queue`
- 大小：`ZCARD spider:nhsa:url_queue`

---

### 7. errors - 错误日志

**键名**：`spider:nhsa:errors`

**类型**：List

**用途**：存储爬取过程中的错误记录

**数据结构**：
```json
{
    "timestamp": "2026-01-20T21:05:00",
    "type": "request_error",
    "url": "https://www.nhsa.gov.cn/...",
    "message": "Connection timeout"
}
```

**操作**：
- 添加：`LPUSH spider:nhsa:errors {json}`
- 获取：`LRANGE spider:nhsa:errors 0 {limit}`
- 数量：`LLEN spider:nhsa:errors`
- 保留最近100条：`LTRIM spider:nhsa:errors 0 99`

---

### 8. links_queue - 待爬取链接队列

**键名**：`spider:nhsa:links_queue`

**类型**：List

**用途**：存储待爬取的详情页链接（从链接收集阶段产生）

**数据结构**：
```json
{
    "url": "https://www.nhsa.gov.cn/art/2024/11/28/art_14_1234.html",
    "title": "关于印发《国家基本医疗保险、工伤保险和生育保险药品目录(2024年)》的通知",
    "category": "政策法规",
    "index": "1",
    "document_number": "医保发〔2024〕22号",
    "publish_date": "2024-11-28",
    "collected_at": "2026-01-20T21:05:00"
}
```

**操作**：
- 添加：`LPUSH spider:nhsa:links_queue {json}`
- 取出：`RPOP spider:nhsa:links_queue`
- 大小：`LLEN spider:nhsa:links_queue`

---

### 9. checkpoint - 检查点

**键名**：`spider:nhsa:checkpoint`

**类型**：String

**用途**：存储爬虫中断后的恢复信息

**数据结构**：
```json
{
    "phase": "link_collection",
    "last_column_id": 1,
    "last_page": 15,
    "links_collected": 150,
    "details_crawled": 45,
    "saved_at": "2026-01-20T21:05:00"
}
```

---

## 爬虫状态流程

```
┌─────────────────────────────────────────────────────────────┐
│                     状态流转图                               │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   idle ──启动──→ starting ──成功──→ running                 │
│    ↑                         │                              │
│    │                         │                              │
│    │                         ↓                              │
│    │                   running ←─恢复──┐                    │
│    │                     │            │                    │
│    │                     ↓            │                    │
│    │              ┌──────┴──────┐     │                    │
│    │              ↓    ↓    ↓   ↓     │                    │
│    │           [链接收] [详情爬] [完成] │                    │
│    │              │         │         │                    │
│    │              ↓         ↓         │                    │
│    │              └─────→ pausing ────┘                    │
│    │                         │                              │
│    │                         ↓                              │
│    │                   paused                                │
│    │                         │                              │
│    │                         ↓                              │
│    │         停止────────→ stopping ──完成──→ stopped       │
│    │                         │                              │
│    │                         ↓                              │
│    │                   [错误] ──→ error                     │
│    │                                                      │
│    └──────────────────────────────────────────────────────┘
```

---

## Redis 命令速查

### 状态管理

```bash
# 查看爬虫状态
HGETALL spider:nhsa:state

# 设置爬虫状态
HSET spider:nhsa:status status "running" updated_at "2026-01-20T21:00:00"

# 检查爬虫是否运行
HGET spider:nhsa:state status
```

### 链接管理

```bash
# 添加URL到已访问集合
SADD spider:nhsa:visited_urls "https://..."

# 检查URL是否已访问
SISMEMBER spider:nhsa:visited_urls "https://..."

# 获取已访问URL数量
SCARD spider:nhsa:visited_urls

# 添加链接到待爬取队列
LPUSH spider:nhsa:links_queue '{"url":"...","title":"..."}'

# 从队列取出链接
RPOP spider:nhsa:links_queue

# 获取队列大小
LLEN spider:nhsa:links_queue
```

### 翻页进度

```bash
# 设置栏目翻页进度
HSET spider:nhsa:pagination 1 15

# 标记栏目完成
HSET spider:nhsa:pagination 1_complete 1

# 获取栏目翻页进度
HGET spider:nhsa:pagination 1

# 检查栏目是否完成
HGET spider:nhsa:pagination 1_complete
```

### 错误日志

```bash
# 添加错误日志
LPUSH spider:nhsa:errors '{"type":"error","message":"..."}'

# 获取最近10条错误
LRANGE spider:nhsa:errors 0 9

# 获取错误数量
LLEN spider:nhsa:errors
```

### 清理数据

```bash
# 清理指定爬虫的所有数据
DEL spider:nhsa:state spider:nhsa:progress spider:nhsa:pagination \
    spider:nhsa:visited_urls spider:nhsa:crawled_urls \
    spider:nhsa:url_queue spider:nhsa:errors \
    spider:nhsa:links_queue spider:nhsa:checkpoint

# 或使用清理命令（如果实现了cleanup方法）
redis_manager.cleanup()
```

---

## 注意事项

1. **连接配置**：Redis 连接地址为 `192.168.1.40:6379`，密码 `1421nbnb`
2. **数据隔离**：不同爬虫类型使用不同前缀（如 `spider:nhsa`, `spider:wjw`）
3. **内存管理**：错误日志最多保留100条（`LTRIM spider:nhsa:errors 0 99`）
4. **持久化**：Redis 数据默认持久化到磁盘
5. **键过期**：检查点数据建议定期更新，避免数据丢失
