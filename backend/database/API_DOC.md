# flkgov API 接口文档

## 概述

flkgov API 提供法律法规和条款的查询接口，基于 FastAPI 框架开发。

**基础URL：** `103.47.81.116:41002`

---

## 接口列表

### 1. 搜索法规

根据关键词搜索法规标题。

**请求方式：** GET

**请求路径：** `/flkgov/regulations`

**Query 参数：**

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| keyword | string | 否 | 搜索关键词，支持模糊匹配 |
| limit | string | 否 | 返回结果数量限制，默认返回全部 |

**请求示例：**

```
GET /flkgov/regulations?keyword=秦皇岛
GET /flkgov/regulations?keyword=秦皇岛&limit=10
```

**响应示例：**

```json
[
  {
    "id": 1,
    "item_id": "12345",
    "url": "http://example.com/regulation/12345",
    "title": "秦皇岛市某法规",
    "regulation_type": "地方性法规",
    "issuing_body": "秦皇岛市人大常委会",
    "promulgation_date": "2023-01-01",
    "effective_date": "2023-02-01",
    "status": "有效",
    "abstract": "这是法规摘要...",
    "chapter_num": 5,
    "article_num": 50
  }
]
```

---

### 2. 获取法规详情

根据ID获取单个法规的详细信息。

**请求方式：** GET

**请求路径：** `/flkgov/regulations/{regulation_id}`

**路径参数：**

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| regulation_id | string | 是 | 法规ID |

**请求示例：**

```
GET /flkgov/regulations/1
```

**响应示例：**

```json
{
  "id": 1,
  "item_id": "12345",
  "url": "http://example.com/regulation/12345",
  "title": "秦皇岛市某法规",
  "regulation_type": "地方性法规",
  "issuing_body": "秦皇岛市人大常委会",
  "promulgation_date": "2023-01-01",
  "effective_date": "2023-02-01",
  "status": "有效",
  "abstract": "这是法规摘要...",
  "chapter_num": 5,
  "article_num": 50
}
```

**错误响应：**

```json
{
  "detail": "法规不存在"
}
```

---

### 3. 搜索条款

根据法规ID搜索相关条款。

**请求方式：** GET

**请求路径：** `/flkgov/articles`

**Query 参数：**

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| regulation_id | string | 否 | 法规ID，筛选特定法规的条款 |
| limit | string | 否 | 返回结果数量限制，默认返回全部 |

**请求示例：**

```
GET /flkgov/articles?regulation_id=1
GET /flkgov/articles?regulation_id=1&limit=20
GET /flkgov/articles
```

**响应示例：**

```json
[
  {
    "id": 1,
    "regulation_id": 1,
    "chapter_no": "第一章",
    "article_no": "第一条",
    "content": "这是条款内容..."
  },
  {
    "id": 2,
    "regulation_id": 1,
    "chapter_no": "第一章",
    "article_no": "第二条",
    "content": "这是条款内容..."
  }
]
```

---

## 数据库表结构

### flkgov_regulations（法规表）

| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | SERIAL | 主键 |
| item_id | VARCHAR(50) | 法规项ID |
| url | VARCHAR(1000) | 法规URL |
| title | VARCHAR(1000) | 法规标题 |
| regulation_type | VARCHAR(100) | 法规类型 |
| issuing_body | VARCHAR(500) | 发布机关 |
| promulgation_date | DATE | 发布日期 |
| effective_date | DATE | 生效日期 |
| status | VARCHAR(20) | 状态 |
| abstract | TEXT | 摘要 |
| chapter_num | INT | 章节数 |
| article_num | INT | 条文数 |

### flkgov_articles（条款表）

| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | SERIAL | 主键 |
| regulation_id | INT | 外键，关联法规表 |
| chapter_no | VARCHAR(100) | 章节编号 |
| article_no | VARCHAR(100) | 条文编号 |
| content | TEXT | 条款内容 |

---

## 索引

| 索引名 | 表名 | 字段 |
|--------|------|------|
| idx_regulations_title | flkgov_regulations | title |
| idx_articles_regulation_id | flkgov_articles | regulation_id |
