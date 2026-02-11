"""
修复 nhsa_data.json 中的 file_paths 路径
将 nhsa_files 后面的路径添加 archive/
"""
import json
import re
from pathlib import Path

def fix_file_paths():
    script_dir = Path(__file__).resolve().parent
    base_dir = script_dir.parent
    data_file = base_dir / 'data' / 'nhsa' / 'nhsa_data.json'
    
    if not data_file.exists():
        print(f"文件不存在: {data_file}")
        return
    
    print(f"处理文件: {data_file}")
    
    fixed_count = 0
    total_count = 0
    
    with open(data_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    fixed_lines = []
    for line_num, line in enumerate(lines, 1):
        line = line.strip()
        if not line:
            continue
        
        total_count += 1
        
        try:
            data = json.loads(line)
            file_paths = data.get('file_paths', [])
            
            if file_paths and isinstance(file_paths, list):
                new_paths = []
                path_changed = False
                
                for path in file_paths:
                    # 处理 Windows 绝对路径
                    new_path = re.sub(
                        r'([A-Za-z]:\\[^\n]+\\nhsa_files)([\\/])',
                        r'\1\\archive\\2',
                        path
                    )
                    new_paths.append(new_path)
                    if new_path != path:
                        path_changed = True
                
                if path_changed:
                    data['file_paths'] = new_paths
                    fixed_count += 1
                    print(f"  第{line_num}行: 修复路径 {len(new_paths)} 个")
                    fixed_lines.append(json.dumps(data, ensure_ascii=False))
                else:
                    fixed_lines.append(line)
            else:
                fixed_lines.append(line)
                
        except json.JSONDecodeError as e:
            print(f"  第{line_num}行: JSON解析错误 - {e}")
            fixed_lines.append(line)
    
    if fixed_count > 0:
        backup_file = data_file.with_suffix('.json.bak')
        data_file.rename(backup_file)
        print(f"\n备份原文件: {backup_file}")
        
        with open(data_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(fixed_lines))
            if fixed_lines:
                f.write('\n')
        
        print(f"\n修复完成!")
        print(f"  总行数: {total_count}")
        print(f"  修复行数: {fixed_count}")
    else:
        print("\n无需修复，所有路径已是正确的")

if __name__ == '__main__':
    fix_file_paths()
