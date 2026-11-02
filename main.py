import os
import sys
import traceback
import logging
import ctypes
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QApplication, QMessageBox
from ui import AutoAnswerApp
from database import QuestionDatabase
from styles import get_app_icon

# 明确设置 Windows 应用程序用户模型 ID (AppUserModelID)
# 彻底解决 Windows 任务栏显示为 Python 默认白框图标的问题，确保独立任务栏图标
try:
    myappid = "taoshiwan.autoanswer.studio.v2"
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
except Exception:
    pass

# 兼容高分辨率（High DPI）屏幕缩放，防止字体发虚或布局变形
if hasattr(Qt, 'AA_EnableHighDpiScaling'):
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
if hasattr(Qt, 'AA_UseHighDpiPixmaps'):
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

# 安全设置 Qt 平台插件路径（仅在非打包环境且路径实际存在时配置，避免跨机崩溃）
if not hasattr(sys, '_MEIPASS'):
    possible_plugin_path = os.path.join(os.path.dirname(__file__), 'venv', 'Lib', 'site-packages', 'PyQt5', 'Qt5', 'plugins')
    if os.path.exists(possible_plugin_path):
        os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = possible_plugin_path

# 配置日志记录 (使用 UTF-8 编码)
logging.basicConfig(
    filename='app_error.log',
    encoding='utf-8',
    level=logging.ERROR,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def main():
    try:
        app = QApplication(sys.argv)
        
        # 全局装载应用专属高保真 Logo 图标 (支持任务栏、托盘与全部模态弹窗)
        app_icon = get_app_icon()
        if not app_icon.isNull():
            app.setWindowIcon(app_icon)
        
        # 全局锁定矢量微软雅黑，彻底根除高分屏下回退到宋体位图导致的字体破碎与笔画缺失
        app_font = QFont("Microsoft YaHei")
        app_font.setPointSize(9)
        app.setFont(app_font)
        
        # 初始化题库数据库
        question_db = QuestionDatabase()
        
        # 创建并显示主窗口
        window = AutoAnswerApp(question_db)
        window.show()
        
        return app.exec_()
    except Exception as e:
        # 记录异常信息到日志文件
        error_msg = f"程序发生错误: {str(e)}\n{traceback.format_exc()}"
        logging.error(error_msg)
        
        # 显示错误对话框
        if 'app' in locals():
            QMessageBox.critical(None, "程序错误", f"程序发生错误: {str(e)}\n请查看app_error.log获取详细信息")
        
        return 1

if __name__ == "__main__":
    sys.exit(main())