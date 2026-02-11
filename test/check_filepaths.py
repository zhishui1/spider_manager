"""
检查 nhsa_data.json 中的 file_paths 格式
"""
import json
from pathlib import Path

data_file = Path(__file__).resolve().parent.parent / 'data' / 'nhsa' / 'nhsa_data.json'

if not data_file.exists():
    print(f"文件不存在: {data_file}")
    exit(1)

print(f"检查文件: {data_file}\n")

with open(data_file, 'r', encoding='utf-8') as f:
    for i, line in enumerate(f, 1):
        if i > 5:
            break
        line = line.strip()
        if not line:
            continue
        try:
            data = json.loads(line)
            file_paths = data.get('file_paths', [])
            if file_paths:
                print(f"第{i}行 file_paths 示例:")
                for path in file_paths[:3]:
                    print(f"  {path}")
                print()
        except json.JSONDecodeError:
            pass
