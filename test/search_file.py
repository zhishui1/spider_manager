from pathlib import Path
import json

data_file = Path('data/nhsa/nhsa_data.json')
lines = data_file.read_text(encoding='utf-8').strip().split('\n')

for i, line in enumerate(lines):
    if '骨、软骨' in line:
        data = json.loads(line)
        print(f'Line {i+1}:')
        print(f'  标题: {data.get("标题", "")}')
        print(f'  file_paths: {data.get("file_paths", [])}')
