"""
处理 flkgov_data.json 数据，按行读取并解析 docx 文件
边解析边按行写入目标 jsonines 文件
"""
import json
import re
from pathlib import Path
from docx import Document
import sys

DATA_DIR = Path(r"E:\spider_manager\data\flkgov")
JSON_FILE = DATA_DIR / "flkgov_data.json"
FILES_DIR = DATA_DIR / "flkgov_files"

REGULATIONS_OUTPUT = DATA_DIR / "flkgov_regulations.json"
ARTICLES_OUTPUT = DATA_DIR / "flkgov_articles.json"
INVALID_OUTPUT = DATA_DIR / "flkgov_invalid.json"


def read_doc_file(file_path: str) -> str:
    """读取doc或docx文件内容"""
    file_path_obj = Path(file_path)
    try:
        if file_path_obj.suffix.lower() == '.docx':
            doc = Document(file_path)
            return '\n'.join([para.text for para in doc.paragraphs])
        elif file_path_obj.suffix.lower() == '.doc':
            try:
                import win32com.client
                word = win32com.client.Dispatch("Word.Application")
                word.Visible = False
                word.DisplayAlerts = False
                try:
                    doc = word.Documents.Open(str(file_path_obj.absolute()))
                    text = doc.Content.Text
                    doc.Close(False)
                    return text
                finally:
                    word.Quit()
            except Exception:
                return ""
        return ""
    except Exception:
        return ""


def parse_docx_text(full_text: str) -> dict:
    """解析文档内容，提取摘要、章节和条目"""
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


def process_item(line: str) -> dict:
    """处理单条记录"""
    item = json.loads(line)

    item_id = item.get('item_id')
    title = item.get('title')
    url = item.get('url')

    data = item.get('data', {})
    regulation_type = data.get('regulation_type', '')
    issuing_body = data.get('issuing_body', '')
    promulgation_date = data.get('promulgation_date')
    effective_date = data.get('effective_date')
    status = data.get('status', '')

    item_files_dir = FILES_DIR / str(item_id)
    abstract = ""
    chapters = []
    chapter_num = 0
    article_num = 0
    has_docx = False

    if item_files_dir.exists():
        docx_files = list(item_files_dir.glob("*.docx"))
        if docx_files:
            has_docx = True
            try:
                full_text = read_doc_file(str(docx_files[0]))
                parsed = parse_docx_text(full_text)
                abstract = parsed.get('abstract', '')
                chapters = parsed.get('chapters', [])
                chapter_num = len(chapters)
                article_num = sum(len(ch.get('articles', [])) for ch in chapters)
            except Exception as e:
                print(f"  解析文件失败: {e}")

    regulation = {
        'item_id': str(item_id),
        'url': url,
        'title': title,
        'regulation_type': regulation_type,
        'issuing_body': issuing_body,
        'promulgation_date': promulgation_date,
        'effective_date': effective_date,
        'status': status,
        'abstract': abstract,
        'chapter_num': chapter_num,
        'article_num': article_num,
        'has_docx': has_docx
    }

    articles = []
    if has_docx:
        for chapter in chapters:
            chapter_no = chapter.get('chapter_no', '')
            for article in chapter.get('articles', []):
                articles.append({
                    'regulation_id': item_id,
                    'chapter_no': chapter_no,
                    'article_no': article.get('article_no', ''),
                    'content': article.get('content', '')
                })

    return {
        'regulation': regulation,
        'articles': articles,
        'is_invalid': not has_docx or ('决定' in regulation_type) or (chapter_num == 0 and article_num == 0)
    }


def main():
    if not JSON_FILE.exists():
        print(f"错误: JSON文件不存在: {JSON_FILE}")
        return

    if not FILES_DIR.exists():
        print(f"错误: 文件目录不存在: {FILES_DIR}")
        return

    print("=" * 60)
    print("开始处理 flkgov_data.json (流式写入)")
    print("=" * 60)
    print(f"输入文件: {JSON_FILE}")
    print(f"文件目录: {FILES_DIR}")
    print(f"输出文件:")
    print(f"  法规: {REGULATIONS_OUTPUT}")
    print(f"  条款: {ARTICLES_OUTPUT}")
    print(f"  无效: {INVALID_OUTPUT}")
    print("=" * 60)

    total_lines = 0
    with open(JSON_FILE, 'r', encoding='utf-8') as f:
        total_lines = sum(1 for _ in f)

    print(f"总记录数: {total_lines}")
    print("=" * 60)

    reg_count = 0
    art_count = 0
    invalid_count = 0

    with open(REGULATIONS_OUTPUT, 'w', encoding='utf-8') as reg_f, \
         open(ARTICLES_OUTPUT, 'w', encoding='utf-8') as art_f, \
         open(INVALID_OUTPUT, 'w', encoding='utf-8') as inv_f:

        with open(JSON_FILE, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue

                try:
                    result = process_item(line)

                    if result['is_invalid']:
                        inv_line = json.dumps(result['regulation'], ensure_ascii=False)
                        inv_f.write(inv_line + '\n')
                        inv_f.flush()
                        invalid_count += 1
                    else:
                        reg_line = json.dumps(result['regulation'], ensure_ascii=False)
                        reg_f.write(reg_line + '\n')
                        reg_f.flush()
                        reg_count += 1

                        for article in result['articles']:
                            art_line = json.dumps(article, ensure_ascii=False)
                            art_f.write(art_line + '\n')
                            art_f.flush()
                            art_count += 1

                    if line_num % 1000 == 0:
                        print(f"进度: {line_num}/{total_lines} ({line_num*100//total_lines}%)")

                except json.JSONDecodeError as e:
                    print(f"JSON解析错误 (行 {line_num}): {e}")
                    continue
                except Exception as e:
                    print(f"处理错误 (行 {line_num}): {e}")
                    continue

    print("=" * 60)
    print("处理完成！统计信息：")
    print("=" * 60)
    print(f"总记录数:     {total_lines}")
    print(f"法规记录数:   {reg_count}")
    print(f"条款记录数:   {art_count}")
    print(f"无效记录数:   {invalid_count}")
    print("=" * 60)


if __name__ == "__main__":
    main()
