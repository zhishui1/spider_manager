"""
删除 file_paths 中的文件名前缀 "2"
"""
import json
from pathlib import Path

DATA_FILE = Path(__file__).resolve().parent.parent / 'data' / 'nhsa' / 'nhsa_data.json'


def remove_prefix_from_filenames():
    if not DATA_FILE.exists():
        print(f"文件不存在: {DATA_FILE}")
        return

    print(f"读取文件: {DATA_FILE}")

    lines = DATA_FILE.read_text(encoding='utf-8').strip().split('\n')
    print(f"共 {len(lines)} 条记录")

    modified_count = 0
    path_count = 0

    for i, line in enumerate(lines):
        try:
            data = json.loads(line)
            if 'file_paths' in data:
                original_paths = data['file_paths']
                new_paths = []
                for p in original_paths:
                    filename = Path(p).name
                    if filename.startswith('2') and len(filename) > 1:
                        new_filename = filename[1:]
                        new_path = str(Path(p).parent / new_filename)
                        new_paths.append(new_path)
                        path_count += 1
                    else:
                        new_paths.append(p)

                if original_paths != new_paths:
                    data['file_paths'] = new_paths
                    modified_count += 1
                    lines[i] = json.dumps(data, ensure_ascii=False)

            if (i + 1) % 50 == 0:
                print(f"  已处理 {i + 1}/{len(lines)} 条记录...")
        except json.JSONDecodeError as e:
            print(f"  JSON解析错误 at line {i + 1}: {e}")
            continue

    print(f"\n处理完成:")
    print(f"  修改记录数: {modified_count}")
    print(f"  删除前缀的路径数: {path_count}")

    backup_path = DATA_FILE.with_suffix('.json.bak')
    if backup_path.exists():
        backup_path.unlink()
    DATA_FILE.rename(backup_path)
    print(f"  备份文件: {backup_path}")

    DATA_FILE.write_text('\n'.join(lines), encoding='utf-8')
    print(f"  新文件: {DATA_FILE}")


if __name__ == '__main__':
    remove_prefix_from_filenames()
