import requests
import os
import re
import json
import sys
from docx import Document
from pathlib import Path


API_BASE = "http://103.47.81.116:8000"


def convert_doc_to_docx(file_path: str) -> dict:
    if not os.path.exists(file_path):
        return {"success": False, "message": f"文件不存在: {file_path}"}

    if not file_path.lower().endswith('.doc'):
        return {"success": False, "message": "只支持.doc格式文件"}

    with open(file_path, 'rb') as f:
        files = {'file': (os.path.basename(file_path), f, 'application/msword')}
        response = requests.post(
            f'{API_BASE}/api/convert/doc-to-docx',
            files=files,
            verify=False
        )

    if response.status_code == 200:
        result = response.json()
        if result.get('success') and result.get('download_url'):
            download_url = result['download_url']
            if not download_url.startswith('http'):
                download_url = API_BASE + download_url

            base_name = os.path.splitext(os.path.basename(file_path))[0]
            save_path = os.path.join(os.path.dirname(file_path), base_name + ".docx")

            response = requests.get(download_url, verify=False)
            if response.status_code == 200:
                with open(save_path, 'wb') as f:
                    f.write(response.content)
                result['saved_path'] = save_path
        return result
    else:
        return {"success": False, "message": f"请求失败: {response.status_code}"}


def read_docx_file(file_path: str) -> str:
    doc = Document(file_path)
    return '\n'.join([para.text for para in doc.paragraphs])


def parse_docx_text(full_text: str) -> dict:
    abstract = ""
    chapters = []
    current_chapter_no = None
    current_articles = []

    lines = full_text.split("\n")

    chapter_pattern = re.compile(r'^(第[一二三四五六七八九十百千零\d]+章)(.*)')
    article_pattern = re.compile(r'^(第[一二三四五六七八九十百千零\d]+条)(.*)')

    def process_enum_newlines(text: str) -> str:
        result = []
        i = 0
        while i < len(text):
            if text[i] == '（':
                if result and result[-1] != '\n':
                    result.append('\n')
                result.append('（')
                i += 1
            else:
                result.append(text[i])
                i += 1
        return ''.join(result)

    in_abstract = True

    for line in lines:
        line = line.strip()
        if not line:
            continue

        match_chapter = chapter_pattern.match(line)
        match_article = article_pattern.match(line)

        if match_chapter:
            if current_chapter_no and current_articles:
                chapters.append({
                    'chapter_no': current_chapter_no,
                    'articles': current_articles
                })
            in_abstract = False
            chapter_title = match_chapter.group(1)
            chapter_name = match_chapter.group(2).strip() if match_chapter.group(2) else ""
            if chapter_name:
                current_chapter_no = f"{chapter_title} - {chapter_name}"
            else:
                current_chapter_no = chapter_title
            current_articles = []
        elif match_article and in_abstract:
            in_abstract = False
            current_chapter_no = '第一章'
            current_articles = []
            content = match_article.group(2).strip() if match_article.group(2) else ""
            current_articles.append({
                'article_no': match_article.group(1),
                'content': content
            })
        elif in_abstract:
            abstract += line + "\n"
        else:
            if match_article:
                if current_articles:
                    current_articles[-1]['content'] = process_enum_newlines(current_articles[-1]['content'].strip())
                content = match_article.group(2).strip() if match_article.group(2) else ""
                current_articles.append({
                    'article_no': match_article.group(1),
                    'content': content
                })
            else:
                if current_articles:
                    current_articles[-1]['content'] += line + "\n"

    if current_articles:
        current_articles[-1]['content'] = process_enum_newlines(current_articles[-1]['content'].strip())
        if current_chapter_no:
            chapters.append({
                'chapter_no': current_chapter_no,
                'articles': current_articles
            })

    if not chapters and abstract:
        chapters.append({
            'chapter_no': '第一章',
            'articles': []
        })

    abstract = abstract.strip()

    return {
        'abstract': abstract,
        'chapters': chapters
    }


def parse_docx_file(file_path: str) -> dict:
    if not os.path.exists(file_path):
        return {"success": False, "message": f"文件不存在: {file_path}"}

    if not file_path.lower().endswith('.docx'):
        return {"success": False, "message": "只支持.docx格式文件"}

    try:
        full_text = read_docx_file(file_path)
        parsed = parse_docx_text(full_text)

        chapter_num = len(parsed.get('chapters', []))
        article_num = sum(len(ch.get('articles', [])) for ch in parsed.get('chapters', []))

        return {
            "success": True,
            "abstract": parsed.get('abstract', ''),
            "chapters": parsed.get('chapters', []),
            "chapter_num": chapter_num,
            "article_num": article_num
        }
    except Exception as e:
        return {"success": False, "message": f"解析失败: {str(e)}"}


def batch_convert_doc_to_docx(json_file: str, files_dir: str):
    """批量转换flkgov_data.json中只有doc文件的记录"""
    import time

    converted = 0
    skipped_existing = 0
    skipped_no_file = 0
    failed = 0
    no_doc_only = 0

    total = 0
    with open(json_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                total += 1

    print(f"共 {total} 条记录待检查\n")
    print("=" * 60)

    processed = 0
    with open(json_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            try:
                item = json.loads(line)
                item_id = item.get('item_id')
                title = item.get('title', '')[:30]

                item_dir = os.path.join(files_dir, str(item_id))
                doc_file = os.path.join(item_dir, f"{item_id}_1.doc")
                docx_file = os.path.join(item_dir, f"{item_id}_1.docx")

                processed += 1

                if os.path.exists(docx_file):
                    skipped_existing += 1
                elif os.path.exists(doc_file):
                    print(f"[{processed}/{total}] {item_id} | {title:<30} | 转换中...")
                    for retry in range(3):
                        try:
                            result = convert_doc_to_docx(doc_file)
                            if result.get('success'):
                                saved_path = result.get('saved_path', '')
                                print(f"  -> 成功: {saved_path}")
                                converted += 1
                                break
                            else:
                                if retry < 2:
                                    time.sleep(2)
                                else:
                                    print(f"  -> 失败: {result.get('message')}")
                                    failed += 1
                        except Exception as e:
                            if retry < 2:
                                time.sleep(2)
                            else:
                                print(f"  -> 异常: {str(e)}")
                                failed += 1
                else:
                    if not os.path.exists(item_dir):
                        skipped_no_file += 1
                    else:
                        no_doc_only += 1

                if processed % 500 == 0 or processed == total:
                    print(f"[{processed}/{total}] 进度: {processed*100//total}%")

            except json.JSONDecodeError:
                continue

    print("=" * 60)
    print(f"【统计结果】")
    print(f"  总记录:        {total}")
    print(f"  成功转换:      {converted}")
    print(f"  已有docx跳过:  {skipped_existing}")
    print(f"  文件夹不存在:  {skipped_no_file}")
    print(f"  无doc文件:     {no_doc_only}")
    print(f"  转换失败:      {failed}")
    print("=" * 60)


if __name__ == "__main__":
    JSON_FILE = r"E:\spider_manager\data\flkgov\flkgov_data.json"
    FILES_DIR = r"E:\spider_manager\data\flkgov\flkgov_files"

    if len(sys.argv) > 1 and sys.argv[1] == 'convert':
        batch_convert_doc_to_docx(JSON_FILE, FILES_DIR)
    else:
        import json

        base_path = r"E:\spider_manager\1772992368088_1"
        doc_file = base_path + ".doc"
        docx_file = base_path + ".docx"

        if os.path.exists(docx_file):
            print(f"docx文件已存在: {docx_file}")
            target_file = docx_file
        elif os.path.exists(doc_file):
            print(f"正在转换doc为docx: {doc_file}")
            result = convert_doc_to_docx(doc_file)
            if result.get('success'):
                target_file = result.get('saved_path', docx_file)
                print(f"转换成功: {target_file}")
            else:
                print(f"转换失败: {result.get('message')}")
                exit(1)
        else:
            print(f"文件不存在: doc和docx都不存在")
            exit(1)

        print(f"\n正在解析: {target_file}")
        result = parse_docx_file(target_file)

        print(f"\n=== 完整解析结果 ===")
        print(json.dumps(result, ensure_ascii=False, indent=2))
