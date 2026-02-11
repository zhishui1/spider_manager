from pathlib import Path

base = Path('data/nhsa/nhsa_files')
count = 0
prefix_files = []
for f in base.rglob('*'):
    if f.is_file() and f.name.startswith('2'):
        count += 1
        prefix_files.append(str(f))

print(f'Files with 2 prefix: {count}')
for f in prefix_files[:10]:
    print(f'  {f}')
