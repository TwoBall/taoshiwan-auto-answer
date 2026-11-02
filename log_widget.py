"""
现代化日志控制台组件 (Modern Log Console Widget)
支持日志分级过滤、实时自动滚屏锁定、一键复制、日志文件导出以及富文本色彩渲染。
"""

import time
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QTextEdit, QComboBox, QCheckBox, 
                             QFileDialog, QMessageBox, QApplication)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QTextCursor

class LogConsoleWidget(QWidget):
    """现代化日志控制台组件"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.logs_data = []  # 存储元组: (timestamp, level, message, color)
        self.max_stored_logs = 2000
        self.current_filter = "ALL"
        self.auto_scroll = True
        self._last_refresh = 0
        
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        
        # 顶部工具栏
        toolbar = QWidget()
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(0, 0, 0, 0)
        toolbar_layout.setSpacing(6)
        
        # 标题
        title_label = QLabel("运行日志")
        title_label.setStyleSheet("font-weight: bold; font-size: 13px; color: #1e293b;")
        toolbar_layout.addWidget(title_label)
        
        # 级别过滤器
        toolbar_layout.addSpacing(6)
        self.filter_combo = QComboBox()
        self.filter_combo.addItem("全部级别", "ALL")
        self.filter_combo.addItem("仅信息 (INFO)", "INFO")
        self.filter_combo.addItem("仅成功 (SUCCESS)", "SUCCESS")
        self.filter_combo.addItem("仅警告 (WARN)", "WARN")
        self.filter_combo.addItem("仅错误 (ERROR)", "ERROR")
        self.filter_combo.currentIndexChanged.connect(self.on_filter_changed)
        self.filter_combo.setFixedWidth(130)
        toolbar_layout.addWidget(self.filter_combo)
        
        # 自动滚动复选框
        self.auto_scroll_cb = QCheckBox("自动滚动")
        self.auto_scroll_cb.setChecked(True)
        self.auto_scroll_cb.toggled.connect(self.on_auto_scroll_toggled)
        toolbar_layout.addWidget(self.auto_scroll_cb)
        
        toolbar_layout.addStretch()
        
        # 复制按钮
        self.copy_btn = QPushButton("复制")
        self.copy_btn.setToolTip("复制当前显示的日志到剪贴板")
        self.copy_btn.clicked.connect(self.copy_logs)
        self.copy_btn.setFixedWidth(54)
        toolbar_layout.addWidget(self.copy_btn)
        
        # 导出按钮
        self.export_btn = QPushButton("导出")
        self.export_btn.setToolTip("将当前日志导出为文本文件")
        self.export_btn.clicked.connect(self.export_logs)
        self.export_btn.setFixedWidth(54)
        toolbar_layout.addWidget(self.export_btn)
        
        # 清空按钮
        self.clear_btn = QPushButton("清空")
        self.clear_btn.setToolTip("清空控制台日志显示")
        self.clear_btn.clicked.connect(self.clear_logs)
        self.clear_btn.setFixedWidth(54)
        toolbar_layout.addWidget(self.clear_btn)
        
        layout.addWidget(toolbar)
        
        # 日志文本展示区
        self.text_edit = QTextEdit()
        self.text_edit.setReadOnly(True)
        self.text_edit.setStyleSheet("""
            QTextEdit {
                background-color: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 6px;
                padding: 8px;
                font-family: "Microsoft YaHei";
                font-size: 12px;
                line-height: 1.4;
            }
        """)
        layout.addWidget(self.text_edit)

    def log(self, message: str, color: str = None):
        """记录一条日志"""
        timestamp = time.strftime("%H:%M:%S")
        
        # 自动探测日志级别
        level = "INFO"
        msg_lower = message.lower()
        if color == "red" or "error" in msg_lower or "错误" in msg_lower or "失败" in msg_lower or "✗" in message:
            level = "ERROR"
            color = "#dc2626"
        elif color == "orange" or "warn" in msg_lower or "警告" in msg_lower or "⚠" in message:
            level = "WARN"
            color = "#d97706"
        elif color == "green" or "成功" in msg_lower or "✓" in message or "完成" in msg_lower:
            level = "SUCCESS"
            color = "#059669"
        else:
            if not color:
                color = "#334155"
        
        log_entry = {
            "time": timestamp,
            "level": level,
            "msg": message,
            "color": color
        }
        
        self.logs_data.append(log_entry)
        if len(self.logs_data) > self.max_stored_logs:
            self.logs_data.pop(0)
            
        # 如果当前过滤器匹配，直接追加
        if self._matches_filter(level):
            self._append_html_line(log_entry)
            
        # 节流刷新
        current_time = time.time()
        if current_time - self._last_refresh > 0.08:
            QApplication.processEvents()
            self._last_refresh = current_time

    def _matches_filter(self, level: str) -> bool:
        if self.current_filter == "ALL":
            return True
        return self.current_filter == level

    def _append_html_line(self, entry: dict):
        # 级别徽章样式
        badge_style = {
            "INFO": "color: #2563eb; font-weight: bold;",
            "SUCCESS": "color: #059669; font-weight: bold;",
            "WARN": "color: #d97706; font-weight: bold;",
            "ERROR": "color: #dc2626; font-weight: bold;"
        }.get(entry["level"], "color: #64748b;")
        
        line_html = (
            f"<div style='margin-bottom: 3px; font-family: Consolas, monospace;'>"
            f"<span style='color: #94a3b8;'>[{entry['time']}]</span> "
            f"<span style='{badge_style}'>[{entry['level']}]</span> "
            f"<span style='color: {entry['color']};'>{entry['msg']}</span>"
            f"</div>"
        )
        self.text_edit.append(line_html)
        
        if self.auto_scroll:
            cursor = self.text_edit.textCursor()
            cursor.movePosition(QTextCursor.End)
            self.text_edit.setTextCursor(cursor)
            self.text_edit.ensureCursorVisible()

    def on_filter_changed(self, index):
        self.current_filter = self.filter_combo.currentData()
        self.rebuild_log_view()

    def rebuild_log_view(self):
        self.text_edit.clear()
        for entry in self.logs_data:
            if self._matches_filter(entry["level"]):
                self._append_html_line(entry)

    def on_auto_scroll_toggled(self, checked):
        self.auto_scroll = checked
        if checked:
            cursor = self.text_edit.textCursor()
            cursor.movePosition(QTextCursor.End)
            self.text_edit.setTextCursor(cursor)
            self.text_edit.ensureCursorVisible()

    def clear_logs(self):
        self.logs_data.clear()
        self.text_edit.clear()
        self.log("日志控制台已清空")

    def copy_logs(self):
        plain_text = self.text_edit.toPlainText()
        if not plain_text.strip():
            return
        clipboard = QApplication.clipboard()
        clipboard.setText(plain_text)
        QMessageBox.information(self, "提示", "当前显示的日志已复制到剪贴板！")

    def export_logs(self):
        plain_text = self.text_edit.toPlainText()
        if not plain_text.strip():
            QMessageBox.information(self, "提示", "当前没有可导出的日志内容。")
            return
            
        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出日志文件", f"taoshiwan_log_{time.strftime('%Y%m%d_%H%M%S')}.txt",
            "文本文件 (*.txt);;所有文件 (*.*)"
        )
        if file_path:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(plain_text)
                QMessageBox.information(self, "导出成功", f"日志已成功保存至:\n{file_path}")
            except Exception as e:
                QMessageBox.warning(self, "导出失败", f"写入文件时发生错误: {str(e)}")
