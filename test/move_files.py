"""
将 nhsa_files 根目录下的文件移动到 archive 子目录
"""
import shutil
from pathlib import Path

def move_files_to_archive():
    nhsa_files = Path(__file__).resolve().parent.parent / 'data' / 'nhsa' / 'nhsa_files'
    archive_dir = nhsa_files / 'archive'
    
    if not nhsa_files.exists():
        print(f"目录不存在: {nhsa_files}")
        return
    
    if not archive_dir.exists():
        archive_dir.mkdir(parents=True, exist_ok=True)
        print(f"创建目录: {archive_dir}")
    
    moved_count = 0
    for file_path in nhsa_files.iterdir():
        if file_path.is_file() and file_path.name != 'nhsa_data.json.bak':
            new_path = archive_dir / file_path.name
            if not new_path.exists():
                shutil.move(str(file_path), str(new_path))
                print(f"  移动: {file_path.name}")
                moved_count += 1
            else:
                print(f"  跳过（已存在）: {file_path.name}")
    
    print(f"\n完成! 共移动 {moved_count} 个文件")

if __name__ == '__main__':
    move_files_to_archive()
