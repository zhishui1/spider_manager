import json
import psycopg2
from psycopg2.extras import execute_values
from pathlib import Path



conn = psycopg2.connect(**DB_CONFIG)
cur = conn.cursor()

cur.execute("""
    SELECT COUNT(*) FROM information_schema.tables
    WHERE table_name = 'flkgov_regulations'
""")
if cur.fetchone()[0] == 0:
    cur.execute('''
        CREATE TABLE flkgov_regulations (
            id SERIAL PRIMARY KEY,
            item_id VARCHAR(50),
            url VARCHAR(1000),
            title VARCHAR(1000),
            regulation_type VARCHAR(100),
            issuing_body VARCHAR(500),
            promulgation_date DATE,
            effective_date DATE,
            status VARCHAR(20),
            abstract TEXT,
            chapter_num INT,
            article_num INT
        );
    ''')
    print("表 flkgov_regulations 创建完成")
else:
    print("表 flkgov_regulations 已存在，跳过创建")

cur.execute("""
    SELECT COUNT(*) FROM information_schema.tables
    WHERE table_name = 'flkgov_articles'
""")
if cur.fetchone()[0] == 0:
    cur.execute('''
        CREATE TABLE flkgov_articles (
            id SERIAL PRIMARY KEY,
            regulation_id INT REFERENCES flkgov_regulations(id),
            chapter_no VARCHAR(100),
            article_no VARCHAR(100),
            content TEXT
        );
    ''')
    print("表 flkgov_articles 创建完成")
else:
    print("表 flkgov_articles 已存在，跳过创建")

cur.execute("""
    SELECT COUNT(*) FROM pg_indexes
    WHERE indexname = 'idx_regulations_title'
""")
if cur.fetchone()[0] == 0:
    cur.execute("CREATE INDEX idx_regulations_title ON flkgov_regulations(title);")
    print("索引 idx_regulations_title 创建完成")
else:
    print("索引 idx_regulations_title 已存在，跳过创建")

cur.execute("""
    SELECT COUNT(*) FROM pg_indexes
    WHERE indexname = 'idx_articles_regulation_id'
""")
if cur.fetchone()[0] == 0:
    cur.execute("CREATE INDEX idx_articles_regulation_id ON flkgov_articles(regulation_id);")
    print("索引 idx_articles_regulation_id 创建完成")
else:
    print("索引 idx_articles_regulation_id 已存在，跳过创建")

conn.commit()
print("表和索引检查完成!")


def count_lines(json_path):
    count = 0
    with open(json_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                count += 1
    return count


def import_regulations(json_path):
    item_id_to_db_id = {}

    total = count_lines(json_path)
    print(f"\n导入法规表，共 {total} 条...")

    batch = []
    batch_size = 1000
    processed = 0

    with open(json_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            row = json.loads(line)
            batch.append((
                str(row.get('item_id', '')),
                row.get('url', '')[:1000] if row.get('url') else '',
                row.get('title', '')[:1000] if row.get('title') else '',
                row.get('regulation_type', ''),
                row.get('issuing_body', '')[:500] if row.get('issuing_body') else '',
                row.get('promulgation_date'),
                row.get('effective_date'),
                row.get('status', ''),
                row.get('abstract', ''),
                row.get('chapter_num', 0),
                row.get('article_num', 0)
            ))

            if len(batch) >= batch_size:
                query = """
                    INSERT INTO flkgov_regulations
                    (item_id, url, title, regulation_type, issuing_body,
                     promulgation_date, effective_date, status, abstract, chapter_num, article_num)
                    VALUES %s
                    RETURNING id, item_id
                """
                result = execute_values(cur, query, batch, fetch=True)

                for db_id, item_id in result:
                    item_id_to_db_id[str(item_id)] = db_id

                conn.commit()
                processed += len(batch)
                print(f"  进度: {processed}/{total}")
                batch = []

        if batch:
            query = """
                INSERT INTO flkgov_regulations
                (item_id, url, title, regulation_type, issuing_body,
                 promulgation_date, effective_date, status, abstract, chapter_num, article_num)
                VALUES %s
                RETURNING id, item_id
            """
            result = execute_values(cur, query, batch, fetch=True)

            for db_id, item_id in result:
                item_id_to_db_id[str(item_id)] = db_id

            conn.commit()
            processed += len(batch)
            print(f"  进度: {processed}/{total}")

    print(f"法规表完成! 共 {len(item_id_to_db_id)} 条")
    return item_id_to_db_id


def import_articles(json_path, item_id_to_db_id):
    total = count_lines(json_path)
    print(f"\n导入条目表，共 {total} 条...")

    batch = []
    batch_size = 1000
    processed = 0

    with open(json_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            row = json.loads(line)
            item_id = str(row.get('regulation_id', ''))
            db_id = item_id_to_db_id.get(item_id)

            if db_id is None:
                continue

            batch.append((
                db_id,
                row.get('chapter_no', ''),
                row.get('article_no', ''),
                row.get('content', '')
            ))

            if len(batch) >= batch_size:
                query = """
                    INSERT INTO flkgov_articles
                    (regulation_id, chapter_no, article_no, content)
                    VALUES %s
                """
                execute_values(cur, query, batch)
                conn.commit()
                processed += len(batch)
                print(f"  进度: {processed}/{total}")
                batch = []

        if batch:
            query = """
                INSERT INTO flkgov_articles
                (regulation_id, chapter_no, article_no, content)
                VALUES %s
            """
            execute_values(cur, query, batch)
            conn.commit()
            processed += len(batch)
            print(f"  进度: {processed}/{total}")

    print(f"条目表完成! 共 {processed} 条")


reg_output = Path(r'E:\spider_manager\data\flkgov\flkgov_regulations.json')
art_output = Path(r'E:\spider_manager\data\flkgov\flkgov_articles.json')

item_id_to_db_id = import_regulations(reg_output)
import_articles(art_output, item_id_to_db_id)

cur.close()
conn.close()
print("\n全部完成!")
