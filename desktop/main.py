import flet as ft
import json
import os

CONFIG_FILE = "config.json"

def main(page: ft.Page):
    page.title = "LLM Agent 配置"
    page.window_width = 500
    page.window_height = 550
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER

    # --- 控件定义 ---
    api_key_field = ft.TextField(
        label="API Key",
        password=True,
        can_reveal_password=True,
        width=400
    )
    model_name_dropdown = ft.Dropdown(
        label="模型名称",
        options=[
            ft.dropdown.Option("gpt-4o"),
            ft.dropdown.Option("gpt-4-turbo"),
            ft.dropdown.Option("claude-3-opus-20240229"),
            ft.dropdown.Option("gemini-1.5-pro-latest"),
        ],
        width=400
    )
    temperature_slider = ft.Slider(min=0, max=2, divisions=20, label="Temperature: {value}", value=0.7)
    status_text = ft.Text(value="请先加载或填写配置", color=ft.colors.GREY)

    # --- 功能函数 ---
    def load_config(e):
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r") as f:
                config = json.load(f)
                api_key_field.value = config.get("api_key", "")
                model_name_dropdown.value = config.get("model_name", "gpt-4o")
                temperature_slider.value = config.get("temperature", 0.7)
                status_text.value = "配置已加载！"
                status_text.color = ft.colors.GREEN
        else:
            status_text.value = "未找到配置文件，请填写并保存。"
            status_text.color = ft.colors.ORANGE
        page.update()

    def save_config(e):
        config = {
            "api_key": api_key_field.value,
            "model_name": model_name_dropdown.value,
            "temperature": temperature_slider.value
        }
        try:
            with open(CONFIG_FILE, "w") as f:
                json.dump(config, f, indent=4)
            status_text.value = "配置已成功保存！"
            status_text.color = ft.colors.GREEN
            # 可以添加一个成功的对话框
            page.snack_bar = ft.SnackBar(ft.Text("保存成功!"), open=True)
        except Exception as ex:
            status_text.value = f"保存失败: {ex}"
            status_text.color = ft.colors.RED
        page.update()

    # --- 页面加载时自动加载配置 ---
    load_config(None)

    # --- 布局 ---
    page.add(
        ft.Column(
            [
                ft.Text("大语言模型 Agent 设置", size=24, weight=ft.FontWeight.BOLD),
                ft.Divider(),
                api_key_field,
                model_name_dropdown,
                ft.Text("模型温度 (Temperature)"),
                temperature_slider,
                ft.Row(
                    [
                        ft.ElevatedButton("保存配置", icon=ft.icons.SAVE, on_click=save_config),
                        # 可以在这里加一个“启动服务”的按钮，使用 subprocess 模块来运行你的服务器脚本
                    ],
                    alignment=ft.MainAxisAlignment.END
                ),
                ft.Divider(),
                status_text,
            ],
            spacing=20,
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER
        )
    )

if __name__ == "__main__":
    ft.app(target=main)