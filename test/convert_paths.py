"""
将 nhsa_data.json 中的绝对路径转换为相对路径
"""
import json
from pathlib import Path

DATA_FILE = Path(__file__).resolve().parent.parent / 'data' / 'nhsa' / 'nhsa_data.json'


def to_relative_path(absolute_path: str) -> str:
    """将绝对路径转换为相对于项目根目录的相对路径"""
    abs_path = Path(absolute_path)
    try:
        project_root = Path(__file__).resolve().parent.parent
        rel_path = abs_path.relative_to(project_root)
        return str(rel_path).replace('\\', '/')
    except ValueError:
        return str(abs_path).replace('\\', '/')


def convert_data_file():
    if not DATA_FILE.exists():
        print(f"文件不存在: {DATA_FILE}")
        return

    print(f"读取文件: {DATA_FILE}")

    lines = DATA_FILE.read_text(encoding='utf-8').strip().split('\n')
    print(f"共 {len(lines)} 条记录")

    converted_count = 0
    path_count = 0

    for i, line in enumerate(lines):
        try:
            data = json.loads(line)
            if 'file_paths' in data:
                original_paths = data['file_paths']
                new_paths = [to_relative_path(p) for p in original_paths]
                if original_paths != new_paths:
                    data['file_paths'] = new_paths
                    converted_count += 1
                    path_count += len(original_paths)
                    lines[i] = json.dumps(data, ensure_ascii=False)

            if (i + 1) % 50 == 0:
                print(f"  已处理 {i + 1}/{len(lines)} 条记录...")
        except json.JSONDecodeError as e:
            print(f"  JSON解析错误 at line {i + 1}: {e}")
            continue

    print(f"\n转换完成:")
    print(f"  修改记录数: {converted_count}")
    print(f"  转换路径数: {path_count}")

    backup_path = DATA_FILE.with_suffix('.json.bak')
    if backup_path.exists():
        backup_path.unlink()
    DATA_FILE.rename(backup_path)
    print(f"  备份文件: {backup_path}")

    DATA_FILE.write_text('\n'.join(lines), encoding='utf-8')
    print(f"  新文件: {DATA_FILE}")


if __name__ == '__main__':
    convert_data_file()
