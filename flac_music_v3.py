from tqdm import tqdm
import requests
import re
import warnings
import urllib3
import json
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import threading
import time
import os
import sys
import shutil
from datetime import datetime, timedelta
import traceback
import math
import subprocess

# 彻底地禁用所有警告
warnings.filterwarnings("ignore")
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 定义颜色方案
COLORS = {
    "primary": "#4A90E2",
    "secondary": "#5C6BC0",
    "success": "#66BB6A",
    "warning": "#FFA726",
    "danger": "#EF5350",
    "dark": "#2C3E50",
    "light": "#F5F7FA",
    "gray": "#B0BEC5",
    "text": "#37474F",
    "text_light": "#78909C",
    "bg_light": "#FFFFFF",
    "bg_dark": "#F8F9FA"
}


class DownloadProgressTracker:
    """跟踪单个下载任务的进度信息"""

    def __init__(self, filename, total_size):
        self.filename = filename
        self.total_size = total_size
        self.downloaded = 0
        self.start_time = time.time()
        self.last_update_time = time.time()
        self.last_downloaded = 0
        self.speed = 0
        self.eta = "计算中..."
        self.progress = 0

    def update(self, chunk_size):
        """更新下载进度"""
        self.downloaded += chunk_size
        current_time = time.time()
        time_elapsed = current_time - self.last_update_time

        # 计算下载速度（每2秒更新一次）
        if time_elapsed >= 2.0:
            downloaded_since_last = self.downloaded - self.last_downloaded
            self.speed = downloaded_since_last / time_elapsed  # 字节/秒
            self.last_downloaded = self.downloaded
            self.last_update_time = current_time

            # 计算剩余时间
            if self.speed > 0 and self.total_size > 0:
                remaining_bytes = self.total_size - self.downloaded
                eta_seconds = remaining_bytes / self.speed
                if eta_seconds > 3600:
                    self.eta = f"{eta_seconds / 3600:.1f}小时"
                elif eta_seconds > 60:
                    self.eta = f"{eta_seconds / 60:.1f}分钟"
                else:
                    self.eta = f"{eta_seconds:.0f}秒"
            else:
                self.eta = "计算中..."

        # 计算进度百分比
        if self.total_size > 0:
            self.progress = (self.downloaded / self.total_size) * 100
        else:
            self.progress = 0

    def format_size(self, size_bytes):
        """格式化文件大小"""
        if size_bytes == 0:
            return "0B"
        size_names = ("B", "KB", "MB", "GB")
        i = int(math.floor(math.log(size_bytes, 1024)))
        p = math.pow(1024, i)
        s = round(size_bytes / p, 2)
        return f"{s} {size_names[i]}"

    def format_speed(self):
        """格式化下载速度"""
        return f"{self.format_size(self.speed)}/s"

    def get_progress_text(self):
        """获取进度显示文本"""
        if self.total_size > 0:
            return f"{self.format_size(self.downloaded)} / {self.format_size(self.total_size)} ({self.progress:.1f}%)"
        else:
            return f"{self.format_size(self.downloaded)} (大小未知)"


class UpdateChecker:
    """更新检查器"""

    def __init__(self, parent_app):
        self.parent_app = parent_app
        self.update_info = None
        self.local_version = "3.2"  # 当前本地版本
        self.update_url = "https://gh-proxy.org/https://github.com/tackeyxy/flac_music_downloader/blob/main/update_info.json"

    def check_for_update(self):
        """检查更新"""
        try:
            response = requests.get(self.update_url, verify=False, timeout=10)
            response.raise_for_status()

            self.update_info = response.json()

            # 提取远程版本号
            remote_version = self.update_info.get("version_info", {}).get("current_version", "0.0")

            # 比较版本号
            if self.is_newer_version(remote_version, self.local_version):
                return True, self.update_info
            else:
                return False, self.update_info

        except Exception as e:
            self.parent_app.log(f"检查更新失败: {str(e)}", "RED")
            return False, None

    def is_newer_version(self, remote_version, local_version):
        """比较版本号，判断远程版本是否更新"""
        try:
            # 将版本号转换为数字列表以便比较
            remote_parts = list(map(int, remote_version.split('.')))
            local_parts = list(map(int, local_version.split('.')))

            # 确保版本号长度一致
            max_len = max(len(remote_parts), len(local_parts))
            remote_parts.extend([0] * (max_len - len(remote_parts)))
            local_parts.extend([0] * (max_len - len(local_parts)))

            # 比较每个部分
            for r, l in zip(remote_parts, local_parts):
                if r > l:
                    return True
                elif r < l:
                    return False
            return False  # 版本完全相同
        except:
            # 如果版本号解析失败，使用字符串比较
            return remote_version > local_version

    def download_update(self, download_url, callback=None):
        """下载更新文件"""
        try:
            # 获取当前运行目录
            current_dir = os.path.dirname(os.path.abspath(sys.argv[0]))

            # 从URL提取文件名
            filename = os.path.basename(download_url)
            if '?' in filename:
                filename = filename.split('?')[0]

            filepath = os.path.join(current_dir, filename)

            # 下载文件
            response = requests.get(download_url, stream=True, verify=False, timeout=30)
            response.raise_for_status()

            total_size = int(response.headers.get('content-length', 0))

            # 创建进度跟踪器
            tracker = DownloadProgressTracker(filename, total_size)

            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        tracker.update(len(chunk))

                        # 如果有回调函数，更新进度
                        if callback:
                            callback(tracker)

            return filepath, True

        except Exception as e:
            self.parent_app.log(f"下载更新失败: {str(e)}", "RED")
            return None, False


class ModernButton(tk.Button):
    """现代化按钮控件"""

    def __init__(self, master=None, **kwargs):
        # 设置默认样式
        defaults = {
            'bg': COLORS['primary'],
            'fg': 'white',
            'font': ('Microsoft YaHei', 9, 'bold'),  # 减小字体大小
            'relief': 'flat',
            'bd': 0,
            'padx': 12,  # 减小内边距
            'pady': 6,  # 减小内边距
            'cursor': 'hand2'
        }

        # 更新用户提供的参数
        defaults.update(kwargs)
        super().__init__(master, **defaults)

        # 绑定鼠标事件
        self.bind('<Enter>', self.on_enter)
        self.bind('<Leave>', self.on_leave)
        self.bind('<ButtonPress-1>', self.on_press)
        self.bind('<ButtonRelease-1>', self.on_release)

        self.original_bg = defaults['bg']

    def on_enter(self, e):
        if self['state'] != 'disabled':
            self.config(bg=self.darken_color(self.original_bg, 0.2))

    def on_leave(self, e):
        if self['state'] != 'disabled':
            self.config(bg=self.original_bg)

    def on_press(self, e):
        if self['state'] != 'disabled':
            self.config(bg=self.darken_color(self.original_bg, 0.3))

    def on_release(self, e):
        if self['state'] != 'disabled':
            self.config(bg=self.darken_color(self.original_bg, 0.2))

    def darken_color(self, color, factor):
        """使颜色变深"""
        try:
            if color.startswith('#'):
                r = int(color[1:3], 16)
                g = int(color[3:5], 16)
                b = int(color[5:7], 16)
                r = max(0, min(255, int(r * (1 - factor))))
                g = max(0, min(255, int(g * (1 - factor))))
                b = max(0, min(255, int(b * (1 - factor))))
                return f'#{r:02x}{g:02x}{b:02x}'
        except:
            pass
        return color


class ModernEntry(tk.Entry):
    """现代化输入框"""

    def __init__(self, master=None, **kwargs):
        defaults = {
            'font': ('Microsoft YaHei', 9),  # 减小字体大小
            'relief': 'flat',
            'bd': 1,
            'highlightthickness': 2,
            'highlightcolor': COLORS['primary'],
            'highlightbackground': COLORS['gray']
        }
        defaults.update(kwargs)
        super().__init__(master, **defaults)


class UpdateDialog:
    """更新弹窗"""

    def __init__(self, parent, update_info, download_callback, skip_callback):
        self.parent = parent
        self.update_info = update_info
        self.download_callback = download_callback
        self.skip_callback = skip_callback

        self.downloaded_file = None
        self.is_downloading = False

        self.create_dialog()

    def create_dialog(self):
        """创建更新弹窗"""
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("发现新版本")
        self.dialog.geometry("600x700")
        self.dialog.configure(bg=COLORS['bg_light'])
        self.dialog.resizable(False, False)

        # 使弹窗模态
        self.dialog.transient(self.parent)
        self.dialog.grab_set()

        # 设置窗口居中
        self.center_window()

        # 添加内容
        self.create_content()

        # 绑定关闭事件
        self.dialog.protocol("WM_DELETE_WINDOW", self.on_close)

    def center_window(self):
        """窗口居中显示"""
        self.dialog.update_idletasks()
        width = self.dialog.winfo_width()
        height = self.dialog.winfo_height()
        x = (self.dialog.winfo_screenwidth() // 2) - (width // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (height // 2)
        self.dialog.geometry(f'{width}x{height}+{x}+{y}')

    def create_content(self):
        """创建弹窗内容"""
        # 标题
        title_frame = tk.Frame(self.dialog, bg=COLORS['primary'], height=60)
        title_frame.pack(fill=tk.X)
        title_frame.pack_propagate(False)

        title_label = tk.Label(title_frame,
                               text="发现新版本",
                               font=("Microsoft YaHei", 16, "bold"),
                               fg="white",
                               bg=COLORS['primary'])
        title_label.pack(expand=True)

        # 版本信息
        info_frame = tk.Frame(self.dialog, bg=COLORS['bg_light'], padx=20, pady=20)
        info_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        version_info = self.update_info.get("version_info", {})

        # 版本号
        version_frame = tk.Frame(info_frame, bg=COLORS['bg_light'])
        version_frame.pack(fill=tk.X, pady=(0, 10))

        tk.Label(version_frame,
                 text="新版本:",
                 font=("Microsoft YaHei", 11, "bold"),
                 bg=COLORS['bg_light']).pack(side=tk.LEFT)

        tk.Label(version_frame,
                 text=f"v{version_info.get('current_version', '未知')}",
                 font=("Microsoft YaHei", 11),
                 fg=COLORS['primary'],
                 bg=COLORS['bg_light']).pack(side=tk.LEFT, padx=(5, 0))

        # 应用名称
        tk.Label(version_frame,
                 text=f" - {version_info.get('app_name', '无损音乐下载器')}",
                 font=("Microsoft YaHei", 11),
                 bg=COLORS['bg_light']).pack(side=tk.LEFT)

        # 详细信息表格
        details_frame = tk.LabelFrame(info_frame,
                                      text="版本信息",
                                      font=("Microsoft YaHei", 10, "bold"),
                                      bg=COLORS['bg_light'],
                                      fg=COLORS['dark'],
                                      padx=10,
                                      pady=10)
        details_frame.pack(fill=tk.X, pady=(0, 15))

        details = [
            ("包大小:", version_info.get('package_size', '未知')),
            ("发布日期:", version_info.get('release_date', '未知')),
            ("更新时间:", version_info.get('update_time', '未知')),
            ("包类型:", version_info.get('installer_type', 'EXE')),
            ("运行平台:", self.update_info.get("download", {}).get("Windows", {}).get("compatibility", "Windows 10/11"))
        ]

        for label_text, value_text in details:
            row_frame = tk.Frame(details_frame, bg=COLORS['bg_light'])
            row_frame.pack(fill=tk.X, pady=2)

            tk.Label(row_frame,
                     text=label_text,
                     font=("Microsoft YaHei", 9),
                     bg=COLORS['bg_light'],
                     width=12,
                     anchor="w").pack(side=tk.LEFT)

            tk.Label(row_frame,
                     text=value_text,
                     font=("Microsoft YaHei", 9),
                     bg=COLORS['bg_light'],
                     anchor="w").pack(side=tk.LEFT, padx=(5, 0))

        # 更新内容
        update_content = self.update_info.get("update_content", [])
        if update_content:
            content_frame = tk.LabelFrame(info_frame,
                                          text="更新内容",
                                          font=("Microsoft YaHei", 10, "bold"),
                                          bg=COLORS['bg_light'],
                                          fg=COLORS['dark'],
                                          padx=10,
                                          pady=10)
            content_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))

            content_text = tk.Text(content_frame,
                                   height=5,
                                   font=("Microsoft YaHei", 9),
                                   bg=COLORS['bg_light'],
                                   relief=tk.FLAT,
                                   wrap=tk.WORD)
            content_text.pack(fill=tk.BOTH, expand=True)

            for i, content in enumerate(update_content, 1):
                content_text.insert(tk.END, f"{i}. {content}\n")

            content_text.config(state=tk.DISABLED)

        # 进度条框架（初始隐藏）
        self.progress_frame = tk.Frame(info_frame, bg=COLORS['bg_light'])

        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(self.progress_frame,
                                            variable=self.progress_var,
                                            maximum=100,
                                            style="Custom.Horizontal.TProgressbar")
        self.progress_bar.pack(fill=tk.X, pady=(0, 5))

        self.progress_label = tk.Label(self.progress_frame,
                                       text="等待下载...",
                                       font=("Microsoft YaHei", 9),
                                       fg=COLORS['text_light'],
                                       bg=COLORS['bg_light'])
        self.progress_label.pack()

        # 按钮框架
        button_frame = tk.Frame(self.dialog, bg=COLORS['bg_light'], pady=15)
        button_frame.pack(fill=tk.X, padx=20)

        # 跳过按钮
        skip_button = ModernButton(button_frame,
                                   text="稍后提醒",
                                   command=self.skip_update,
                                   bg=COLORS['gray'],
                                   font=('Microsoft YaHei', 10),
                                   padx=20,
                                   pady=8)
        skip_button.pack(side=tk.LEFT, padx=(0, 10))

        # 下载按钮
        self.download_button = ModernButton(button_frame,
                                            text="立即下载更新",
                                            command=self.start_download,
                                            bg=COLORS['primary'],
                                            font=('Microsoft YaHei', 10, 'bold'),
                                            padx=20,
                                            pady=8)
        self.download_button.pack(side=tk.RIGHT)

    def start_download(self):
        """开始下载更新"""
        if self.is_downloading:
            return

        self.is_downloading = True
        self.download_button.config(state=tk.DISABLED, text="下载中...")

        # 显示进度条
        self.progress_frame.pack(fill=tk.X, pady=(10, 0))

        # 启动下载线程
        thread = threading.Thread(target=self.download_update)
        thread.daemon = True
        thread.start()

    def download_update(self):
        """下载更新文件"""
        try:
            # 获取下载链接
            download_url = self.update_info.get("download", {}).get("Windows", {}).get("url", "")
            if not download_url:
                raise Exception("未找到下载链接")

            # 创建更新检查器实例
            update_checker = UpdateChecker(None)

            # 下载回调函数
            def progress_callback(tracker):
                # 更新进度条
                self.progress_var.set(tracker.progress)
                self.progress_label.config(text=f"{tracker.get_progress_text()} - {tracker.format_speed()}")

                # 更新UI
                self.dialog.update_idletasks()

            # 开始下载
            filepath, success = update_checker.download_update(download_url, progress_callback)

            if success:
                self.downloaded_file = filepath
                self.progress_label.config(text="下载完成!", fg=COLORS['success'])
                self.progress_var.set(100)

                # 下载完成后显示安装按钮
                self.download_button.config(state=tk.NORMAL,
                                            text="立即安装",
                                            command=self.prompt_installation,
                                            bg=COLORS['success'])
            else:
                raise Exception("下载失败")

        except Exception as e:
            self.progress_label.config(text=f"下载失败: {str(e)}", fg=COLORS['danger'])
            self.download_button.config(state=tk.NORMAL,
                                        text="重试下载",
                                        command=self.start_download)
            self.is_downloading = False

    def prompt_installation(self):
        """提示安装"""
        response = messagebox.askyesno("安装更新",
                                       "更新文件已下载完成，是否立即安装？\n\n安装后软件将自动重启。")

        if response:
            # 执行安装
            self.perform_installation()
        else:
            # 不安装，直接退出
            messagebox.showinfo("退出", "更新已下载但未安装。软件将退出。")
            self.dialog.destroy()
            self.skip_callback(exit_app=True)

    def perform_installation(self):
        """执行安装"""
        try:
            if not self.downloaded_file or not os.path.exists(self.downloaded_file):
                raise Exception("更新文件不存在")

            # 获取当前运行的文件路径
            current_exe = sys.argv[0]

            # 创建安装脚本
            self.create_install_script(current_exe, self.downloaded_file)

            # 关闭当前应用
            self.dialog.destroy()
            self.download_callback(install=True)

        except Exception as e:
            messagebox.showerror("安装错误", f"安装失败: {str(e)}")

    def create_install_script(self, old_file, new_file):
        """创建安装脚本（用于替换旧版本）"""
        script_content = f"""
@echo off
echo 正在安装更新...
timeout /t 2 /nobreak >nul

echo 正在关闭旧版本进程...
taskkill /f /im "{os.path.basename(old_file)}" 2>nul

echo 正在替换文件...
del "{old_file}" 2>nul
move "{new_file}" "{old_file}" 2>nul

echo 启动新版本...
start "" "{old_file}"

echo 清理临时文件...
del "%~f0" 2>nul
"""

        # 保存脚本
        script_path = os.path.join(os.path.dirname(old_file), "install_update.bat")
        with open(script_path, 'w', encoding='gbk') as f:
            f.write(script_content)

        # 运行脚本
        subprocess.Popen([script_path], shell=True)

    def skip_update(self):
        """跳过更新"""
        response = messagebox.askyesno("跳过更新",
                                       "确定要跳过此更新吗？\n\n您可以在设置中手动检查更新。")
        if response:
            self.dialog.destroy()
            self.skip_callback()

    def on_close(self):
        """关闭窗口事件"""
        self.skip_update()


class MusicDownloaderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("无损音乐下载器 v3.2")
        # 调整窗口高度，移除底部状态栏
        self.root.geometry("950x982")

        # 设置窗口背景
        self.root.configure(bg=COLORS['bg_dark'])

        # 存储会话信息的变量
        self.sl_session = None
        self.sl_jwt_session = None
        self.is_initialized = False

        # 存储搜索结果
        self.search_results = []
        self.selected_songs = {}  # 改为字典，键为歌曲ID，值为歌曲信息，用于存储所有已选择的歌曲

        # 添加用于存储每页歌曲ID的列表
        self.current_page_songs = []  # 当前页显示的歌曲ID列表

        # 下载状态
        self.is_downloading = False
        self.download_queue = []
        self.downloaded_count = 0
        self.total_to_download = 0

        # 下载进度跟踪器字典
        self.progress_trackers = {}

        # 下载任务框架字典
        self.download_frames = {}

        # 分页相关变量
        self.current_page = 1
        self.total_pages = 1
        self.total_results = 0
        self.current_keywords = ""

        # 创建会话对象
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36'
        })

        # 创建样式
        self.create_styles()

        # 创建界面
        self.create_widgets()

        # 在后台初始化会话和检查更新
        self.init_session_async()

        # 启动更新检查（延迟2秒，等待主窗口显示）
        self.root.after(2000, self.check_update_on_start)

        # 绑定窗口大小变化事件
        self.root.bind('<Configure>', self.on_window_resize)

        # 更新检查器
        self.update_checker = UpdateChecker(self)

    def check_update_on_start(self):
        """启动时检查更新"""
        thread = threading.Thread(target=self.perform_update_check)
        thread.daemon = True
        thread.start()

    def perform_update_check(self):
        """执行更新检查"""
        try:
            has_update, update_info = self.update_checker.check_for_update()

            if has_update:
                # 在主线程中显示更新弹窗
                self.root.after(0, lambda: self.show_update_dialog(update_info))
            else:
                self.log("当前已是最新版本", "GREEN")

        except Exception as e:
            self.log(f"更新检查失败: {str(e)}", "RED")

    def show_update_dialog(self, update_info):
        """显示更新弹窗"""

        def download_callback(install=False):
            if install:
                # 安装更新，退出应用
                self.log("开始安装更新，退出应用...", "GREEN")
                self.root.quit()
                self.root.destroy()

        def skip_callback(exit_app=False):
            if exit_app:
                # 不安装，直接退出
                self.log("用户选择不安装更新，退出应用...", "YELLOW")
                self.root.quit()
                self.root.destroy()

        # 创建更新弹窗
        self.update_dialog = UpdateDialog(self.root, update_info, download_callback, skip_callback)

    def manual_check_update(self):
        """手动检查更新"""
        self.log("手动检查更新...")
        self.status_label.config(text="正在检查更新...", fg=COLORS['primary'])

        # 异步检查更新
        thread = threading.Thread(target=self.manual_update_check_thread)
        thread.daemon = True
        thread.start()

    def manual_update_check_thread(self):
        """手动检查更新的线程函数"""
        try:
            has_update, update_info = self.update_checker.check_for_update()

            if has_update:
                # 在主线程中显示更新弹窗
                self.root.after(0, lambda: self.show_update_dialog(update_info))
                self.root.after(0, lambda: self.status_label.config(text="✅ 发现新版本!", fg=COLORS['success']))
            else:
                self.root.after(0, lambda: self.status_label.config(text="✅ 当前已是最新版本", fg=COLORS['success']))
                self.root.after(0, lambda: messagebox.showinfo("检查更新", "当前已是最新版本!"))
                self.log("当前已是最新版本", "GREEN")

        except Exception as e:
            self.root.after(0, lambda: self.status_label.config(text="❌ 更新检查失败", fg=COLORS['danger']))
            self.log(f"手动检查更新失败: {str(e)}", "RED")
            self.root.after(0, lambda: messagebox.showerror("检查更新失败", f"检查更新失败: {str(e)}"))

    def create_styles(self):
        """创建自定义样式"""
        style = ttk.Style()

        # 配置Treeview样式 - 优化表头样式
        style.configure("Custom.Treeview",
                        background=COLORS['bg_light'],
                        foreground=COLORS['text'],
                        rowheight=25,  # 增加行高使内容更清晰
                        fieldbackground=COLORS['bg_light'],
                        borderwidth=0,
                        font=('Microsoft YaHei', 10))

        # 优化表头样式：增加字体大小，优化背景颜色
        style.configure("Custom.Treeview.Heading",
                        background=COLORS['primary'],
                        foreground='blue',
                        relief='flat',
                        font=('Microsoft YaHei', 11, 'bold'),  # 增大字体
                        padding=(10, 8))  # 增加内边距

        style.map("Custom.Treeview.Heading",
                  background=[('active', COLORS['secondary'])])

        # 配置进度条样式
        style.configure("Custom.Horizontal.TProgressbar",
                        background=COLORS['success'],
                        troughcolor=COLORS['bg_light'],
                        bordercolor=COLORS['bg_light'],
                        lightcolor=COLORS['success'],
                        darkcolor=COLORS['success'])

        # 配置滚动条样式
        style.configure("Custom.Vertical.TScrollbar",
                        background=COLORS['gray'],
                        darkcolor=COLORS['gray'],
                        lightcolor=COLORS['gray'],
                        troughcolor=COLORS['bg_light'],
                        bordercolor=COLORS['bg_light'])

        style.map("Custom.Vertical.TScrollbar",
                  background=[('active', COLORS['text_light'])])

    def create_widgets(self):
        # 主框架
        main_frame = tk.Frame(self.root, bg=COLORS['bg_dark'])
        main_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)

        # 状态显示框
        status_frame = tk.Frame(main_frame, bg=COLORS['bg_light'],
                                relief=tk.RIDGE, bd=1, padx=15, pady=10)
        status_frame.pack(fill=tk.X, pady=(0, 15))

        status_label = tk.Label(status_frame, text="状态:",
                                font=("Microsoft YaHei", 10, "bold"),
                                fg=COLORS['text'], bg=COLORS['bg_light'])
        status_label.pack(side=tk.LEFT)

        self.status_label = tk.Label(status_frame, text="⏳ 正在初始化...",
                                     font=("Microsoft YaHei", 10),
                                     fg=COLORS['warning'], bg=COLORS['bg_light'])
        self.status_label.pack(side=tk.LEFT, padx=(5, 20))

        # 初始化状态指示器
        self.init_indicator = tk.Label(status_frame, text="●",
                                       font=("Microsoft YaHei", 12),
                                       fg=COLORS['warning'], bg=COLORS['bg_light'])
        self.init_indicator.pack(side=tk.LEFT)

        # 添加检查更新按钮到状态栏
        self.update_check_button = ModernButton(status_frame,
                                                text="检查更新",
                                                command=self.manual_check_update,
                                                bg=COLORS['secondary'],
                                                font=('Microsoft YaHei', 9),
                                                padx=8,
                                                pady=4)
        self.update_check_button.pack(side=tk.RIGHT, padx=(0, 5))

        # 合并的搜索和保存设置区域
        combined_frame = tk.LabelFrame(main_frame,
                                       font=("Microsoft YaHei", 12, "bold"),
                                       bg=COLORS['bg_light'], fg=COLORS['dark'],
                                       padx=15, pady=15, relief=tk.RIDGE, bd=2)
        combined_frame.pack(fill=tk.X, pady=(0, 15))

        # 搜索行框架
        search_row_frame = tk.Frame(combined_frame, bg=COLORS['bg_light'])
        search_row_frame.pack(fill=tk.X, pady=(0, 10))

        # 关键字搜索部分
        tk.Label(search_row_frame, text="关键字 :", font=("Microsoft YaHei", 9, "bold"),
                 bg=COLORS['bg_light'], fg=COLORS['text']).pack(side=tk.LEFT, padx=(0, 5))

        # 创建输入框容器
        entry_container = tk.Frame(search_row_frame, bg=COLORS['bg_light'])
        entry_container.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)

        # 动态设置输入框宽度（初始为窗口一半）
        self.entry_width = 25  # 初始宽度
        self.keyword_entry = ModernEntry(entry_container, width=self.entry_width)
        self.keyword_entry.pack(fill=tk.X, expand=True)

        # 添加默认搜索词
        self.keyword_entry.insert(0, "旅人")

        tk.Label(search_row_frame, text="结果数量:", font=("Microsoft YaHei", 9, "bold"),
                 bg=COLORS['bg_light'], fg=COLORS['text']).pack(side=tk.LEFT, padx=(15, 10))
        self.count_var = tk.StringVar(value="10")
        count_options = ["1", "5", "10", "20"]
        self.count_combo = ttk.Combobox(search_row_frame, textvariable=self.count_var,
                                        values=count_options, state="readonly", width=6,
                                        font=("Microsoft YaHei", 9))
        self.count_combo.pack(side=tk.LEFT, padx=5)

        # 按钮框架
        button_frame = tk.Frame(search_row_frame, bg=COLORS['bg_light'])
        button_frame.pack(side=tk.LEFT, padx=(15, 0))

        self.search_button = ModernButton(button_frame, text="搜索",
                                          command=self.search_music, state=tk.DISABLED,
                                          bg=COLORS['primary'], padx=10, pady=5)  # 减小按钮大小
        self.search_button.pack(side=tk.LEFT, padx=(0, 5))

        self.reinit_button = ModernButton(button_frame, text="重连",
                                          command=self.reinit_session, bg=COLORS['warning'],
                                          padx=10, pady=5)  # 减小按钮大小
        self.reinit_button.pack(side=tk.LEFT, padx=(0, 5))

        self.clear_button = ModernButton(button_frame, text="清空",
                                         command=self.clear_results, bg=COLORS['gray'],
                                         padx=10, pady=5)  # 减小按钮大小
        self.clear_button.pack(side=tk.LEFT)

        # 保存位置设置行框架
        save_row_frame = tk.Frame(combined_frame, bg=COLORS['bg_light'])
        save_row_frame.pack(fill=tk.X)

        tk.Label(save_row_frame, text="保存目录:",
                 font=("Microsoft YaHei", 9, "bold"),
                 bg=COLORS['bg_light'], fg=COLORS['text']).pack(side=tk.LEFT, padx=(0, 10))

        self.download_dir = tk.StringVar(value=os.path.join(os.path.expanduser("~"), "MusicDownloads"))
        dir_entry = ModernEntry(save_row_frame, textvariable=self.download_dir, width=45)
        dir_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)

        browse_button = ModernButton(save_row_frame, text="📁 浏览",
                                     command=self.browse_directory,
                                     bg=COLORS['secondary'],
                                     font=('Microsoft YaHei', 9),
                                     padx=10, pady=4)  # 减小按钮大小
        browse_button.pack(side=tk.LEFT, padx=5)

        # 搜索结果框架
        result_frame = tk.LabelFrame(main_frame, text="搜索结果",
                                     font=("Microsoft YaHei", 12, "bold"),
                                     bg=COLORS['bg_light'], fg=COLORS['dark'],
                                     padx=10, pady=10, relief=tk.RIDGE, bd=2)
        result_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))

        # 控制面板（全选/取消全选）
        control_panel = tk.Frame(result_frame, bg=COLORS['bg_light'])
        control_panel.pack(fill=tk.X, pady=(0, 5))

        self.select_all_var = tk.BooleanVar()
        self.select_all_cb = tk.Checkbutton(control_panel,
                                            text="全选/取消全选",
                                            variable=self.select_all_var,
                                            command=self.toggle_select_all,
                                            font=("Microsoft YaHei", 10),
                                            bg=COLORS['bg_light'],
                                            fg=COLORS['text'],
                                            selectcolor=COLORS['bg_light'],
                                            activebackground=COLORS['bg_light'],
                                            activeforeground=COLORS['text'])
        self.select_all_cb.pack(side=tk.LEFT)

        selected_count_label = tk.Label(control_panel, text="已选择: 0 首",
                                        font=("Microsoft YaHei", 10),
                                        bg=COLORS['bg_light'], fg=COLORS['text_light'])
        selected_count_label.pack(side=tk.RIGHT)
        self.selected_count_label = selected_count_label

        # 结果列表（使用Treeview）- 优化列宽和表头
        tree_frame = tk.Frame(result_frame, bg=COLORS['bg_light'])
        tree_frame.pack(fill=tk.BOTH, expand=True)

        columns = ("选择", "序号", "歌曲名称", "歌手", "专辑", "时长")
        self.result_tree = ttk.Treeview(tree_frame, columns=columns,
                                        show="headings", height=12,
                                        style="Custom.Treeview")

        # 设置列宽 - 优化列宽分配
        column_widths = {
            "选择": 50,  # 选择列稍宽一些
            "序号": 50,  # 序号列
            "歌曲名称": 300,  # 歌曲名称列最宽
            "歌手": 120,  # 歌手列
            "专辑": 200,  # 专辑列
            "时长": 80,  # 时长列
        }

        for col in columns:
            self.result_tree.heading(col, text=col, anchor="center")
            width = column_widths.get(col, 100)
            anchor = "center" if col in ["选择", "序号", "时长"] else "w"
            self.result_tree.column(col, width=width, anchor=anchor, minwidth=width // 2)

        # 添加滚动条
        tree_scroll = ttk.Scrollbar(tree_frame, orient="vertical",
                                    command=self.result_tree.yview,
                                    style="Custom.Vertical.TScrollbar")
        self.result_tree.configure(yscrollcommand=tree_scroll.set)

        self.result_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # 为Treeview绑定单击事件，实现单独选择功能
        self.result_tree.bind("<ButtonRelease-1>", self.on_treeview_click)

        # 翻页控制面板
        pagination_frame = tk.Frame(result_frame, bg=COLORS['bg_light'])
        pagination_frame.pack(fill=tk.X, pady=(10, 0))

        # 上一页按钮
        self.prev_button = ModernButton(pagination_frame, text="上一页",
                                        command=self.prev_page,
                                        state=tk.DISABLED,
                                        bg=COLORS['primary'],
                                        font=('Microsoft YaHei', 9),
                                        padx=8, pady=4)  # 减小按钮大小
        self.prev_button.pack(side=tk.LEFT, padx=(0, 10))

        # 当前页显示
        self.page_label = tk.Label(pagination_frame,
                                   text="第 1 页 / 共 1 页",
                                   font=("Microsoft YaHei", 9),
                                   bg=COLORS['bg_light'],
                                   fg=COLORS['text'])
        self.page_label.pack(side=tk.LEFT, padx=(0, 10))

        # 下一页按钮
        self.next_button = ModernButton(pagination_frame, text="下一页",
                                        command=self.next_page,
                                        state=tk.DISABLED,
                                        bg=COLORS['primary'],
                                        font=('Microsoft YaHei', 9),
                                        padx=8, pady=4)  # 减小按钮大小
        self.next_button.pack(side=tk.LEFT, padx=(0, 10))

        # 跳转页输入框
        tk.Label(pagination_frame, text="跳转到:",
                 font=("Microsoft YaHei", 9),
                 bg=COLORS['bg_light'], fg=COLORS['text']).pack(side=tk.LEFT, padx=(0, 5))

        self.jump_page_var = tk.StringVar()
        self.jump_page_entry = ModernEntry(pagination_frame,
                                           textvariable=self.jump_page_var,
                                           width=8,
                                           font=("Microsoft YaHei", 9))
        self.jump_page_entry.pack(side=tk.LEFT, padx=(0, 5))

        # 跳转按钮
        self.jump_button = ModernButton(pagination_frame, text="跳转",
                                        command=self.jump_to_page,
                                        bg=COLORS['primary'],
                                        font=('Microsoft YaHei', 9),
                                        padx=8, pady=4)  # 减小按钮大小
        self.jump_button.pack(side=tk.LEFT)

        # 下载按钮
        self.download_button = ModernButton(pagination_frame, text="下载",
                                            command=self.download_selected_music,
                                            state=tk.DISABLED,
                                            bg=COLORS['success'],
                                            font=('Microsoft YaHei', 9, 'bold'),
                                            padx=8, pady=4)  # 减小按钮大小
        self.download_button.pack(side=tk.RIGHT)

        # 总结果数显示
        self.total_results_label = tk.Label(pagination_frame,
                                            text="共 0 条结果",
                                            font=("Microsoft YaHei", 9),
                                            bg=COLORS['bg_light'],
                                            fg=COLORS['text_light'])
        self.total_results_label.pack(side=tk.RIGHT, padx=(0, 10))

        # 总进度条框架
        progress_frame = tk.Frame(main_frame, bg=COLORS['bg_dark'])
        progress_frame.pack(fill=tk.X, pady=(0, 15))

        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(progress_frame,
                                            variable=self.progress_var,
                                            maximum=100,
                                            style="Custom.Horizontal.TProgressbar")
        self.progress_bar.pack(fill=tk.X, pady=(0, 5))

        self.progress_label = tk.Label(progress_frame, text="等待下载...",
                                       font=("Microsoft YaHei", 9),
                                       fg=COLORS['text_light'], bg=COLORS['bg_dark'])
        self.progress_label.pack()

        # 下载任务进度显示区域 - 增加高度，填充底部空间
        download_tasks_frame = tk.LabelFrame(main_frame, text="下载任务",
                                             font=("Microsoft YaHei", 12, "bold"),
                                             bg=COLORS['bg_light'], fg=COLORS['dark'],
                                             padx=15, pady=15, relief=tk.RIDGE, bd=2,
                                             height=180)  # 增加高度
        download_tasks_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 0))  # 没有底部边距，直接到底部
        download_tasks_frame.pack_propagate(False)

        # 添加滚动区域用于显示多个下载任务
        self.download_canvas = tk.Canvas(download_tasks_frame,
                                         bg=COLORS['bg_light'],
                                         highlightthickness=0)
        scrollbar = ttk.Scrollbar(download_tasks_frame, orient="vertical",
                                  command=self.download_canvas.yview,
                                  style="Custom.Vertical.TScrollbar")
        self.download_scrollable_frame = tk.Frame(self.download_canvas,
                                                  bg=COLORS['bg_light'])

        self.download_scrollable_frame.bind(
            "<Configure>",
            lambda e: self.download_canvas.configure(
                scrollregion=self.download_canvas.bbox("all")
            )
        )

        self.download_canvas.create_window((0, 0),
                                           window=self.download_scrollable_frame,
                                           anchor="nw")
        self.download_canvas.configure(yscrollcommand=scrollbar.set)

        self.download_canvas.pack(side="left", fill="both", expand=True, padx=(0, 5))
        scrollbar.pack(side="right", fill="y")

    def on_window_resize(self, event):
        """处理窗口大小变化事件，动态调整输入框宽度"""
        if event.widget == self.root:
            # 计算窗口宽度的一半对应的字符数（大约）
            # 假设每个字符平均宽度为7像素
            window_width = event.width
            char_width = 7
            # 计算输入框宽度（字符数），窗口一半宽度减去一些边距
            new_width = max(10, (window_width // 2 - 100) // char_width)

            # 更新输入框宽度
            if hasattr(self, 'keyword_entry'):
                self.keyword_entry.config(width=new_width)
                self.entry_width = new_width

    def create_download_task_frame(self, filename, song_index):
        """为每个下载任务创建进度显示框架"""
        frame = tk.Frame(self.download_scrollable_frame,
                         relief=tk.RIDGE,
                         bd=1,
                         padx=10,
                         pady=8,
                         bg=COLORS['bg_light'])
        frame.pack(fill=tk.X, pady=3, padx=2)

        # 任务信息标签
        task_label = tk.Label(frame,
                              text=f"#{song_index:02d} {filename[:50]}...",
                              font=("Microsoft YaHei", 9, "bold"),
                              anchor="w",
                              bg=COLORS['bg_light'],
                              fg=COLORS['text'])
        task_label.pack(fill=tk.X)

        # 进度条
        progress_var = tk.DoubleVar()
        progress_bar = ttk.Progressbar(frame,
                                       variable=progress_var,
                                       maximum=100,
                                       length=970,
                                       style="Custom.Horizontal.TProgressbar")
        progress_bar.pack(fill=tk.X, pady=(5, 2))

        # 进度信息框架
        info_frame = tk.Frame(frame, bg=COLORS['bg_light'])
        info_frame.pack(fill=tk.X)

        # 进度百分比标签
        percent_label = tk.Label(info_frame,
                                 text="0%",
                                 font=("Microsoft YaHei", 9, "bold"),
                                 width=6,
                                 anchor="w",
                                 bg=COLORS['bg_light'],
                                 fg=COLORS['primary'])
        percent_label.pack(side=tk.LEFT, padx=(0, 15))

        # 大小标签
        size_label = tk.Label(info_frame,
                              text="0B / 0B",
                              font=("Microsoft YaHei", 9),
                              width=25,
                              anchor="w",
                              bg=COLORS['bg_light'],
                              fg=COLORS['text'])
        size_label.pack(side=tk.LEFT, padx=(0, 15))

        # 速度标签
        speed_label = tk.Label(info_frame,
                               text="速度: 0B/s",
                               font=("Microsoft YaHei", 9),
                               width=15,
                               anchor="w",
                               bg=COLORS['bg_light'],
                               fg=COLORS['text'])
        speed_label.pack(side=tk.LEFT, padx=(0, 15))

        # 剩余时间标签
        eta_label = tk.Label(info_frame,
                             text="剩余: 计算中...",
                             font=("Microsoft YaHei", 9),
                             width=15,
                             anchor="w",
                             bg=COLORS['bg_light'],
                             fg=COLORS['text'])
        eta_label.pack(side=tk.LEFT)

        # 存储控件引用
        self.download_frames[filename] = {
            'frame': frame,
            'progress_var': progress_var,
            'percent_label': percent_label,
            'size_label': size_label,
            'speed_label': speed_label,
            'eta_label': eta_label,
            'task_label': task_label
        }

        return frame

    def update_download_task_progress(self, filename, progress_tracker):
        """更新下载任务进度显示"""
        if filename not in self.download_frames:
            return

        frame_info = self.download_frames[filename]

        # 在主线程中更新UI
        def update_ui():
            # 更新进度条
            frame_info['progress_var'].set(progress_tracker.progress)

            # 更新百分比标签
            frame_info['percent_label'].config(text=f"{progress_tracker.progress:.1f}%")

            # 更新大小标签
            frame_info['size_label'].config(text=progress_tracker.get_progress_text())

            # 更新速度标签
            frame_info['speed_label'].config(text=f"速度: {progress_tracker.format_speed()}")

            # 更新剩余时间标签
            frame_info['eta_label'].config(text=f"剩余: {progress_tracker.eta}")

            # 更新任务标签颜色
            if progress_tracker.progress >= 100:
                frame_info['task_label'].config(fg=COLORS['success'])
            elif progress_tracker.progress > 75:
                frame_info['task_label'].config(fg=COLORS['warning'])
            elif progress_tracker.progress > 0:
                frame_info['task_label'].config(fg=COLORS['primary'])
            else:
                frame_info['task_label'].config(fg=COLORS['text'])

        # 使用线程安全的方式更新UI
        self.root.after(0, update_ui)

    def remove_download_task_frame(self, filename):
        """移除下载任务框架"""
        if filename in self.download_frames:
            def remove():
                self.download_frames[filename]['frame'].destroy()
                del self.download_frames[filename]

            self.root.after(0, remove)

    def clear_all_download_tasks(self):
        """清除所有下载任务显示"""
        for filename in list(self.download_frames.keys()):
            self.remove_download_task_frame(filename)

    def on_treeview_click(self, event):
        """处理Treeview的点击事件，实现单独选择功能"""
        # 获取点击的区域和项目
        region = self.result_tree.identify_region(event.x, event.y)
        if region == "cell":
            column = self.result_tree.identify_column(event.x)
            item = self.result_tree.identify_row(event.y)

            # 如果是点击了第一列（选择列）
            if column == "#1" and item:
                values = list(self.result_tree.item(item, 'values'))
                # 获取歌曲索引
                index = int(values[1]) - 1  # 转换为0-based索引

                # 检查索引是否在有效范围内
                if 0 <= index < len(self.current_page_songs):
                    song_id = self.current_page_songs[index]

                    # 切换选择状态
                    if values[0] == "✓":
                        values[0] = ""
                        # 从已选择歌曲中移除
                        if song_id in self.selected_songs:
                            del self.selected_songs[song_id]
                    else:
                        values[0] = "✓"
                        # 添加到已选择歌曲中
                        if index < len(self.search_results):
                            self.selected_songs[song_id] = self.search_results[index]

                    self.result_tree.item(item, values=values)

                    # 更新全选复选框的状态
                    self.update_select_all_checkbox()

                    # 更新已选择数量
                    self.update_selected_count()

    def update_selected_count(self):
        """更新已选择歌曲数量"""
        count = len(self.selected_songs)
        self.selected_count_label.config(text=f"已选择: {count} 首")

    def update_select_all_checkbox(self):
        """更新全选复选框的状态"""
        all_items = self.result_tree.get_children()
        if not all_items:
            self.select_all_var.set(False)
            return

        # 检查是否所有项目都被选中
        all_selected = True
        for item in all_items:
            values = self.result_tree.item(item, 'values')
            if values and values[0] != "✓":
                all_selected = False
                break

        # 更新复选框状态（不触发command回调）
        self.select_all_cb.config(command=lambda: None)  # 临时禁用command
        self.select_all_var.set(all_selected)
        self.select_all_cb.config(command=self.toggle_select_all)  # 重新启用command

    def log(self, message, color=None):
        """添加日志信息到控制台，不显示在界面上"""
        timestamp = datetime.now().strftime("%H:%M:%S")

        # 确定颜色
        if not color:
            if "错误" in message or "失败" in message:
                color = "RED"
            elif "成功" in message or "完成" in message:
                color = "GREEN"
            elif "警告" in message:
                color = "YELLOW"
            else:
                color = "WHITE"

        # 只打印到控制台，不显示在界面上
        print(f"[{timestamp}] {message}")

    def browse_directory(self):
        """选择下载目录 - 优化版本，使用异步方式防止卡顿"""

        def async_browse():
            directory = filedialog.askdirectory(initialdir=self.download_dir.get())
            if directory:
                # 在主线程中更新UI
                self.root.after(0, lambda: self.download_dir.set(directory))
                self.log(f"下载目录已更改为: {directory}")

        # 启动新线程执行文件夹选择操作
        thread = threading.Thread(target=async_browse)
        thread.daemon = True
        thread.start()

    def toggle_select_all(self):
        """全选/取消全选当前页"""
        select_all = self.select_all_var.get()

        for item in self.result_tree.get_children():
            values = list(self.result_tree.item(item, 'values'))
            index = int(values[1]) - 1  # 转换为0-based索引

            # 检查索引是否在有效范围内
            if 0 <= index < len(self.current_page_songs) and index < len(self.search_results):
                song_id = self.current_page_songs[index]
                song = self.search_results[index]

                if select_all:
                    values[0] = "✓"
                    # 添加到已选择歌曲中
                    self.selected_songs[song_id] = song
                else:
                    values[0] = ""
                    # 从已选择歌曲中移除
                    if song_id in self.selected_songs:
                        del self.selected_songs[song_id]

                self.result_tree.item(item, values=values)

        # 更新已选择数量
        self.update_selected_count()

    def clear_results(self):
        """清空搜索结果"""
        self.result_tree.delete(*self.result_tree.get_children())
        self.search_results = []
        self.selected_songs = {}  # 清空已选择歌曲
        self.current_page_songs = []  # 清空当前页歌曲ID列表
        self.select_all_var.set(False)
        self.download_button.config(state=tk.DISABLED)
        self.selected_count_label.config(text="已选择: 0 首")
        self.log("已清空搜索结果")

        # 重置分页信息
        self.current_page = 1
        self.total_pages = 1
        self.total_results = 0
        self.update_pagination_ui()

    def update_progress(self, current, total, message=""):
        """更新总进度条"""
        if total > 0:
            progress = (current / total) * 100
            self.progress_var.set(progress)

            if current < total:
                self.progress_label.config(text=f"{message} ({current}/{total})")
            else:
                self.progress_label.config(text="下载完成!", fg=COLORS['success'])

            self.root.update_idletasks()

    def init_session_async(self):
        """异步初始化会话"""
        self.log("开始初始化会话...")
        self.init_indicator.config(fg=COLORS['warning'])
        thread = threading.Thread(target=self.init_session)
        thread.daemon = True
        thread.start()

    def init_session(self):
        """初始化会话"""
        try:
            self.sl_session, self.sl_jwt_session = self.get_jwt_data()

            if self.sl_session and self.sl_jwt_session:
                self.is_initialized = True
                self.status_label.config(text="✅ 初始化成功!", fg=COLORS['success'])
                self.init_indicator.config(fg=COLORS['success'])
                self.search_button.config(state=tk.NORMAL)
                self.log("会话初始化成功!")
            else:
                self.status_label.config(text="❌ 初始化失败!", fg=COLORS['danger'])
                self.init_indicator.config(fg=COLORS['danger'])
                self.log("会话初始化失败!")
        except Exception as e:
            self.status_label.config(text=f"❌ 初始化出错: {str(e)[:50]}", fg=COLORS['danger'])
            self.init_indicator.config(fg=COLORS['danger'])
            self.log(f"初始化出错: {str(e)}", COLORS['danger'])
            self.log(traceback.format_exc())

    def reinit_session(self):
        """重新初始化会话"""
        self.is_initialized = False
        self.search_button.config(state=tk.DISABLED)
        self.download_button.config(state=tk.DISABLED)
        self.status_label.config(text="正在重新初始化...", fg=COLORS['warning'])
        self.init_indicator.config(fg=COLORS['warning'])
        self.log("重新初始化...")
        self.init_session_async()

    def search_music(self):
        """搜索音乐"""
        if not self.is_initialized:
            messagebox.showerror("错误", "未初始化，请先初始化!")
            return

        keywords = self.keyword_entry.get().strip()
        if not keywords:
            messagebox.showwarning("警告", "请输入搜索关键词!")
            return

        # 清空结果
        self.clear_results()

        # 设置当前关键词
        self.current_keywords = keywords

        # 异步搜索
        thread = threading.Thread(target=self.do_search, args=(keywords,))
        thread.daemon = True
        thread.start()

    def do_search(self, keywords, page=1):
        """执行搜索"""
        try:
            self.log(f"开始搜索: {keywords} - 第 {page} 页")
            count = int(self.count_var.get())

            # 显示搜索状态
            self.status_label.config(text=f"正在搜索: {keywords} (第 {page} 页)", fg=COLORS['primary'])

            # 使用已有的会话信息搜索
            song_list, total_count = self.search_music_with_session(
                keywords, self.sl_session, self.sl_jwt_session, page, count
            )

            # 存储搜索结果
            self.search_results = song_list

            # 清空当前页歌曲ID列表
            self.current_page_songs = []

            # 显示结果
            for i, song in enumerate(song_list, 1):
                song_id = song.get('id', '')
                self.current_page_songs.append(song_id)  # 添加歌曲ID到当前页列表

                # 检查歌曲是否已经在已选择列表中
                is_selected = song_id in self.selected_songs

                self.result_tree.insert("", tk.END, values=(
                    "✓" if is_selected else "",  # 选择框
                    i,  # 序号
                    song.get('name', '未知'),
                    song.get('artist', '未知'),
                    song.get('album_name', '未知'),
                    song.get('duration', '未知'),
                    song.get('format', 'flac')
                ))

            # 更新分页信息
            self.current_page = page
            self.total_results = total_count

            # 确保每页数量不为0，避免除零错误
            if count > 0:
                self.total_pages = max(1, math.ceil(total_count / count))
            else:
                self.total_pages = 1

            # 更新分页UI
            self.update_pagination_ui()

            # 启用下载按钮
            if song_list:
                self.download_button.config(state=tk.NORMAL)
                self.status_label.config(text=f"✅ 找到 {total_count} 首歌曲 (第 {page}/{self.total_pages} 页)",
                                         fg=COLORS['success'])
                self.log(f"搜索成功，找到 {total_count} 首歌曲", COLORS['success'])
            else:
                self.status_label.config(text="未找到相关歌曲", fg=COLORS['warning'])
                self.log("未找到相关歌曲", COLORS['warning'])

        except Exception as e:
            self.status_label.config(text="❌ 搜索失败", fg=COLORS['danger'])
            self.log(f"搜索出错: {str(e)}", COLORS['danger'])
            messagebox.showerror("错误", f"搜索失败: {str(e)}")

    def update_pagination_ui(self):
        """更新分页UI状态"""
        # 更新页面标签
        self.page_label.config(text=f"第 {self.current_page} 页 / 共 {self.total_pages} 页")

        # 更新总结果数标签
        self.total_results_label.config(text=f"共 {self.total_results} 条结果")

        # 更新按钮状态
        if self.current_page > 1:
            self.prev_button.config(state=tk.NORMAL, bg=COLORS['secondary'])
        else:
            self.prev_button.config(state=tk.DISABLED, bg=COLORS['gray'])

        if self.current_page < self.total_pages:
            self.next_button.config(state=tk.NORMAL, bg=COLORS['secondary'])
        else:
            self.next_button.config(state=tk.DISABLED, bg=COLORS['gray'])

    def prev_page(self):
        """上一页"""
        if self.current_page > 1:
            self.current_page -= 1
            self.load_page(self.current_page)

    def next_page(self):
        """下一页"""
        if self.current_page < self.total_pages:
            self.current_page += 1
            self.load_page(self.current_page)

    def jump_to_page(self):
        """跳转到指定页"""
        try:
            page = int(self.jump_page_var.get().strip())
            if 1 <= page <= self.total_pages:
                self.current_page = page
                self.load_page(page)
            else:
                messagebox.showwarning("警告", f"请输入有效的页码 (1-{self.total_pages})")
        except ValueError:
            messagebox.showwarning("警告", "请输入有效的页码数字")

    def load_page(self, page):
        """加载指定页的数据"""
        # 清空当前结果
        self.result_tree.delete(*self.result_tree.get_children())
        self.search_results = []
        self.current_page_songs = []  # 清空当前页歌曲ID列表
        self.select_all_var.set(False)
        self.download_button.config(state=tk.DISABLED)
        self.selected_count_label.config(text="已选择: 0 首")

        # 异步加载页面
        thread = threading.Thread(target=self.do_search, args=(self.current_keywords, page))
        thread.daemon = True
        thread.start()

    def download_selected_music(self):
        """下载选中的音乐"""
        if self.is_downloading:
            messagebox.showwarning("警告", "当前正在下载中，请稍候...")
            return

        # 获取选中的歌曲（从self.selected_songs字典中获取）
        selected_items = list(self.selected_songs.values())

        if not selected_items:
            messagebox.showwarning("警告", "请先选择要下载的歌曲!")
            return

        # 确认下载
        if not messagebox.askyesno("确认下载", f"确定要下载选中的 {len(selected_items)} 首歌曲吗？"):
            return

        # 异步下载
        thread = threading.Thread(target=self.do_download_batch, args=(selected_items,))
        thread.daemon = True
        thread.start()

    def do_download_batch(self, songs_to_download):
        """批量下载歌曲"""
        try:
            self.is_downloading = True
            self.downloaded_count = 0
            self.total_to_download = len(songs_to_download)

            # 禁用按钮
            self.root.after(0, lambda: self.download_button.config(state=tk.DISABLED))
            self.root.after(0, lambda: self.search_button.config(state=tk.DISABLED))

            # 清除之前的下载任务显示
            self.clear_all_download_tasks()

            # 创建下载目录
            download_dir = self.download_dir.get()
            os.makedirs(download_dir, exist_ok=True)

            self.log(f"开始批量下载，共 {len(songs_to_download)} 首歌曲")
            self.log(f"保存目录: {download_dir}")

            # 重置进度条
            self.progress_var.set(0)
            self.progress_label.config(text="开始下载...", fg=COLORS['text_light'])

            # 下载每首歌曲
            for i, song in enumerate(songs_to_download, 1):
                try:
                    self.update_progress(i - 1, self.total_to_download,
                                         f"正在下载第 {i} 首:")

                    song_id = song.get('id')
                    song_name = song.get('name', '未知歌曲')
                    artist = song.get('artist', '未知歌手')
                    format_type = song.get('format', 'flac')
                    # 获取歌曲的sign值和time值
                    song_sign = song.get('sign', '')
                    song_time = song.get('time', '')

                    self.log(f"正在下载: {song_name} - {artist} (sign: {song_sign[:20]}..., time: {song_time})")

                    # 获取下载链接 - 传入sign值和time值
                    song_url, _ = self.get_music_download_url_with_session(
                        song_id, self.sl_session, self.sl_jwt_session, song_sign, song_time
                    )

                    # 生成文件名：歌曲名-艺术家.格式
                    filename = f"{song_name} - {artist}.{format_type}"
                    # 清理文件名中的非法字符
                    filename = self.clean_filename(filename)

                    # 为当前任务创建进度显示框架
                    self.create_download_task_frame(filename, i)

                    # 下载文件
                    success = self.download_file(song_url, download_dir, filename, i)

                    if success:
                        self.downloaded_count += 1
                        self.log(f"✅ 下载完成: {filename}", COLORS['success'])
                        # 下载完成后更新任务状态
                        if filename in self.progress_trackers:
                            tracker = self.progress_trackers[filename]
                            tracker.progress = 100
                            self.update_download_task_progress(filename, tracker)
                    else:
                        self.log(f"❌ 下载失败: {filename}", COLORS['danger'])

                except Exception as e:
                    self.log(f"❌ 下载失败 {song_name}: {str(e)}", COLORS['danger'])
                    continue

            # 更新进度条完成
            self.update_progress(self.total_to_download, self.total_to_download,
                                 "下载完成")

            # 显示完成消息
            messagebox.showinfo("完成",
                                f"下载完成!\n成功: {self.downloaded_count}/{self.total_to_download}")

        except Exception as e:
            self.log(f"❌ 批量下载出错: {str(e)}", COLORS['danger'])
            messagebox.showerror("错误", f"下载失败: {str(e)}")
        finally:
            self.is_downloading = False
            # 重新启用按钮
            self.root.after(0, lambda: self.download_button.config(state=tk.NORMAL))
            self.root.after(0, lambda: self.search_button.config(state=tk.NORMAL))

    def clean_filename(self, filename):
        """清理文件名中的非法字符"""
        # 替换Windows文件名中不允许的字符
        illegal_chars = r'[<>:"/\\|?*]'
        filename = re.sub(illegal_chars, '_', filename)

        # 移除开头和结尾的空格和点
        filename = filename.strip('. ')

        # 如果文件名太长，截断
        if len(filename) > 200:
            name, ext = os.path.splitext(filename)
            filename = name[:200 - len(ext)] + ext

        return filename

    def download_file(self, url, save_dir, filename, task_index):
        """下载文件并保存，显示进度信息"""
        try:
            filepath = os.path.join(save_dir, filename)

            # 如果文件已存在，添加序号
            counter = 1
            original_filepath = filepath
            base_name, ext = os.path.splitext(filename)
            while os.path.exists(filepath):
                filepath = os.path.join(save_dir, f"{base_name}_{counter}{ext}")
                counter += 1

            # 下载文件
            response = self.session.get(url, stream=True, verify=False, timeout=30)
            response.raise_for_status()

            # 获取文件大小
            total_size = int(response.headers.get('content-length', 0))

            # 创建进度跟踪器
            tracker = DownloadProgressTracker(filename, total_size)
            self.progress_trackers[filename] = tracker

            # 打开文件进行写入
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        # 更新进度
                        tracker.update(len(chunk))
                        # 更新UI显示
                        self.update_download_task_progress(filename, tracker)

            # 下载完成后移除进度跟踪器
            if filename in self.progress_trackers:
                del self.progress_trackers[filename]

            return True

        except Exception as e:
            # 如果下载失败，更新任务状态为失败
            if filename in self.download_frames:
                frame_info = self.download_frames[filename]

                def mark_failed():
                    frame_info['task_label'].config(fg=COLORS['danger'],
                                                    text=f"#{task_index:02d} {filename[:50]}... [失败]")

                self.root.after(0, mark_failed)
            raise Exception(f"文件下载失败: {str(e)}")

    # 以下是网络请求函数（保持不变）
    def get_sl_session(self):
        """获取sl_session"""
        try:
            response = self.session.get('https://flac.music.hi.cn/', verify=False, timeout=10)
            sl_session_cookie = response.cookies.get('sl-session')
            print(sl_session_cookie)
            return sl_session_cookie
        except Exception as e:
            self.log(f"获取sl_session失败: {e}")
            return None

    def get_clientId(self):
        """获取客户端ID"""
        try:
            url = "https://flac.music.hi.cn/"
            response = self.session.get(url, verify=False, timeout=30)
            text = response.text
            pattern = r'SafeLineChallenge\("([^"]+)"'
            match = re.search(pattern, text)
            print(match.group(1))
            return match.group(1) if match else None
        except Exception as e:
            self.log(f"获取clientId失败: {e}")
            return None

    def get_issueId(self):
        """获取issueId"""
        try:
            clientId = self.get_clientId()
            if not clientId:
                self.log("ERROR: clientId 获取失败")
                return None, None

            # self.log(f"DEBUG: 获取到的 clientId: {clientId}")

            url = "https://challenge.rivers.chaitin.cn/challenge/v2/api/issue"
            payload = json.dumps({"client_id": clientId, "level": 1})

            # self.log(f"DEBUG: 请求URL: {url}")
            # self.log(f"DEBUG: 请求payload: {payload}")

            # 添加更完整的请求头
            headers = {
                'Host': 'challenge.rivers.chaitin.cn',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36',
                'Content-Type': 'application/json',
                'Accept': '*/*',
                'Accept-Language': 'zh-CN,zh;q=0.9',
                'sec-ch-ua-platform': '"Windows"',
                'sec-ch-ua': '"Chromium";v="142", "Google Chrome";v="142", "Not_A Brand";v="99"',
                'sec-ch-ua-mobile': '?0',
                'Origin': 'https://flac.music.hi.cn',
                'Sec-Fetch-Site': 'cross-site',
                'Sec-Fetch-Mode': 'cors',
                'Sec-Fetch-Dest': 'empty',
                'Referer': 'https://flac.music.hi.cn/'
            }

            max_retries = 3
            for attempt in range(max_retries):
                try:
                    self.log(f"尝试获取issueId (第{attempt + 1}次)...")
                    response = self.session.post(url,
                                                 headers=headers,
                                                 data=payload,
                                                 verify=False,
                                                 timeout=15)

                    # self.log(f"DEBUG: 响应状态码: {response.status_code}")
                    # self.log(f"DEBUG: 响应头: {dict(response.headers)}")

                    if response.status_code == 200:
                        result = response.json()
                        # self.log(f"DEBUG: 响应JSON: {json.dumps(result, ensure_ascii=False)[:300]}")

                        if 'data' in result:
                            data_org = result['data'].get('data')
                            issue_id = result['data'].get('issue_id')

                            # self.log(f"DEBUG: data_org: {data_org}")
                            # self.log(f"DEBUG: issue_id: {issue_id}")

                            if data_org and issue_id:
                                self.log(f"获取issueId成功: {issue_id}")
                                return data_org, issue_id
                            else:
                                self.log(f"WARN: data_org或issue_id为空")
                        else:
                            self.log(f"WARN: 响应中没有data字段")
                    else:
                        self.log(f"ERROR: 响应状态码异常: {response.status_code}")
                        self.log(f"ERROR: 响应文本: {response.text[:500]}")

                except json.JSONDecodeError as e:
                    self.log(f"ERROR: JSON解析失败: {e}")
                    self.log(f"ERROR: 响应内容: {response.text[:500]}")
                    if attempt < max_retries - 1:
                        time.sleep(1)
                    else:
                        raise
                except Exception as e:
                    self.log(f"ERROR: 请求异常: {e}")
                    if attempt < max_retries - 1:
                        time.sleep(1)
                    else:
                        raise

            self.log("ERROR: 所有重试都失败")
            return None, None

        except Exception as e:
            self.log(f"获取issueId失败: {e}")
            self.log(traceback.format_exc())
            return None, None

    def f(self):
        """计算函数"""
        try:
            data_org, issue_id = self.get_issueId()
            if not data_org or not issue_id:
                return None, None

            t = 1
            n = sum(data_org)
            r = (6 + len(data_org) + n) % 6 + 6

            for _ in range(r):
                t *= 6

            if t < 6666:
                t *= len(data_org)
            if t > 0x3f940aa:
                t = t // len(data_org)

            for o in range(len(data_org)):
                t += data_org[o] ** 3
                t ^= o
                t ^= data_org[o] + o

            f_result = []
            while t > 0:
                f_result.insert(0, 63 & t)
                t >>= 6

            print(f_result, issue_id)
            return f_result, issue_id
        except Exception as e:
            self.log(f"计算函数f失败: {e}")
            return None, None

    def get_sl_challenge_jwt(self):
        """获取sl_challenge_jwt"""
        try:
            clientId = self.get_clientId()
            if not clientId:
                return None

            f_result, issue_id = self.f()
            if not f_result or not issue_id:
                return None

            url = "https://challenge.rivers.chaitin.cn/challenge/v2/api/verify"
            payload = json.dumps({
                "issue_id": issue_id,
                "result": f_result,
                "serials": [],
                "client": {
                    "userAgent": self.session.headers['User-Agent'],
                    "platform": "Win32",
                    "language": "zh-CN,zh",
                    "vendor": "Google Inc.",
                    "screen": [1920, 1080],
                    "visitorId": clientId,
                    "score": 0,
                    "target": []
                }
            })
            headers = {
                'Host': 'challenge.rivers.chaitin.cn',
                'sec-ch-ua-platform': '"Windows"',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36',
                'sec-ch-ua': '"Chromium";v="142", "Google Chrome";v="142", "Not_A Brand";v="99"',
                'Content-Type': 'application/json',
                'sec-ch-ua-mobile': '?0',
                'Accept': '*/*',
                'Origin': 'https://flac.music.hi.cn',
                'Sec-Fetch-Site': 'cross-site',
                'Sec-Fetch-Mode': 'cors',
                'Sec-Fetch-Dest': 'empty',
                'Referer': 'https://flac.music.hi.cn/',
                'Accept-Language': 'zh-CN,zh;q=0.9'
            }

            response = self.session.post(url, headers=headers, data=payload, verify=False, timeout=30)
            result = response.json()
            print(result['data']['jwt'])
            return result['data']['jwt'] if 'data' in result else None

        except Exception as e:
            self.log(f"获取sl_challenge_jwt失败: {e}")
            return None

    def get_jwt_data(self):
        """获取完整的JWT数据"""
        try:
            sl_session = self.get_sl_session()
            if not sl_session:
                return None, None

            sl_challenge_jwt = self.get_sl_challenge_jwt()
            if not sl_challenge_jwt:
                return None, None

            cookie = f'sl-session={sl_session}; sl-challenge-server=cloud; sl-challenge-jwt={sl_challenge_jwt}'
            url = "https://flac.music.hi.cn"

            headers = {'Cookie': cookie}
            response = self.session.get(url, headers=headers, verify=False, timeout=30)
            sl_jwt_session = response.cookies.get('sl_jwt_session')
            print(sl_session, sl_jwt_session)

            return sl_session, sl_jwt_session

        except Exception as e:
            self.log(f"获取JWT数据失败: {e}")
            return None, None

    def search_music_with_session(self, keywords, sl_session, sl_jwt_session, page=1, page_size=10):
        """使用已有的会话信息搜索音乐"""
        try:
            url = "https://flac.music.hi.cn/ajax.php?act=search"
            payload = f'keyword={keywords}&page={page}&size={page_size}'

            headers = {
                'Cookie': f'sl-session={sl_session}; sl_jwt_session={sl_jwt_session}; sl_jwt_sign=',
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'X-Requested-With': 'XMLHttpRequest'
            }

            response = self.session.post(url, headers=headers, data=payload,
                                         verify=False, timeout=30)
            result = response.json()

            if 'data' not in result:
                return [], 0

            # 获取总结果数并转换为整数
            total_count = result['data'].get('total', 0)
            try:
                total_count = int(total_count)
            except (ValueError, TypeError):
                total_count = 0

            if 'list' not in result['data']:
                return [], total_count

            song_list = result['data']['list']
            formatted_list = []

            for song in song_list:
                formatted_list.append({
                    'id': song.get('id', ''),
                    'name': song.get('name', '未知'),
                    'artist': song.get('artist', '未知'),
                    'album_name': song.get('album_name', '未知'),
                    'duration': self.format_duration(song.get('duration', 0)),
                    'format': 'flac',  # 默认格式
                    'sign': song.get('sign', ''),  # 保存sign值
                    'time': song.get('time', '')  # 保存time值
                })

            return formatted_list, total_count

        except Exception as e:
            self.log(f"搜索音乐失败: {e}")
            return [], 0

    def format_duration(self, seconds):
        """格式化时长（秒 → MM:SS）"""
        try:
            minutes = int(seconds) // 60
            secs = int(seconds) % 60
            return f"{minutes:02d}:{secs:02d}"
        except:
            return "00:00"

    def get_music_download_url_with_session(self, song_id, sl_session, sl_jwt_session, sign='', time=''):
        """使用已有的会话信息获取音乐下载链接，带上sign值和time值"""
        try:
            url = "https://flac.music.hi.cn/ajax.php?act=getUrl"
            quality = 'format=flac&bitrate=2000'

            # 构建请求参数，包含sign值和time值
            params = [f'songid={song_id}', quality]
            if sign:
                params.append(f'sign={sign}')
            if time:
                params.append(f'time={time}')

            payload = '&'.join(params)

            headers = {
                'Cookie': f'sl-session={sl_session}; sl_jwt_session={sl_jwt_session}; sl_jwt_sign=',
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'X-Requested-With': 'XMLHttpRequest'
            }

            self.log(f"获取下载链接: song_id={song_id}, sign={sign[:20]}..., time={time}")

            response = self.session.post(url, headers=headers, data=payload,
                                         verify=False, timeout=60)
            result = response.json()

            if 'data' not in result:
                raise Exception("下载链接获取失败")

            song_info = result['data']
            song_url = song_info['url']

            # 从URL中提取文件名
            if 'song_name' in song_info and 'artist' in song_info:
                song_name = song_info['song_name']
                artist = song_info['artist']
                music_format = song_info.get('format', 'flac')
                filename = f"{song_name} - {artist}.{music_format}"
            else:
                # 如果没有歌曲信息，使用当前时间作为文件名
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"song_{timestamp}.flac"

            return song_url, filename

        except Exception as e:
            self.log(f"获取下载链接失败: {e}")
            raise


def main():
    root = tk.Tk()
    app = MusicDownloaderApp(root)
    root.mainloop()


if __name__ == '__main__':
    main()