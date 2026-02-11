"""
爬虫管理 API 接口测试脚本

该脚本包含 5 个 API 接口的测试用例：
1. 获取爬虫项目列表
2. 获取爬虫项目统计信息
3. 下载爬虫项目 JSON 配置文件
4. 下载单个 item 的 ZIP 文件包
5. 批量下载多个 item 的 ZIP 文件包

使用方法：
    python test_api_endpoints.py

依赖：
    pip install requests
"""

import os
import sys
import time
import requests
from typing import List, Optional
from datetime import datetime

BASE_URL = "http://localhost:8000/api/v1/spiders"

SPIDER_ID = "nhsa_2026"
TEST_ITEM_IDS = ["1769172544270", "1769173209899", "1769173254861"]


def test_spider_list() -> bool:
    """
    测试接口 1：获取爬虫项目列表

    GET /api/v1/spiders/list/

    返回所有已注册的爬虫项目信息
    """
    print("\n" + "=" * 60)
    print("测试接口 1：获取爬虫项目列表")
    print("=" * 60)

    url = f"{BASE_URL}/list/"
    print(f"请求地址: {url}")
    print(f"请求方法: GET")

    try:
        response = requests.get(url, timeout=30)
        print(f"响应状态码: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                spiders = data.get("data", [])
                print(f"获取到 {len(spiders)} 个爬虫项目：")
                for spider in spiders:
                    print(f"  - spider_id: {spider.get('spider_id')}")
                    print(f"    spider_name: {spider.get('spider_name')}")
                    print(f"    spider_display_name: {spider.get('spider_display_name')}")
                    print()
                return True
            else:
                print(f"请求失败: {data.get('error')}")
                return False
        else:
            print(f"请求失败，状态码: {response.status_code}")
            return False

    except requests.exceptions.RequestException as e:
        print(f"请求异常: {e}")
        return False


def test_spider_detail(spider_id: str) -> bool:
    """
    测试接口 2：获取爬虫项目统计信息

    GET /api/v1/spiders/{spider_id}/stats/

    返回指定爬虫项目的详细统计信息，包括链接收集情况、文件数量等
    """
    print("\n" + "=" * 60)
    print("测试接口 2：获取爬虫项目统计信息")
    print("=" * 60)

    url = f"{BASE_URL}/{spider_id}/stats/"
    print(f"请求地址: {url}")
    print(f"请求方法: GET")
    print(f"spider_id: {spider_id}")

    try:
        response = requests.get(url, timeout=30)
        print(f"响应状态码: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                stats = data.get("data", {})
                print("\n统计信息：")
                print(f"  爬虫名称: {stats.get('spider_name', 'N/A')}")
                print(f"  爬虫显示名称: {stats.get('spider_display_name', 'N/A')}")
                print(f"  已收集链接: {stats.get('collected_links', 0)}")
                print(f"  待爬取链接: {stats.get('pending_links', 0)}")
                print(f"  已爬取链接: {stats.get('crawled_links', 0)}")
                print(f"  文件数量: {stats.get('file_count', 0)}")
                print(f"  错误数量: {stats.get('error_count', 0)}")
                print(f"  最后更新: {stats.get('last_updated', 'N/A')}")
                return True
            else:
                print(f"请求失败: {data.get('error')}")
                return False
        elif response.status_code == 404:
            print(f"爬虫项目不存在: {spider_id}")
            return False
        else:
            print(f"请求失败，状态码: {response.status_code}")
            return False

    except requests.exceptions.RequestException as e:
        print(f"请求异常: {e}")
        return False


def test_download_config(spider_id: str, output_dir: str = "./downloads") -> bool:
    """
    测试接口 3：下载爬虫项目 JSON 数据文件

    GET /api/v1/spiders/{spider_id}/json/

    下载指定爬虫项目的 JSON 数据文件（爬取的网页数据）
    """
    print("\n" + "=" * 60)
    print("测试接口 3：下载爬虫项目 JSON 数据文件")
    print("=" * 60)

    url = f"{BASE_URL}/{spider_id}/json/"
    print(f"请求地址: {url}")
    print(f"请求方法: GET")
    print(f"spider_id: {spider_id}")

    os.makedirs(output_dir, exist_ok=True)

    try:
        response = requests.get(url, timeout=30)
        print(f"响应状态码: {response.status_code}")

        if response.status_code == 200:
            content_type = response.headers.get("Content-Type", "")
            if "application/json" in content_type:
                content_text = response.text.strip()
                if content_text.startswith('{') and content_text.endswith('}'):
                    try:
                        data = response.json()
                        if data.get("success") is False:
                            print(f"请求失败: {data.get('error')}")
                            return False
                    except requests.exceptions.JSONDecodeError:
                        pass

            filename = response.headers.get("Content-Disposition", "").split("filename=")[-1].strip('"')
            if not filename:
                filename = f"{spider_id}_data.json"

            filepath = os.path.join(output_dir, filename)
            with open(filepath, "wb") as f:
                f.write(response.content)

            file_size = os.path.getsize(filepath)
            print(f"数据文件已保存: {filepath}")
            print(f"文件大小: {file_size} 字节")

            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read(500)
                print(f"数据内容预览 (前500字符): {content[:500]}...")
            return True

        elif response.status_code == 404:
            print(f"数据文件不存在: {spider_id}")
            return False
        else:
            print(f"请求失败，状态码: {response.status_code}")
            return False

    except requests.exceptions.RequestException as e:
        print(f"请求异常: {e}")
        return False


def test_download_item_zip(spider_id: str, item_id: str, output_dir: str = "./downloads") -> bool:
    """
    测试接口 4：下载单个 item 的 ZIP 文件包

    GET /api/v1/spiders/{spider_id}/items/{item_id}/download/

    将指定 item 文件夹下的所有文件打包为 ZIP 并下载
    """
    print("\n" + "=" * 60)
    print("测试接口 4：下载单个 item 的 ZIP 文件包")
    print("=" * 60)

    url = f"{BASE_URL}/{spider_id}/items/{item_id}/download/"
    print(f"请求地址: {url}")
    print(f"请求方法: GET")
    print(f"spider_id: {spider_id}")
    print(f"item_id: {item_id}")

    os.makedirs(output_dir, exist_ok=True)

    try:
        response = requests.get(url, timeout=60)
        print(f"响应状态码: {response.status_code}")

        if response.status_code == 200:
            content_type = response.headers.get("Content-Type", "")
            if "application/json" in content_type:
                data = response.json()
                if data.get("success") is False:
                    print(f"请求失败: {data.get('error')}")
                    return False

            filename = response.headers.get("Content-Disposition", "").split("filename=")[-1].strip('"')
            if not filename:
                filename = f"{spider_id}_{item_id}.zip"

            filepath = os.path.join(output_dir, filename)
            with open(filepath, "wb") as f:
                f.write(response.content)

            file_size = os.path.getsize(filepath)
            print(f"文件已保存: {filepath}")
            print(f"文件大小: {file_size} 字节")
            return True
        elif response.status_code == 404:
            error_data = response.json()
            print(f"请求失败: {error_data.get('error')}")
            return False
        else:
            print(f"请求失败，状态码: {response.status_code}")
            return False

    except requests.exceptions.RequestException as e:
        print(f"请求异常: {e}")
        return False


def test_batch_download_items(spider_id: str, item_ids: List[str], output_dir: str = "./downloads") -> bool:
    """
    测试接口 5：批量下载多个 item 的 ZIP 文件包

    POST /api/v1/spiders/{spider_id}/items/batch-download/

    将多个 item 文件夹及其内容批量打包为 ZIP 并下载
    """
    print("\n" + "=" * 60)
    print("测试接口 5：批量下载多个 item 的 ZIP 文件包")
    print("=" * 60)

    url = f"{BASE_URL}/{spider_id}/items/batch-download/"
    print(f"请求地址: {url}")
    print(f"请求方法: POST")
    print(f"spider_id: {spider_id}")
    print(f"item_ids: {item_ids}")

    payload = {"item_ids": item_ids}
    print(f"请求体: {payload}")

    os.makedirs(output_dir, exist_ok=True)

    try:
        response = requests.post(url, json=payload, timeout=120)
        print(f"响应状态码: {response.status_code}")

        if response.status_code == 200:
            content_type = response.headers.get("Content-Type", "")
            if "application/json" in content_type:
                data = response.json()
                if data.get("success") is False:
                    print(f"请求失败: {data.get('error')}")
                    if "missing_item_ids" in data:
                        print(f"缺失的 item_ids: {data['missing_item_ids']}")
                    return False

            filename = response.headers.get("Content-Disposition", "").split("filename=")[-1].strip('"')
            if not filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"{spider_id}_batch_{timestamp}.zip"

            filepath = os.path.join(output_dir, filename)
            with open(filepath, "wb") as f:
                f.write(response.content)

            file_size = os.path.getsize(filepath)
            print(f"文件已保存: {filepath}")
            print(f"文件大小: {file_size} 字节")
            print(f"包含 {len(item_ids)} 个项目的文件")
            return True
        elif response.status_code == 400:
            error_data = response.json()
            print(f"请求失败: {error_data.get('error')}")
            return False
        elif response.status_code == 404:
            error_data = response.json()
            print(f"请求失败: {error_data.get('error')}")
            return False
        else:
            print(f"请求失败，状态码: {response.status_code}")
            return False

    except requests.exceptions.RequestException as e:
        print(f"请求异常: {e}")
        return False


def run_all_tests() -> dict:
    """
    运行所有 API 测试用例

    Returns:
        dict: 测试结果汇总
    """
    print("\n" + "#" * 60)
    print("# 爬虫管理 API 接口测试")
    print("#" * 60)
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"基础 URL: {BASE_URL}")
    print(f"测试 spider_id: {SPIDER_ID}")
    print(f"测试 item_ids: {TEST_ITEM_IDS}")

    results = {}

    results["test_spider_list"] = test_spider_list()
    time.sleep(0.5)

    results["test_spider_detail"] = test_spider_detail(SPIDER_ID)
    time.sleep(0.5)

    results["test_download_config"] = test_download_config(SPIDER_ID)
    time.sleep(0.5)

    if TEST_ITEM_IDS:
        results["test_download_item_zip"] = test_download_item_zip(SPIDER_ID, TEST_ITEM_IDS[0])
        time.sleep(0.5)

        results["test_batch_download_items"] = test_batch_download_items(SPIDER_ID, TEST_ITEM_IDS[:3])
    else:
        print("\n警告: 未提供测试 item_id，跳过接口 4 和 5 的测试")
        results["test_download_item_zip"] = False
        results["test_batch_download_items"] = False

    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)

    passed = 0
    failed = 0
    for test_name, result in results.items():
        status = "通过" if result else "失败"
        print(f"  {test_name}: {status}")
        if result:
            passed += 1
        else:
            failed += 1

    print(f"\n总计: {passed} 个通过，{failed} 个失败")
    print("=" * 60)

    return results


if __name__ == "__main__":
    results = run_all_tests()

    exit_code = 0 if all(results.values()) else 1
    sys.exit(exit_code)
