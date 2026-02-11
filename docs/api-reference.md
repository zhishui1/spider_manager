# 爬虫管理 API 文档

本文档描述了爬虫管理系统新增的 RESTful API 接口。

## 目录

- [概述](#概述)
- [基础信息](#基础信息)
- [API 接口](#api-接口)
  - [1. 获取爬虫项目列表](#1-获取爬虫项目列表)
  - [2. 获取爬虫项目详细信息](#2-获取爬虫项目详细信息)
  - [3. 下载爬虫项目 JSON 文件](#3-下载爬虫项目-json-文件)
  - [4. 下载单个 item_id 文件包](#4-下载单个-item_id-文件包)
  - [5. 批量下载多个 item_id 文件包](#5-批量下载多个-item_id-文件包)
- [错误处理](#错误处理)
- [使用示例](#使用示例)

---

## 概述

本文档描述了爬虫管理系统的 RESTful API 接口，用于获取爬虫项目信息、统计数据以及下载相关文件。

### 爬虫项目标识符

每个爬虫项目都有一个唯一的 `spider_id`，定义在其配置文件中：

| 爬虫类型 | spider_id | 配置文件 |
|----------|-----------|----------|
| 国家医保局爬虫 | `nhsa_2026` | `backend/spiders/crawlers/nhsa/config.py` |
| 卫生健康委爬虫 | `wjw_*` | `backend/spiders/crawlers/wjw/config.py` |

---

## 基础信息

### 基础 URL

```
http://localhost:8000/api/v1/spiders
```

### 通用响应格式

成功响应：
```json
{
  "success": true,
  "data": { ... }
}
```

错误响应：
```json
{
  "success": false,
  "error": "错误信息",
  "details": "详细错误信息（可选）"
}
```

### HTTP 方法说明

| 方法 | 用途 |
|------|------|
| GET | 获取数据和小型文件下载 |
| POST | 提交数据，用于批量下载 |

---

## API 接口

### 1. 获取爬虫项目列表

获取系统中所有爬虫项目的基础信息。

#### 请求

```http
GET /api/v1/spiders/list/
```

#### 参数

无

#### 响应

**状态码：200 OK**

```json
{
  "success": true,
  "data": [
    {
      "spider_id": "nhsa_2026",
      "spider_name": "nhsa",
      "spider_display_name": "国家医保局爬虫"
    }
  ]
}
```

#### 示例

**cURL**
```bash
curl -X GET "http://localhost:8000/api/v1/spiders/list/"
```

**Python**
```python
import requests

response = requests.get("http://localhost:8000/api/v1/spiders/list/")
if response.status_code == 200:
    data = response.json()
    print(data)
```

---

### 2. 获取爬虫项目详细信息

根据爬虫项目 ID 查询该项目的详细统计信息。

#### 请求

```http
GET /api/v1/spiders/{spider_id}/stats/
```

#### 参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `spider_id` | string | 是 | 爬虫项目唯一标识符 |

#### 响应

**状态码：200 OK**

```json
{
  "success": true,
  "data": {
    "spider_id": "nhsa_2026",
    "spider_name": "nhsa",
    "spider_display_name": "国家医保局爬虫",
    "collected_links": 1500,
    "pending_links": 50,
    "crawled_links": 1450,
    "file_count": 3200,
    "error_count": 5,
    "last_updated": "2026-01-24 10:30:00"
  }
}
```

**状态码：404 Not Found**

```json
{
  "success": false,
  "error": "爬虫项目不存在"
}
```

#### 字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `collected_links` | integer | 已收集的链接总数 |
| `pending_links` | integer | 待爬取的链接数量 |
| `crawled_links` | integer | 已成功爬取的链接数量 |
| `file_count` | integer | 附件文件总数 |
| `error_count` | integer | 爬取过程中的错误数量 |
| `last_updated` | string | 最后更新时间，格式为 `YYYY-MM-DD HH:MM:SS` |

#### 示例

**cURL**
```bash
curl -X GET "http://localhost:8000/api/v1/spiders/nhsa_2026/stats/"
```

**Python**
```python
import requests

spider_id = "nhsa_2026"
response = requests.get(f"http://localhost:8000/api/v1/spiders/{spider_id}/stats/")
if response.status_code == 200:
    data = response.json()
    stats = data["data"]
    print(f"已收集链接: {stats['collected_links']}")
    print(f"已爬取链接: {stats['crawled_links']}")
    print(f"文件数量: {stats['file_count']}")
```

---

### 3. 下载爬虫项目 JSON 数据文件

根据爬虫项目 ID 下载对应的 JSON 数据文件（爬取的网页数据）。

#### 请求

```http
GET /api/v1/spiders/{spider_id}/json/
```

#### 参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `spider_id` | string | 是 | 爬虫项目唯一标识符 |

#### 响应

**状态码：200 OK**

返回 JSON 数据文件下载流。

**响应头**

| 头信息 | 值 |
|--------|-----|
| Content-Type | application/json |
| Content-Disposition | attachment; filename="nhsa_data.json" |

**状态码：404 Not Found**

```json
{
  "success": false,
  "error": "爬虫项目不存在"
}
```

或

```json
{
  "success": false,
  "error": "数据文件不存在"
}
```

#### 数据格式

下载的 JSON 数据文件采用 NDJSON 格式（每行一条 JSON 记录）：

```json
{"item_id": "123456", "title": "文章标题", "publish_date": "2026-01-01", "url": "https://...", "content": "文章内容...", "attachments": [{"filename": "xxx.pdf", "filepath": "..."}]}
{"item_id": "123457", "title": "文章标题2", "publish_date": "2026-01-02", "url": "https://...", "content": "文章内容...", "attachments": [...]}
```

#### 示例

**cURL**
```bash
curl -X GET "http://localhost:8000/api/v1/spiders/nhsa_2026/json/" \
     -o nhsa_data.json
```

**Python**
```python
import requests

spider_id = "nhsa_2026"
response = requests.get(f"http://localhost:8000/api/v1/spiders/{spider_id}/json/")
if response.status_code == 200:
    with open("nhsa_data.json", "wb") as f:
        f.write(response.content)
    print("数据文件已保存到 nhsa_data.json")
else:
    print(f"下载失败: {response.json()}")
```
```

---

### 4. 下载单个 item_id 文件包

根据爬虫项目 ID 和 item_id，将对应文件夹下的所有文件打包为 ZIP 并提供下载。

#### 请求

```http
GET /api/v1/spiders/{spider_id}/items/{item_id}/download/
```

#### 参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `spider_id` | string | 是 | 爬虫项目唯一标识符 |
| `item_id` | string | 是 | 数据项的唯一标识符 |

#### 响应

**状态码：200 OK**

返回 ZIP 文件下载流。

**响应头**

| 头信息 | 值 |
|--------|-----|
| Content-Type | application/zip |
| Content-Disposition | attachment; filename="nhsa_1769172544270.zip" |

**状态码：404 Not Found**

```json
{
  "success": false,
  "error": "爬虫项目不存在"
}
```

或

```json
{
  "success": false,
  "error": "item文件夹不存在"
}
```

#### 示例

**cURL**
```bash
curl -X GET "http://localhost:8000/api/v1/spiders/nhsa_2026/items/1769172544270/download/" \
     -o nhsa_1769172544270.zip
```

**Python**
```python
import requests

spider_id = "nhsa_2026"
item_id = "1769172544270"

response = requests.get(
    f"http://localhost:8000/api/v1/spiders/{spider_id}/items/{item_id}/download/"
)
if response.status_code == 200:
    filename = f"nhsa_{item_id}.zip"
    with open(filename, "wb") as f:
        f.write(response.content)
    print(f"文件已保存到 {filename}")
else:
    print(f"下载失败: {response.json()}")
```

---

### 5. 批量下载多个 item_id 文件包

根据爬虫项目 ID 和多个 item_id，将多个对应文件夹及其内容批量打包为 ZIP 并提供下载。

#### 请求

```http
POST /api/v1/spiders/{spider_id}/items/batch-download/
Content-Type: application/json

{
  "item_ids": ["item_id_1", "item_id_2", "item_id_3"]
}
```

#### 参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `spider_id` | string | 是 | 爬虫项目唯一标识符 |
| `item_ids` | array | 是 | 要下载的 item_id 列表 |

#### 请求体

```json
{
  "item_ids": ["1769172544270", "1769173209899", "1769173254861"]
}
```

#### 响应

**状态码：200 OK**

返回 ZIP 文件下载流。

**响应头**

| 头信息 | 值 |
|--------|-----|
| Content-Type | application/zip |
| Content-Disposition | attachment; filename="nhsa_batch_20240123_120000.zip" |

**状态码：400 Bad Request**

```json
{
  "success": false,
  "error": "item_ids参数不能为空"
}
```

或

```json
{
  "success": false,
  "error": "item_ids必须为数组"
}
```

**状态码：404 Not Found**

```json
{
  "success": false,
  "error": "爬虫项目不存在"
}
```

或

```json
{
  "success": false,
  "error": "部分item_id不存在",
  "missing_item_ids": ["1769179999999"]
}
```

#### 示例

**cURL**
```bash
curl -X POST "http://localhost:8000/api/v1/spiders/nhsa_2026/items/batch-download/" \
     -H "Content-Type: application/json" \
     -d '{"item_ids": ["1769172544270", "1769173209899", "1769173254861"]}' \
     -o nhsa_batch.zip
```

**Python**
```python
import requests
import json

spider_id = "nhsa_2026"
item_ids = ["1769172544270", "1769173209899", "1769173254861"]

response = requests.post(
    f"http://localhost:8000/api/v1/spiders/{spider_id}/items/batch-download/",
    json={"item_ids": item_ids}
)

if response.status_code == 200:
    from datetime import datetime
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"nhsa_batch_{timestamp}.zip"
    with open(filename, "wb") as f:
        f.write(response.content)
    print(f"批量下载已完成: {filename}")
elif response.status_code == 404:
    error_data = response.json()
    print(f"部分item_id不存在: {error_data.get('missing_item_ids', [])}")
else:
    print(f"下载失败: {response.json()}")
```

---

## 错误处理

所有接口遵循统一的错误处理规范。

### HTTP 状态码

| 状态码 | 说明 |
|--------|------|
| 200 | 请求成功 |
| 400 | 请求参数无效 |
| 404 | 资源不存在 |
| 405 | 请求方法不允许 |
| 500 | 服务器内部错误 |

### 错误响应格式

```json
{
  "success": false,
  "error": "错误描述信息"
}
```

### 常见错误

| 错误信息 | 说明 |
|----------|------|
| "爬虫项目不存在" | spider_id 无效或不存在 |
| "数据文件不存在" | JSON 数据文件未找到 |
| "item文件夹不存在" | 指定的 item_id 文件夹不存在 |
| "部分item_id不存在" | 批量下载时部分 item_id 不存在 |
| "item_ids参数不能为空" | 批量下载时未提供 item_ids |
| "item_ids必须为数组" | item_ids 参数格式错误 |
| "仅支持POST请求" | 接口仅支持 POST 方法 |
| "请求体必须为有效的JSON" | 请求体 JSON 格式错误 |
| "服务器内部错误" | 服务器发生未预期的错误 |
| "文件目录不存在" | 爬虫项目的附件文件目录不存在 |

---

## 使用示例

### 完整的 Python 使用示例

```python
import requests
from datetime import datetime

BASE_URL = "http://localhost:8000/api/v1/spiders"


class SpiderAPI:
    """爬虫管理 API 客户端"""
    
    @staticmethod
    def get_spider_list():
        """获取爬虫项目列表"""
        response = requests.get(f"{BASE_URL}/list/")
        return response.json()
    
    @staticmethod
    def get_spider_stats(spider_id):
        """获取爬虫项目统计信息"""
        response = requests.get(f"{BASE_URL}/{spider_id}/stats/")
        return response.json()
    
    @staticmethod
    def download_config(spider_id, save_path):
        """下载 JSON 配置文件"""
        response = requests.get(f"{BASE_URL}/{spider_id}/json/")
        if response.status_code == 200:
            with open(save_path, "wb") as f:
                f.write(response.content)
            return True
        return False
    
    @staticmethod
    def download_item(spider_id, item_id, save_path):
        """下载单个 item 的附件 ZIP"""
        response = requests.get(
            f"{BASE_URL}/{spider_id}/items/{item_id}/download/"
        )
        if response.status_code == 200:
            with open(save_path, "wb") as f:
                f.write(response.content)
            return True
        return False
    
    @staticmethod
    def batch_download_items(spider_id, item_ids, save_path):
        """批量下载多个 item 的附件"""
        response = requests.post(
            f"{BASE_URL}/{spider_id}/items/batch-download/",
            json={"item_ids": item_ids}
        )
        if response.status_code == 200:
            with open(save_path, "wb") as f:
                f.write(response.content)
            return True, None
        else:
            error_data = response.json()
            return False, error_data.get("missing_item_ids", [])


# 使用示例
if __name__ == "__main__":
    api = SpiderAPI()
    
    # 1. 获取爬虫列表
    print("=== 获取爬虫项目列表 ===")
    result = api.get_spider_list()
    if result["success"]:
        for spider in result["data"]:
            print(f"- {spider['spider_display_name']} ({spider['spider_id']})")
    
    # 2. 获取爬虫统计
    print("\n=== 获取爬虫统计信息 ===")
    spider_id = "nhsa_2026"
    result = api.get_spider_stats(spider_id)
    if result["success"]:
        stats = result["data"]
        print(f"爬虫名称: {stats['spider_display_name']}")
        print(f"已收集链接: {stats['collected_links']}")
        print(f"已爬取链接: {stats['crawled_links']}")
        print(f"待爬取链接: {stats['pending_links']}")
        print(f"文件数量: {stats['file_count']}")
        print(f"错误数量: {stats['error_count']}")
        print(f"最后更新: {stats.get('last_updated', 'N/A')}")
    
    # 3. 下载数据文件
    print("\n=== 下载数据文件 ===")
    if api.download_config(spider_id, "nhsa_data.json"):
        print("数据文件已保存到 nhsa_data.json")
    
    # 4. 下载单个 item
    print("\n=== 下载单个 item ===")
    item_id = "1769172544270"
    if api.download_item(spider_id, item_id, f"nhsa_{item_id}.zip"):
        print(f"item {item_id} 已保存到 nhsa_{item_id}.zip")
    
    # 5. 批量下载
    print("\n=== 批量下载 ===")
    item_ids = ["1769172544270", "1769173209899", "1769173254861"]
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    success, missing = api.batch_download_items(
        spider_id, item_ids, f"nhsa_batch_{timestamp}.zip"
    )
    if success:
        print(f"批量下载完成: nhsa_batch_{timestamp}.zip")
    elif missing:
        print(f"以下 item_id 不存在: {missing}")
```

---

## 附录

### 数据目录结构

```
data/
├── nhsa/
│   ├── nhsa_data.json         # 爬取的数据文件
│   └── nhsa_files/            # 附件文件目录
│       ├── 1769172544270/
│       │   ├── 1769172544270_1.txt
│       │   ├── 1769172544270_2.pdf
│       │   └── 1769172544270_3.jpg
│       ├── 1769173209899/
│       │   └── ...
│       └── ...
└── wjw/
    └── ...
```

### JSON 数据格式

每条数据记录的格式（NDJSON，每行一条）：

```json
{
  "item_id": 1769172544270,
  "title": "国家医疗保障局办公室关于完善新冠治疗药品价格形成机制 实施分类管理的通知",
  "publish_date": "2023-03-28",
  "url": "https://www.nhsa.gov.cn/art/2023/3/28/art_104_10299.html",
  "data": {
    "category": "政策法规",
    "index": "2023-02-00007",
    "document_number": "医保办发〔2023〕8号",
    "crawled_at": "2026-01-23T19:44:52.451733"
  }
}
```

---

*文档最后更新时间：2026-01-24*
