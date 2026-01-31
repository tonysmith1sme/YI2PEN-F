import os
import subprocess
import sys
import urllib.request
import zipfile
import shutil
import re
import threading
import tkinter as tk
from tkinter import filedialog, scrolledtext, messagebox

class DngConverterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("YI2PEN-F DNG 转换器")
        self.root.geometry("600x450")
        
        # --- 配置与常量 ---
        self.RSS_URL = "https://exiftool.org/rss.xml"
        self.FALLBACK_VERSION = "13.10"
        self.BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        self.EXIFTOOL_DIR = os.path.join(self.BASE_DIR, "ExifTool")
        self.EXIFTOOL_EXE_PATH = os.path.join(self.EXIFTOOL_DIR, "exiftool.exe")
        
        self.target_dir = ""
        self.is_running = False

        # --- 界面布局 ---
        self.create_widgets()

    def create_widgets(self):
        # 1. 顶部：文件夹选择区域
        top_frame = tk.Frame(self.root, pady=10)
        top_frame.pack(fill=tk.X, padx=10)

        tk.Label(top_frame, text="目标文件夹:").pack(side=tk.LEFT)
        
        self.path_entry = tk.Entry(top_frame)
        self.path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        btn_browse = tk.Button(top_frame, text="浏览...", command=self.select_folder)
        btn_browse.pack(side=tk.LEFT)

        # 2. 中部：操作按钮
        action_frame = tk.Frame(self.root, pady=5)
        action_frame.pack(fill=tk.X, padx=10)
        
        self.btn_start = tk.Button(action_frame, text="开始处理", command=self.start_thread, 
                                   bg="#dddddd", height=2, width=20)
        self.btn_start.pack()

        # 3. 底部：日志输出区域
        log_frame = tk.Frame(self.root, pady=5)
        # --- 修复点：将 bottom=tk.BOTTOM 修改为 side=tk.BOTTOM ---
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10, side=tk.BOTTOM)
        
        tk.Label(log_frame, text="运行日志:").pack(anchor=tk.W)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, state='disabled', height=10)
        self.log_text.pack(fill=tk.BOTH, expand=True)

    def log(self, message):
        """线程安全的日志输出方法"""
        self.log_text.config(state='normal')
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END) # 自动滚动到底部
        self.log_text.config(state='disabled')

    def select_folder(self):
        path = filedialog.askdirectory()
        if path:
            self.target_dir = path
            self.path_entry.delete(0, tk.END)
            self.path_entry.insert(0, path)

    def start_thread(self):
        """启动后台线程，防止界面卡死"""
        folder = self.path_entry.get().strip()
        if not folder or not os.path.isdir(folder):
            messagebox.showerror("错误", "请先选择有效的文件夹路径！")
            return

        if self.is_running:
            return

        self.btn_start.config(state='disabled', text="处理中...")
        self.is_running = True
        
        # 开启新线程运行核心逻辑
        thread = threading.Thread(target=self.run_process, args=(folder,))
        thread.daemon = True
        thread.start()

    def run_process(self, directory_path):
        """核心业务逻辑（运行在子线程）"""
        try:
            # 1. 检查/安装 ExifTool
            exiftool_path = self.get_exiftool_path()
            
            if not exiftool_path:
                self.log("【严重错误】ExifTool 初始化失败，任务终止。")
                return

            # 2. 开始处理图片
            self.log(f"--- 开始扫描目录: {directory_path} ---")
            
            new_make = "OLYMPUS CORPORATION"
            new_model = "PEN-F"
            count_processed = 0
            count_total_dng = 0

            for root, dirs, files in os.walk(directory_path):
                for filename in files:
                    # 排除已生成的 _PEN 文件
                    if filename.lower().endswith(".dng") and "_PEN" not in filename:
                        count_total_dng += 1
                        filepath = os.path.join(root, filename)
                        
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
                            # 隐藏黑框
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
                                self.log(f"[成功] {filename} -> {new_filename}")
                                count_processed += 1
                            elif "failed condition" in output:
                                self.log(f"[跳过] {filename} (非 YI M1 相机)")
                            elif "Error" in output:
                                self.log(f"[报错] {filename}: {output}")
                            else:
                                if output: self.log(f"[ExifTool] {output}")

                        except Exception as e:
                            self.log(f"[异常] 处理 {filename} 时出错: {e}")

            self.log(f"\n--- 处理完成 ---")
            self.log(f"发现DNG文件: {count_total_dng}")
            self.log(f"成功生成文件: {count_processed}")
            
            # 使用 after 方法在主线程弹窗，防止线程冲突
            if count_processed > 0:
                self.root.after(0, lambda: messagebox.showinfo("完成", f"处理完成！成功生成 {count_processed} 个文件。"))
            else:
                self.root.after(0, lambda: messagebox.showinfo("完成", "扫描完成，但没有生成新文件（可能没有匹配的照片）。"))

        except Exception as e:
            self.log(f"运行期间发生未知错误: {e}")
        finally:
            self.is_running = False
            self.root.after(0, lambda: self.btn_start.config(state='normal', text="开始处理"))

    # --- 以下是 ExifTool 安装逻辑 ---
    def get_latest_version(self):
        self.log(">>> 正在检测 ExifTool 最新版本...")
        try:
            with urllib.request.urlopen(self.RSS_URL, timeout=10) as response:
                data = response.read().decode('utf-8')
                match = re.search(r"ExifTool (\d+\.\d+)", data)
                if match:
                    version = match.group(1)
                    self.log(f"    检测到最新版本: {version}")
                    return version
        except Exception as e:
            self.log(f"    版本检测失败 ({e})，使用备用版本。")
        return self.FALLBACK_VERSION

    def setup_exiftool(self):
        self.log("="*40)
        self.log("【系统检测】正在初始化 ExifTool 环境...")
        
        if os.path.exists(self.EXIFTOOL_DIR):
            try:
                shutil.rmtree(self.EXIFTOOL_DIR)
            except:
                pass     
        os.makedirs(self.EXIFTOOL_DIR)

        version = self.get_latest_version()
        url = f"https://exiftool.org/exiftool-{version}_64.zip"
        zip_path = os.path.join(self.BASE_DIR, "temp_exiftool.zip")

        self.log(f"【下载地址】{url}")
        self.log(">>> 正在下载... (请稍候)")
        
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req) as response, open(zip_path, 'wb') as out_file:
                shutil.copyfileobj(response, out_file)
                
            with open(zip_path, 'rb') as f:
                if f.read(2) != b'PK':
                    self.log("!!! 错误: 下载的文件不是ZIP。")
                    return False
        except Exception as e:
            self.log(f"!!! 下载失败: {e}")
            return False

        self.log(">>> 正在解压完整包...")
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(self.EXIFTOOL_DIR)
            
            # 智能调整目录结构
            items = os.listdir(self.EXIFTOOL_DIR)
            # 如果只有一个子文件夹，说明多套了一层
            if len(items) == 1 and os.path.isdir(os.path.join(self.EXIFTOOL_DIR, items[0])):
                subdir_path = os.path.join(self.EXIFTOOL_DIR, items[0])
                for sub_item in os.listdir(subdir_path):
                    shutil.move(os.path.join(subdir_path, sub_item), os.path.join(self.EXIFTOOL_DIR, sub_item))
                os.rmdir(subdir_path)

            found_exe = False
            possible_exes = ["exiftool(-k).exe", "exiftool.exe"]
            for exe_name in possible_exes:
                current_exe_path = os.path.join(self.EXIFTOOL_DIR, exe_name)
                if os.path.exists(current_exe_path):
                    if "(-k)" in exe_name:
                        shutil.move(current_exe_path, self.EXIFTOOL_EXE_PATH)
                    found_exe = True
                    break
            
            if not found_exe:
                self.log("!!! 错误: 解压后未找到 exe。")
                return False

        except Exception as e:
            self.log(f"!!! 解压失败: {e}")
            return False
        finally:
            if os.path.exists(zip_path):
                os.remove(zip_path)

        self.log(f"✅ ExifTool 安装完成")
        self.log("="*40)
        return True

    def get_exiftool_path(self):
        if os.path.exists(self.EXIFTOOL_EXE_PATH):
            return self.EXIFTOOL_EXE_PATH
        if self.setup_exiftool():
            return self.EXIFTOOL_EXE_PATH
        return None

if __name__ == "__main__":
    root = tk.Tk()
    app = DngConverterApp(root)
    root.mainloop()