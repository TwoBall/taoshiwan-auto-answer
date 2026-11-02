#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
一键打包脚本（与 GitHub Actions 保持一致）
生成单个免安装的 Windows 可执行程序并打包为发布压缩包
"""

import os
import sys
import shutil
import subprocess

def run_cmd(cmd, description=""):
    if description:
        print(f"==> {description}")
    print(f"执行: {' '.join(cmd) if isinstance(cmd, list) else cmd}")
    subprocess.check_call(cmd, shell=isinstance(cmd, str))

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(base_dir)

    print("=" * 60)
    print("开始构建：暴打淘师湾 Windows 客户端")
    print("=" * 60)

    # 1. 检查必要文件
    if not os.path.exists("main.py"):
        print("❌ 错误: 找不到 main.py")
        sys.exit(1)
    if not os.path.exists("questions.db"):
        print("❌ 错误: 找不到 questions.db 题库文件")
        sys.exit(1)

    # 2. 安装依赖
    run_cmd([sys.executable, "-m", "pip", "install", "--upgrade", "pip"], "更新 pip")
    run_cmd([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], "安装项目依赖")
    run_cmd([sys.executable, "-m", "pip", "install", "pyinstaller"], "安装 PyInstaller")

    # 3. 清理旧构建
    print("==> 清理旧构建目录...")
    for d in ["build", "dist", "__pycache__"]:
        if os.path.exists(d):
            shutil.rmtree(d, ignore_errors=True)

    # 4. PyInstaller 打包
    pyinstaller_cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onefile",
        "--windowed",
        "--name=taoshiwan-auto-answer",
        "--icon=assets/app_icon.ico",
        "--add-data", "questions.db;.",
        "--add-data", "config.py;.",
        "--add-data", "browser_manager.py;.",
        "--add-data", "styles.py;.",
        "--add-data", "log_widget.py;.",
        "--add-data", "assets;assets",
        "--hidden-import=selenium",
        "--hidden-import=selenium.webdriver",
        "--hidden-import=selenium.webdriver.chrome.service",
        "--hidden-import=selenium.webdriver.chrome.options",
        "--hidden-import=selenium.webdriver.edge.service",
        "--hidden-import=selenium.webdriver.edge.options",
        "--hidden-import=browser_manager",
        "--hidden-import=styles",
        "--hidden-import=log_widget",
        "--hidden-import=PyQt5",
        "--hidden-import=PyQt5.QtCore",
        "--hidden-import=PyQt5.QtWidgets",
        "--hidden-import=PyQt5.QtGui",
        "--hidden-import=PyQt5.QtSvg",
        "--hidden-import=PIL",
        "--hidden-import=PIL.Image",
        "--hidden-import=psutil",
        "--hidden-import=bs4",
        "--exclude-module=PyQt5.Qt",
        "main.py"
    ]
    run_cmd(pyinstaller_cmd, "正在打包可执行文件...")

    # 5. 整理发布包
    release_dir = os.path.join("dist", "release")
    os.makedirs(release_dir, exist_ok=True)

    exe_path = os.path.join("dist", "taoshiwan-auto-answer.exe")
    if not os.path.exists(exe_path):
        print(f"❌ 打包失败: 未生成 {exe_path}")
        sys.exit(1)

    print("==> 正在准备发布文件...")
    # 同时提供英文原名与中文重命名副本，兼顾直接下载与解压查看
    shutil.copy(exe_path, os.path.join(release_dir, "taoshiwan-auto-answer.exe"))
    shutil.copy(exe_path, os.path.join(release_dir, "暴打淘师湾.exe"))
    shutil.copy("questions.db", release_dir)
    shutil.copy("config.py", release_dir)
    shutil.copy("browser_manager.py", release_dir)
    shutil.copy("styles.py", release_dir)
    shutil.copy("log_widget.py", release_dir)
    if os.path.exists("assets"):
        shutil.copytree("assets", os.path.join(release_dir, "assets"), dirs_exist_ok=True)
    if os.path.exists("README.md"):
        shutil.copy("README.md", release_dir)

    # 6. 生成 ZIP 压缩包
    zip_output = os.path.join("dist", "taoshiwan-auto-answer-windows")
    shutil.make_archive(zip_output, "zip", release_dir)

    print("\n" + "=" * 60)
    print("🎉 构建成功！")
    print(f"可执行文件: {os.path.abspath(exe_path)}")
    print(f"发布压缩包: {os.path.abspath(zip_output + '.zip')}")
    print("=" * 60)

if __name__ == "__main__":
    main()
