from pathlib import Path
import json

data_file = Path('data/nhsa/nhsa_data.json')
lines = data_file.read_text(encoding='utf-8').strip().split('\n')

def has_2_prefix(name):
    """检查是否以'2'开头但不是年份（如'2024'）"""
    if not name.startswith('2'):
        return False
    if len(name) > 1 and name[1].isdigit():
        return False  # 是年份，如"2024年"
    return True  # 是我们要删除的"2"前缀

count_with_2 = 0
for i, line in enumerate(lines):
    data = json.loads(line)
    if 'file_paths' in data:
        for p in data['file_paths']:
            filename = Path(p).name
            if has_2_prefix(filename):
                count_with_2 += 1
                if count_with_2 <= 10:
                    print(f'Line {i+1}: {filename[:60]}')

print(f'\nTotal paths with 2 prefix (not year): {count_with_2}')
