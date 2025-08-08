import flet as ft
import json
import os
import subprocess
import threading
import time

CONFIG_FILE = "config.json"

def main(page: ft.Page):
    page.title = "LLM Agent 配置"
    page.window.resizable = True
    page.window.width = 1000
    page.window.height = 850
    page.window.min_width = 1000
    page.window.min_height = 800
    page.vertical_alignment = ft.MainAxisAlignment.START
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.padding = 20

    # --- 服务器状态变量 ---
    server_process = None
    server_running = False

    # --- 控件定义 ---
    config_name_field = ft.TextField(
        label="配置名称",
        hint_text="为您的配置起一个名字",
        width=400
    )
    
    api_key_field = ft.TextField(
        label="api_key",
        password=True,
        can_reveal_password=True,
        width=400
    )
    base_url_field = ft.TextField(
        label="base_url",
        hint_text="API基础URL，例如：https://api.openai.com/v1",
        width=400
    )
    model_name_field = ft.TextField(
        label="model_name",
        width=400
    )
    temperature_field = ft.TextField(
        label="temperature",
        width=400
    )
    
    # 配置选择下拉框
    config_dropdown = ft.Dropdown(
        label="选择配置",
        width=400,
        on_change=lambda e: load_selected_config(e)
    )
    
    status_text = ft.Text(value="请先加载或填写配置", color=ft.Colors.GREY)
    
    # 服务器控制按钮
    start_server_btn = ft.ElevatedButton(
        "启动服务器", 
        icon=ft.Icons.PLAY_ARROW, 
        on_click=lambda e: start_server(e),
        color=ft.Colors.GREEN
    )
    stop_server_btn = ft.ElevatedButton(
        "停止服务器", 
        icon=ft.Icons.STOP, 
        on_click=lambda e: stop_server(e),
        color=ft.Colors.RED,
        disabled=True
    )
    server_status_text = ft.Text(value="服务器状态: 未运行", color=ft.Colors.GREY)

    # --- 功能函数 ---
    def load_configs():
        """加载所有配置并更新下拉框"""
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    configs = json.load(f)
                    # 直接使用多配置格式
                    config_dropdown.options = [
                        ft.dropdown.Option(key=name, text=name)
                        for name in configs.keys()
                    ]
                    page.update()
                    return configs
            except Exception as e:
                print(f"加载配置失败: {e}")
                return {}
        return {}

    def load_selected_config(e):
        """加载选中的配置到表单"""
        if not e.control.value:
            return
            
        configs = load_configs()
        selected_config_name = e.control.value
        
        if selected_config_name in configs:
            config = configs[selected_config_name]
            config_name_field.value = selected_config_name
            api_key_field.value = config.get("api_key", "")
            base_url_field.value = config.get("base_url", "")
            model_name_field.value = config.get("model_name", "gpt-4o")
            temperature_field.value = str(config.get("temperature", 0.7))
            
            status_text.value = f"已加载配置: {selected_config_name}"
            status_text.color = ft.Colors.GREEN
            page.update()

    def save_config(e):
        """保存当前配置"""
        config_name = config_name_field.value.strip()
        if not config_name:
            status_text.value = "请输入配置名称"
            status_text.color = ft.Colors.RED
            page.update()
            return
            
        config = {
            "api_key": api_key_field.value,
            "base_url": base_url_field.value,
            "model_name": model_name_field.value,
            "temperature": float(temperature_field.value) if temperature_field.value else 0.7
        }
        
        try:
            # 加载现有配置
            configs = load_configs()
            
            # 添加或更新配置
            configs[config_name] = config
            
            # 保存到文件
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(configs, f, indent=4, ensure_ascii=False)
            
            # 更新下拉框
            config_dropdown.options = [
                ft.dropdown.Option(key=name, text=name)
                for name in configs.keys()
            ]
            config_dropdown.value = config_name
            
            status_text.value = f"配置 '{config_name}' 已成功保存！"
            status_text.color = ft.Colors.GREEN
            page.overlay.append(ft.SnackBar(ft.Text("保存成功!"), open=True))
            
        except Exception as ex:
            status_text.value = f"保存失败: {ex}"
            status_text.color = ft.Colors.RED
        page.update()

    def delete_config(e):
        """删除选中的配置"""
        if not config_dropdown.value:
            status_text.value = "请先选择要删除的配置"
            status_text.color = ft.Colors.RED
            page.update()
            return
            
        config_name = config_dropdown.value
        
        try:
            # 加载现有配置
            configs = load_configs()
            
            if config_name in configs:
                del configs[config_name]
                
                # 保存到文件
                with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                    json.dump(configs, f, indent=4, ensure_ascii=False)
                
                # 更新下拉框
                config_dropdown.options = [
                    ft.dropdown.Option(key=name, text=name)
                    for name in configs.keys()
                ]
                config_dropdown.value = None
                
                # 清空表单
                config_name_field.value = ""
                api_key_field.value = ""
                base_url_field.value = ""
                model_name_field.value = ""
                temperature_field.value = ""
                
                status_text.value = f"配置 '{config_name}' 已删除"
                status_text.color = ft.Colors.ORANGE
                page.overlay.append(ft.SnackBar(ft.Text("删除成功!"), open=True))
            else:
                status_text.value = "配置不存在"
                status_text.color = ft.Colors.RED
                
        except Exception as ex:
            status_text.value = f"删除失败: {ex}"
            status_text.color = ft.Colors.RED
        page.update()

    def clear_form(e):
        """清空表单"""
        config_name_field.value = ""
        api_key_field.value = ""
        base_url_field.value = ""
        model_name_field.value = ""
        temperature_field.value = ""
        config_dropdown.value = None
        status_text.value = "表单已清空"
        status_text.color = ft.Colors.GREY
        page.update()

    def start_server(e):
        nonlocal server_process, server_running
        if server_running:
            return
        
        try:
            add_log_message("正在启动服务器...")
            
            # 检查是否选择了配置
            if not config_dropdown.value:
                add_log_message("错误: 请先选择一个配置")
                status_text.value = "请先选择一个配置"
                status_text.color = ft.Colors.RED
                page.update()
                return
            
            config_name = config_dropdown.value
            add_log_message(f"使用配置: {config_name}")
            
            # 启动前彻底清理所有遗留的服务器进程
            kill_all_server_processes()
            
            # 启动服务器进程，传递配置名称
            server_process = subprocess.Popen(
                ["python", "launch_server.py", "--config", config_name],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=os.getcwd()  # 确保在正确的目录中运行
            )
            
            # 等待一小段时间检查进程是否正常启动
            time.sleep(1)
            if server_process.poll() is not None:
                # 进程立即退出，说明启动失败
                stdout, stderr = server_process.communicate()
                error_msg = f"服务器启动失败: {stderr}"
                add_log_message(f"错误: {error_msg}")
                raise Exception(error_msg)
            
            server_running = True
            
            # 更新UI状态
            start_server_btn.disabled = True
            stop_server_btn.disabled = False
            server_status_text.value = "服务器状态: 运行中"
            server_status_text.color = ft.Colors.GREEN
            status_text.value = "服务器已启动！"
            status_text.color = ft.Colors.GREEN
            
            add_log_message("服务器启动成功！")
            
            # 启动监控线程
            def monitor_server():
                nonlocal server_running
                while server_running and server_process.poll() is None:
                    time.sleep(1)
                if server_running:
                    async def update_status_task():
                        update_server_status(False, "服务器意外停止")
                        add_log_message("服务器意外停止")
                    page.run_task(update_status_task)
            
            threading.Thread(target=monitor_server, daemon=True).start()
            
        except Exception as ex:
            error_msg = f"启动服务器失败: {ex}"
            status_text.value = error_msg
            status_text.color = ft.Colors.RED
            add_log_message(f"错误: {error_msg}")
            server_running = False
        
        page.update()

    def stop_server(e):
        nonlocal server_process, server_running
        if not server_running:
            return
        
        try:
            add_log_message("正在停止服务器...")
            # 停止所有相关的服务器进程
            kill_all_server_processes()
            
            server_running = False
            
            # 更新UI状态
            update_server_status(False, "服务器已停止")
            status_text.value = "服务器已停止！"
            status_text.color = ft.Colors.ORANGE
            add_log_message("服务器已停止！")
            
        except Exception as ex:
            error_msg = f"停止服务器失败: {ex}"
            status_text.value = error_msg
            status_text.color = ft.Colors.RED
            add_log_message(f"错误: {error_msg}")
        
        page.update()

    def kill_all_server_processes():
        """彻底停止所有相关的服务器进程"""
        try:
            import psutil
            import platform
            
            # 查找所有相关的Python进程
            killed_processes = []
            
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    cmdline = proc.info['cmdline']
                    if cmdline:
                        cmdline_str = ' '.join(cmdline)
                        # 检查是否是我们的服务器进程
                        if ('launch_server.py' in cmdline_str or 
                            'uvicorn' in cmdline_str or
                            'python' in proc.info['name'].lower() and 'server' in cmdline_str):
                            
                            # 获取所有子进程
                            children = []
                            try:
                                children = proc.children(recursive=True)
                            except:
                                pass
                            
                            # 先停止子进程
                            for child in children:
                                try:
                                    child.terminate()
                                    child.wait(timeout=2)
                                except:
                                    try:
                                        child.kill()
                                    except:
                                        pass
                            
                            # 停止主进程
                            try:
                                proc.terminate()
                                proc.wait(timeout=3)
                            except psutil.TimeoutExpired:
                                try:
                                    proc.kill()
                                    proc.wait(timeout=2)
                                except:
                                    pass
                            
                            killed_processes.append(proc.info['pid'])
                            
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
            
            # 如果还有进程没有停止，使用系统命令强制终止
            if killed_processes:
                time.sleep(1)  # 等待进程完全停止
                
                # 再次检查是否还有相关进程
                for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                    try:
                        cmdline = proc.info['cmdline']
                        if cmdline:
                            cmdline_str = ' '.join(cmdline)
                            if ('launch_server.py' in cmdline_str or 
                                'uvicorn' in cmdline_str):
                                
                                # 使用系统命令强制终止
                                if platform.system() == "Windows":
                                    subprocess.run(["taskkill", "/F", "/PID", str(proc.info['pid'])], 
                                                 capture_output=True, timeout=5)
                                else:
                                    subprocess.run(["kill", "-9", str(proc.info['pid'])], 
                                                 capture_output=True, timeout=5)
                    except:
                        continue
            
            # 停止当前管理的进程
            if server_process and server_process.poll() is None:
                try:
                    server_process.terminate()
                    server_process.wait(timeout=2)
                except:
                    try:
                        server_process.kill()
                        server_process.wait(timeout=1)
                    except:
                        pass
                        
        except ImportError:
            # 如果没有psutil，使用基本的停止方法
            if server_process and server_process.poll() is None:
                try:
                    server_process.terminate()
                    server_process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    try:
                        server_process.kill()
                        server_process.wait(timeout=2)
                    except:
                        pass
        except Exception:
            # 最后的备用方案
            if server_process and server_process.poll() is None:
                try:
                    server_process.kill()
                except:
                    pass

    def update_server_status(running, message):
        nonlocal server_running
        server_running = running
        start_server_btn.disabled = running
        stop_server_btn.disabled = not running
        server_status_text.value = f"服务器状态: {message}"
        server_status_text.color = ft.Colors.GREEN if running else ft.Colors.GREY
        page.update()

    # --- 日志显示区域 ---
    log_display = ft.TextField(
        multiline=True,
        read_only=True,
        min_lines=32,
        max_lines=50,
        width=400,
        border_color=ft.Colors.GREY_400,
        bgcolor=ft.Colors.BLACK,
        color=ft.Colors.GREEN,
        text_style=ft.TextStyle(font_family="monospace", size=12)
    )
    
    def add_log_message(message):
        """添加日志消息到显示区域"""
        current_time = time.strftime("%H:%M:%S")
        timestamped_message = f"[{current_time}] {message}\n"
        log_display.value += timestamped_message
        # 保持最新的日志在底部
        if len(log_display.value) > 10000:  # 限制日志长度
            log_display.value = log_display.value[-8000:]
        page.update()
    
    # --- 页面加载时自动加载配置 ---
    load_configs() # 加载所有配置并更新下拉框
    
    # 应用启动时清理遗留的服务器进程
    def cleanup_on_startup():
        try:
            # 延迟执行，确保UI已经加载完成
            time.sleep(2)
            kill_all_server_processes()
        except Exception:
            pass
    
    # 在后台线程中清理遗留进程
    threading.Thread(target=cleanup_on_startup, daemon=True).start()
    
    # 添加初始日志消息
    add_log_message("DST Agent 配置界面已启动")
    
    # --- 布局 ---
    page.add(
        ft.Row(
            [
                # 左侧配置区域
                ft.Column(
                    [
                        ft.Text("DST Agent Configuration", size=24, weight=ft.FontWeight.BOLD),
                        ft.Divider(),
                        ft.Text("Config", size=18, weight=ft.FontWeight.BOLD),
                        config_name_field,
                        api_key_field,
                        base_url_field,
                        model_name_field,
                        temperature_field,
                        ft.Row(
                            [
                                ft.ElevatedButton("Save", icon=ft.Icons.SAVE, on_click=save_config),
                                ft.ElevatedButton("Delete", icon=ft.Icons.DELETE, on_click=delete_config),
                                ft.ElevatedButton("Clear", icon=ft.Icons.CLEAR_ALL, on_click=clear_form),
                            ],
                            alignment=ft.MainAxisAlignment.CENTER
                        ),
                        ft.Divider(),
                        ft.Text("Server Control", size=18, weight=ft.FontWeight.BOLD),
                        config_dropdown,
                        status_text,
                        server_status_text,
                        ft.Row(
                            [
                                start_server_btn,
                                stop_server_btn,
                            ],
                            alignment=ft.MainAxisAlignment.CENTER
                        )
                    ],
                    spacing=15,
                    alignment=ft.MainAxisAlignment.START,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    width=400
                ),
                
                # 分隔线
                ft.VerticalDivider(width=1, color=ft.Colors.GREY_400),
                
                                 # 右侧日志区域
                 ft.Column(
                     [
                         ft.Text("Server Logs", size=24, weight=ft.FontWeight.BOLD),
                         ft.Divider(),
                         log_display,
                         ft.Row(
                             [
                                 ft.ElevatedButton("Clear Logs", icon=ft.Icons.CLEAR, on_click=lambda e: clear_logs()),
                             ],
                             alignment=ft.MainAxisAlignment.CENTER
                         )
                     ],
                     spacing=15,
                     alignment=ft.MainAxisAlignment.START,
                     horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                     width=550
                 )
            ],
            alignment=ft.MainAxisAlignment.START,
            spacing=20
        )
    )
    
    def clear_logs():
        """清空日志"""
        log_display.value = ""
        page.update()
        add_log_message("日志已清空")
    
    def copy_logs():
        """复制日志到剪贴板"""
        try:
            import pyperclip
            pyperclip.copy(log_display.value)
            add_log_message("日志已复制到剪贴板")
        except ImportError:
            add_log_message("复制功能需要安装 pyperclip: pip install pyperclip")
        except Exception as e:
            add_log_message(f"复制失败: {e}")

if __name__ == "__main__":
    ft.app(target=main)