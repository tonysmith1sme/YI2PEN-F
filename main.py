import os
import subprocess
import sys
import urllib.request
import zipfile
import shutil
import re
import time

# --- 配置区域 ---
# 官方 RSS 用于获取版本号
RSS_URL = "https://exiftool.org/rss.xml"
# 备用版本
FALLBACK_VERSION = "13.10"

# 路径定义
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# 我们的目标是：项目根目录/ExifTool/exiftool.exe
EXIFTOOL_DIR = os.path.join(BASE_DIR, "ExifTool")
EXIFTOOL_EXE_PATH = os.path.join(EXIFTOOL_DIR, "exiftool.exe")

def get_latest_version():
    """从官网 RSS 获取最新版本号"""
    print(">>> 正在检测 ExifTool 最新版本...")
    try:
        with urllib.request.urlopen(RSS_URL, timeout=10) as response:
            data = response.read().decode('utf-8')
            match = re.search(r"ExifTool (\d+\.\d+)", data)
            if match:
                version = match.group(1)
                print(f"    检测到最新版本: {version}")
                return version
    except Exception as e:
        print(f"    版本检测失败 ({e})，使用备用版本。")
    return FALLBACK_VERSION

def setup_exiftool():
    """
    下载 -> 全量解压 -> 智能移动文件 -> 重命名
    """
    print("="*50)
    print("【系统检测】正在初始化 ExifTool 环境...")
    
    # 1. 如果存在旧文件夹，先清理，确保干净安装
    if os.path.exists(EXIFTOOL_DIR):
        print("    清理旧文件...")
        try:
            shutil.rmtree(EXIFTOOL_DIR)
        except Exception as e:
            print(f"!!! 警告: 无法删除旧文件夹，请手动删除 {EXIFTOOL_DIR}")
            return False
            
    os.makedirs(EXIFTOOL_DIR)

    # 2. 下载
    version = get_latest_version()
    # 优先下载 64位 Windows 包 (包含 exiftool(-k).exe 和可能的 exiftool_files)
    url = f"https://exiftool.org/exiftool-{version}_64.zip"
    zip_path = os.path.join(BASE_DIR, "temp_exiftool.zip") # 下载到根目录，防止占用ExifTool文件夹

    print(f"【下载地址】{url}")
    print(">>> 正在下载... (请稍候)")
    
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response, open(zip_path, 'wb') as out_file:
            shutil.copyfileobj(response, out_file)
            
        # 简单校验
        with open(zip_path, 'rb') as f:
            if f.read(2) != b'PK':
                print("!!! 错误: 下载的文件不是ZIP。")
                return False
                
    except Exception as e:
        print(f"!!! 下载失败: {e}")
        return False

    # 3. 解压所有文件
    print(">>> 正在解压完整包...")
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(EXIFTOOL_DIR)
            
        # 4. 【关键步骤】处理目录结构
        # 通常 zip 解压后会有一个主文件夹，例如 ExifTool/exiftool-13.48_64/...
        # 我们需要把里面的东西移出来
        
        items = os.listdir(EXIFTOOL_DIR)
        # 如果只有一个文件夹 (例如 exiftool-13.48_64)
        if len(items) == 1 and os.path.isdir(os.path.join(EXIFTOOL_DIR, items[0])):
            subdir_name = items[0]
            subdir_path = os.path.join(EXIFTOOL_DIR, subdir_name)
            
            print(f"    正在调整目录结构 (从 {subdir_name} 移出)...")
            
            # 将子目录下的所有文件和文件夹移动到 EXIFTOOL_DIR
            for sub_item in os.listdir(subdir_path):
                src = os.path.join(subdir_path, sub_item)
                dst = os.path.join(EXIFTOOL_DIR, sub_item)
                shutil.move(src, dst)
            
            # 删除空的子目录
            os.rmdir(subdir_path)

        # 5. 重命名 exiftool(-k).exe -> exiftool.exe
        # 还要注意检查是否存在 exiftool_files 文件夹，这一步是自然存在的，因为我们做了全量解压
        
        found_exe = False
        possible_exes = ["exiftool(-k).exe", "exiftool.exe"]
        
        for exe_name in possible_exes:
            current_exe_path = os.path.join(EXIFTOOL_DIR, exe_name)
            if os.path.exists(current_exe_path):
                # 如果叫 (-k) 就改名
                if "(-k)" in exe_name:
                    shutil.move(current_exe_path, EXIFTOOL_EXE_PATH)
                    print(f"    已重命名: {exe_name} -> exiftool.exe")
                else:
                    print(f"    找到执行文件: {exe_name}")
                found_exe = True
                break
        
        if not found_exe:
            print("!!! 错误: 解压后未找到 exiftool(-k).exe。")
            return False

        # 检查是否有 exiftool_files (可选检查，为了确认)
        if os.path.exists(os.path.join(EXIFTOOL_DIR, "exiftool_files")):
            print("    已保留运行库文件夹: exiftool_files")

    except Exception as e:
        print(f"!!! 解压或配置文件失败: {e}")
        return False
    finally:
        # 清理 ZIP 包
        if os.path.exists(zip_path):
            os.remove(zip_path)

    print(f"✅ ExifTool 安装完成！路径: {EXIFTOOL_EXE_PATH}")
    print("="*50 + "\n")
    return True

def get_exiftool_path():
    """获取路径，不存在则安装"""
    if os.path.exists(EXIFTOOL_EXE_PATH):
        return EXIFTOOL_EXE_PATH
    
    if setup_exiftool():
        return EXIFTOOL_EXE_PATH
    else:
        return None

def modify_dng_with_exiftool(directory_path):
    exiftool_path = get_exiftool_path()
    
    if exiftool_path is None:
        return

    print(f"--- 开始扫描目录: {directory_path} ---")
    
    new_make = "OLYMPUS CORPORATION"
    new_model = "PEN-F"
    count_processed = 0
    
    for root, dirs, files in os.walk(directory_path):
        for filename in files:
            # 排除已生成的 _PEN 文件
            if filename.lower().endswith(".dng") and "_PEN" not in filename:
                filepath = os.path.join(root, filename)
                count_processed += 1
                
                file_base, file_ext = os.path.splitext(filename)
                new_filename = f"{file_base}_PEN{file_ext}"
                new_filepath = os.path.join(root, new_filename)

                cmd = [
                    exiftool_path,
                    "-m",
                    "-if", "$Make =~ /YI/i",
                    "-if", "$Model =~ /M1/i",
                    f"-Make={new_make}",
                    f"-Model={new_model}",
                    "-o", new_filepath,
                    filepath
                ]

                try:
                    startupinfo = None
                    if os.name == 'nt':
                        startupinfo = subprocess.STARTUPINFO()
                        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                    
                    result = subprocess.run(
                        cmd, 
                        stdout=subprocess.PIPE, 
                        stderr=subprocess.PIPE, 
                        text=True,
                        encoding='utf-8', 
                        errors='ignore',
                        startupinfo=startupinfo
                    )
                    
                    output = result.stdout.strip()
                    
                    if "1 image files created" in output:
                        print(f"[成功生成] {new_filename}")
                    elif "failed condition" in output:
                        print(f"[跳过] {filename} (非 YI M1 相机)")
                    elif "Error" in output:
                        print(f"[ExifTool报错] {filename}: {output}")
                    else:
                        if output: print(f"[消息] {output}")

                except Exception as e:
                    print(f"[Python异常] {e}")

    print(f"\n--- 处理完成 ---")
    print(f"扫描源文件数: {count_processed}")

if __name__ == "__main__":
    os.system('cls' if os.name == 'nt' else 'clear')
    print("ExifTool DNG 修改助手 (完整包安装版)")
    print("-" * 30)
    
    # 检测是否需要重新安装 (如果是之前的错误安装，文件夹结构可能不对)
    # 如果 ExifTool 文件夹下没有 exe，或者有 exe 但无法运行，这里会通过 setup_exiftool 重新覆盖
    
    target_dir = input("请输入包含DNG文件的文件夹路径: ").strip()
    target_dir = target_dir.strip('"').strip("'")

    if os.path.isdir(target_dir):
        modify_dng_with_exiftool(target_dir)
    else:
        print("错误: 输入的路径不存在。")