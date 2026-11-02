"""
现代化 UI 设计规范与样式系统 (Modern Fluent / Flat Theme)
提供现代全局 QSS 样式表、调色板、状态彩色徽章代理 (StatusBadgeDelegate) 以及指标统计卡片 (MetricCard)。
全面采用 Microsoft YaHei (微软雅黑) 矢量字体渲染，彻底解决多候选字体回退导致的文字断裂、缺失与点阵模糊问题。
"""

from PyQt5.QtWidgets import (QFrame, QLabel, QVBoxLayout, QHBoxLayout, QStyledItemDelegate, 
                             QStyle, QDialog, QPushButton, QWidget)
from PyQt5.QtCore import Qt, QRectF, QSize
from PyQt5.QtGui import QColor, QPainter, QBrush, QPen, QFont, QPainterPath, QPixmap, QIcon
from config import get_resource_path, APP_VERSION
import os

# 现代化调色板
THEME_COLORS = {
    # 核心背景与表面
    "window_bg": "#f8fafc",       # 现代微冷灰背景 (Slate 50)
    "card_bg": "#ffffff",         # 纯白卡片容器背景
    "card_border": "#e2e8f0",     # 细浅灰边框 (Slate 200)
    "card_border_hover": "#cbd5e1",
    
    # 文字层级
    "text_primary": "#1e293b",    # 主标题与正文 (Slate 800)
    "text_secondary": "#64748b",  # 次级提示 (Slate 500)
    "text_muted": "#94a3b8",      # 弱化提示 / 占位符 (Slate 400)
    
    # 品牌与状态主色
    "primary": "#2563eb",         # 科技蓝 (Blue 600)
    "primary_hover": "#3b82f6",   # 悬浮亮蓝 (Blue 500)
    "primary_active": "#1d4ed8",  # 按下深蓝 (Blue 700)
    "primary_bg": "#eff6ff",      # 极浅蓝背景 (Blue 50)
    
    "success": "#10b981",         # 翠绿 (Emerald 500)
    "success_hover": "#059669",
    "success_bg": "#ecfdf5",
    "success_text": "#047857",
    
    "warning": "#f59e0b",         # 琥珀黄 (Amber 500)
    "warning_hover": "#d97706",
    "warning_bg": "#fffbeb",
    "warning_text": "#b45309",
    
    "danger": "#ef4444",          # 柔和赤红 (Red 500)
    "danger_hover": "#dc2626",
    "danger_bg": "#fef2f2",
    "danger_text": "#b91c1c",
    
    "info": "#0284c7",            # 天空蓝 (Sky 600)
    "info_bg": "#f0f9ff",
    "info_text": "#0369a1",
    
    "neutral_bg": "#f1f5f9",      # 待处理灰 (Slate 100)
    "neutral_text": "#475569",    # 灰文字 (Slate 600)
    "neutral_dot": "#94a3b8",     # 灰圆点
}

# 全局现代化 QSS 样式表 (锁定 Microsoft YaHei 单一标准矢量字体)
MODERN_STYLE_SHEET = """
/* 全局基础设置 */
QMainWindow, QDialog, QWidget {
    background-color: #f8fafc;
    color: #1e293b;
    font-family: "Microsoft YaHei";
    font-size: 13px;
    outline: none;
}

/* 分割线与通用面板容器 */
QSplitter::handle {
    background-color: #e2e8f0;
    width: 2px;
    height: 2px;
}
QSplitter::handle:hover {
    background-color: #3b82f6;
}

/* 选项卡 QTabWidget 现代平铺风格 - 充足高度与垂直居中，消除文字截断 */
QTabWidget::pane {
    border: 1px solid #e2e8f0;
    background-color: #ffffff;
    border-radius: 8px;
    top: -1px;
}

QTabBar::tab {
    background-color: #f1f5f9;
    color: #475569;
    border: 1px solid #e2e8f0;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    min-height: 32px;
    min-width: 104px;
    padding: 0 16px;
    margin-right: 4px;
    font-size: 13px;
    font-family: "Microsoft YaHei";
}

QTabBar::tab:hover {
    background-color: #e2e8f0;
    color: #1e293b;
}

QTabBar::tab:selected {
    background-color: #ffffff;
    color: #2563eb;
    border-bottom: 2px solid #2563eb;
    font-weight: bold;
}

/* 输入框 QLineEdit & QTextEdit */
QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QComboBox {
    background-color: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    padding: 6px 10px;
    color: #1e293b;
    selection-background-color: #bfdbfe;
    selection-color: #1e293b;
    font-size: 12px;
    font-family: "Microsoft YaHei";
}

QLineEdit:hover, QTextEdit:hover, QPlainTextEdit:hover, QSpinBox:hover, QComboBox:hover {
    border-color: #94a3b8;
}

QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QSpinBox:focus, QComboBox:focus {
    border: 1.5px solid #2563eb;
    background-color: #ffffff;
}

QLineEdit:disabled, QTextEdit:disabled, QSpinBox:disabled, QComboBox:disabled {
    background-color: #f1f5f9;
    color: #94a3b8;
    border-color: #e2e8f0;
}

/* 下拉框 QComboBox 细节 */
QComboBox {
    padding-right: 20px;
}

QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 24px;
    border-left: none;
}

QComboBox::down-arrow {
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid #64748b;
    width: 0px;
    height: 0px;
    margin-right: 8px;
}

QComboBox QAbstractItemView {
    background-color: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    selection-background-color: #eff6ff;
    selection-color: #2563eb;
    padding: 4px;
    font-family: "Microsoft YaHei";
}

/* 按钮通用风格 */
QPushButton {
    background-color: #ffffff;
    color: #1e293b;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    padding: 6px 14px;
    font-size: 12px;
    font-family: "Microsoft YaHei";
}

QPushButton:hover {
    background-color: #f8fafc;
    border-color: #94a3b8;
    color: #0f172a;
}

QPushButton:pressed {
    background-color: #f1f5f9;
    border-color: #64748b;
}

QPushButton:disabled {
    background-color: #f1f5f9;
    color: #94a3b8;
    border-color: #e2e8f0;
}

/* 特色按钮样式 */
QPushButton#primary_btn {
    background-color: #2563eb;
    color: #ffffff;
    border: 1px solid #1d4ed8;
    font-weight: bold;
}
QPushButton#primary_btn:hover {
    background-color: #3b82f6;
    border-color: #2563eb;
}
QPushButton#primary_btn:pressed {
    background-color: #1d4ed8;
}
QPushButton#primary_btn:disabled {
    background-color: #93c5fd;
    border-color: #bfdbfe;
    color: #ffffff;
}

QPushButton#start_btn {
    background-color: #10b981;
    color: #ffffff;
    border: 1px solid #059669;
    font-weight: bold;
    font-size: 13px;
    padding: 8px 18px;
}
QPushButton#start_btn:hover {
    background-color: #34d399;
    border-color: #10b981;
}
QPushButton#start_btn:pressed {
    background-color: #059669;
}
QPushButton#start_btn:disabled {
    background-color: #a7f3d0;
    border-color: #6ee7b7;
    color: #ffffff;
}

QPushButton#pause_btn {
    background-color: #f59e0b;
    color: #ffffff;
    border: 1px solid #d97706;
    font-weight: bold;
}
QPushButton#pause_btn:hover {
    background-color: #fbbf24;
}
QPushButton#pause_btn:pressed {
    background-color: #d97706;
}

QPushButton#stop_btn {
    background-color: #ef4444;
    color: #ffffff;
    border: 1px solid #dc2626;
    font-weight: bold;
}
QPushButton#stop_btn:hover {
    background-color: #f87171;
}
QPushButton#stop_btn:pressed {
    background-color: #dc2626;
}

QPushButton#danger_action_btn {
    background-color: #fff1f2;
    color: #e11d48;
    border: 1px solid #fecdd3;
}
QPushButton#danger_action_btn:hover {
    background-color: #ffe4e6;
    border-color: #fda4af;
}

/* 表格 QTableWidget 现代质感 */
QTableWidget {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 6px;
    gridline-color: #f1f5f9;
    selection-background-color: #eff6ff;
    selection-color: #1e293b;
    font-size: 12px;
    font-family: "Microsoft YaHei";
}

QTableWidget::item {
    padding: 5px 8px;
    border-bottom: 1px solid #f1f5f9;
}

QTableWidget::item:hover {
    background-color: #f8fafc;
}

QTableWidget::item:selected {
    background-color: #eff6ff;
    color: #1d4ed8;
}

QHeaderView::section {
    background-color: #f8fafc;
    color: #475569;
    font-weight: bold;
    font-size: 12px;
    padding: 7px 8px;
    border: none;
    border-bottom: 2px solid #e2e8f0;
    font-family: "Microsoft YaHei";
}

/* 现代化滚动条 QScrollBar */
QScrollBar:vertical {
    border: none;
    background-color: transparent;
    width: 7px;
    margin: 0px 0px 0px 0px;
}

QScrollBar::handle:vertical {
    background-color: #cbd5e1;
    border-radius: 3px;
    min-height: 24px;
}

QScrollBar::handle:vertical:hover {
    background-color: #94a3b8;
}

QScrollBar::sub-line:vertical, QScrollBar::add-line:vertical {
    height: 0px;
}

QScrollBar:horizontal {
    border: none;
    background-color: transparent;
    height: 7px;
    margin: 0px 0px 0px 0px;
}

QScrollBar::handle:horizontal {
    background-color: #cbd5e1;
    border-radius: 3px;
    min-width: 24px;
}

QScrollBar::handle:horizontal:hover {
    background-color: #94a3b8;
}

QScrollBar::sub-line:horizontal, QScrollBar::add-line:horizontal {
    width: 0px;
}

/* 复选框 QCheckBox */
QCheckBox {
    spacing: 7px;
    color: #334155;
    font-size: 12px;
    font-family: "Microsoft YaHei";
}

QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border: 1px solid #cbd5e1;
    border-radius: 4px;
    background-color: #ffffff;
}

QCheckBox::indicator:hover {
    border-color: #2563eb;
}

QCheckBox::indicator:checked {
    background-color: #2563eb;
    border-color: #2563eb;
    image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='white'%3E%3Cpath d='M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z'/%3E%3C/svg%3E");
}

/* 滑块 QSlider 现代设计 */
QSlider::groove:horizontal {
    border: none;
    height: 5px;
    background-color: #e2e8f0;
    border-radius: 2px;
}

QSlider::sub-page:horizontal {
    background-color: #3b82f6;
    border-radius: 2px;
}

QSlider::handle:horizontal {
    background-color: #ffffff;
    border: 2px solid #2563eb;
    width: 14px;
    margin: -5px 0;
    border-radius: 8px;
}

QSlider::handle:horizontal:hover {
    background-color: #eff6ff;
    border-color: #1d4ed8;
}

/* 进度条 QProgressBar */
QProgressBar {
    border: 1px solid #e2e8f0;
    border-radius: 4px;
    text-align: center;
    background-color: #f1f5f9;
    color: #334155;
    font-size: 11px;
    font-family: "Microsoft YaHei";
}

QProgressBar::chunk {
    background-color: #10b981;
    border-radius: 3px;
}
"""

class StatusBadgeDelegate(QStyledItemDelegate):
    """
    状态药丸徽章代理 (Status Badge Delegate)
    在 QTableWidget 中以现代微胶囊药丸形式高保真绘制状态项
    """
    
    BADGE_CONFIG = {
        "待处理": {
            "bg": QColor("#f1f5f9"),
            "text": QColor("#475569"),
            "border": QColor("#e2e8f0"),
            "dot": QColor("#94a3b8")
        },
        "进行中": {
            "bg": QColor("#fef3c7"),
            "text": QColor("#b45309"),
            "border": QColor("#fde68a"),
            "dot": QColor("#f59e0b")
        },
        "已完成": {
            "bg": QColor("#ecfdf5"),
            "text": QColor("#047857"),
            "border": QColor("#a7f3d0"),
            "dot": QColor("#10b981")
        },
        "失败": {
            "bg": QColor("#fef2f2"),
            "text": QColor("#b91c1c"),
            "border": QColor("#fecaca"),
            "dot": QColor("#ef4444")
        },
        "暂停": {
            "bg": QColor("#eef2ff"),
            "text": QColor("#4338ca"),
            "border": QColor("#c7d2fe"),
            "dot": QColor("#6366f1")
        }
    }
    
    @classmethod
    def get_style_for_text(cls, status_text: str):
        text = status_text.strip()
        if "已完成" in text or "成功" in text:
            return cls.BADGE_CONFIG["已完成"]
        elif "进行" in text or "答题" in text or "登录" in text or "处理中" in text or "开始" in text:
            return cls.BADGE_CONFIG["进行中"]
        elif "失败" in text or "错误" in text or "异常" in text:
            return cls.BADGE_CONFIG["失败"]
        elif "暂停" in text:
            return cls.BADGE_CONFIG["暂停"]
        else:
            return cls.BADGE_CONFIG["待处理"]

    def paint(self, painter: QPainter, option, index):
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing, True)
        
        # 绘制背景选中/悬停色
        if option.state & QStyle.State_Selected:
            painter.fillRect(option.rect, QColor("#eff6ff"))
        elif option.state & QStyle.State_MouseOver:
            painter.fillRect(option.rect, QColor("#f8fafc"))
        else:
            painter.fillRect(option.rect, QColor("#ffffff"))

        status_text = index.data() or ""
        if not status_text:
            painter.restore()
            return
            
        style = self.get_style_for_text(status_text)
        
        # 计算徽章药丸尺寸 (强制指定 Microsoft YaHei 9pt)
        font = QFont("Microsoft YaHei", 9)
        font.setBold(True)
        painter.setFont(font)
        
        metrics = painter.fontMetrics()
        text_width = metrics.horizontalAdvance(status_text)
        
        badge_height = 22
        dot_diameter = 6
        padding_x = 9
        spacing = 5
        badge_width = padding_x * 2 + dot_diameter + spacing + text_width
        
        # 居中显示药丸
        rect = option.rect
        x = rect.x() + (rect.width() - badge_width) / 2
        y = rect.y() + (rect.height() - badge_height) / 2
        
        badge_rect = QRectF(x, y, badge_width, badge_height)
        
        # 绘制胶囊背景
        painter.setBrush(QBrush(style["bg"]))
        painter.setPen(QPen(style["border"], 1))
        painter.drawRoundedRect(badge_rect, badge_height / 2, badge_height / 2)
        
        # 绘制彩色圆点
        dot_x = x + padding_x
        dot_y = y + (badge_height - dot_diameter) / 2
        painter.setBrush(QBrush(style["dot"]))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(QRectF(dot_x, dot_y, dot_diameter, dot_diameter))
        
        # 绘制状态文字
        text_x = dot_x + dot_diameter + spacing
        painter.setPen(QPen(style["text"]))
        text_rect = QRectF(text_x, y, text_width + 4, badge_height)
        painter.drawText(text_rect, Qt.AlignVCenter | Qt.AlignLeft, status_text)
        
        painter.restore()


class MetricCard(QFrame):
    """
    现代扁平化统计指标小卡片 (KPI Card)
    展示当前批次任务的关键运营数据（总账号、待答题、答题中、已完成、失败等）
    """
    def __init__(self, title: str, value: str = "0", accent_color: str = "#2563eb", bg_tint: str = "#ffffff"):
        super().__init__()
        self.accent_color = accent_color
        self.setObjectName("metricCard")
        
        self.setStyleSheet(f"""
            QFrame#metricCard {{
                background-color: {bg_tint};
                border: 1px solid #e2e8f0;
                border-radius: 8px;
            }}
            QFrame#metricCard:hover {{
                border-color: #cbd5e1;
                background-color: #ffffff;
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(2)
        
        # 标题标签 (纯粹雅黑矢量字体)
        self.title_label = QLabel(title)
        self.title_label.setStyleSheet("color: #64748b; font-size: 11px; font-family: 'Microsoft YaHei';")
        layout.addWidget(self.title_label)
        
        # 数值标签
        self.value_label = QLabel(str(value))
        self.value_label.setStyleSheet(f"color: {accent_color}; font-size: 18px; font-weight: bold; font-family: 'Microsoft YaHei';")
        layout.addWidget(self.value_label)
        
    def set_value(self, value):
        self.value_label.setText(str(value))


def get_app_icon() -> QIcon:
    """
    获取全局统一的应用高清 Logo 图标 (QIcon)
    优先读取 assets/app_icon.ico 或 assets/app_icon.png，兼容打包环境与源码环境
    """
    for filename in ["assets/app_icon.ico", "assets/app_icon.png", "assets/logo.svg"]:
        path = get_resource_path(filename)
        if os.path.exists(path):
            icon = QIcon(path)
            if not icon.isNull():
                return icon
    return QIcon()


class AboutDialog(QDialog):
    """
    现代化关于对话框 (Modern About Dialog)
    以大号圆角高保真 Logo 展示暴打淘师湾的品牌形象与核心技术特性
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("关于 暴打淘师湾")
        self.setFixedSize(530, 480)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.setWindowIcon(get_app_icon())
        
        # 强制设置全窗口矢量微软雅黑字体
        base_font = QFont("Microsoft YaHei", 9)
        self.setFont(base_font)
        
        self.setStyleSheet("""
            QDialog {
                background-color: #ffffff;
                font-family: 'Microsoft YaHei';
            }
            QLabel {
                font-family: 'Microsoft YaHei';
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 20, 28, 20)
        layout.setSpacing(10)
        
        # 顶部品牌 Logo 大图标容器
        logo_container = QHBoxLayout()
        logo_label = QLabel()
        logo_label.setFixedSize(76, 76)
        logo_label.setStyleSheet("""
            background-color: #ffffff;
            border: 2px solid #ffedd5;
            border-radius: 16px;
            padding: 4px;
        """)
        icon_path = get_resource_path("assets/app_icon.png")
        if os.path.exists(icon_path):
            pixmap = QPixmap(icon_path).scaled(68, 68, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            logo_label.setPixmap(pixmap)
            logo_label.setAlignment(Qt.AlignCenter)
        logo_container.addStretch()
        logo_container.addWidget(logo_label)
        logo_container.addStretch()
        layout.addLayout(logo_container)
        
        # 标题与版本
        title_label = QLabel("暴打淘师湾")
        title_label.setFont(QFont("Microsoft YaHei", 15, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("color: #0f172a;")
        layout.addWidget(title_label)
        
        version_label = QLabel(f"{APP_VERSION} 极速自适应版 · 纯净零释放")
        version_label.setFont(QFont("Microsoft YaHei", 9, QFont.Medium))
        version_label.setAlignment(Qt.AlignCenter)
        version_label.setStyleSheet("color: #ea580c;")
        layout.addWidget(version_label)
        
        # 特性卡片信息区
        desc_card = QFrame()
        desc_card.setStyleSheet("""
            QFrame {
                background-color: #f8fafc;
                border: 1px solid #e2e8f0;
                border-radius: 8px;
            }
        """)
        desc_layout = QVBoxLayout(desc_card)
        desc_layout.setSpacing(6)
        desc_layout.setContentsMargins(12, 10, 12, 10)
        
        features = [
            ("⚡", "双引擎驱动自适应", "支持 Edge 与 Chrome，国内镜像秒级自动补全"),
            ("🛡️", "零假阳性与状态自愈", "彻底根除误报与遮罩卡死，自动清理脏会话无缝流转"),
            ("🔍", "双阶极速题库匹配", "精准匹配 + 中文 2-Gram 模糊联想，题库只读绿色加载"),
            ("📝", "主观题智能清洗", "富文本标签过滤与多行排版转换，告别死循环"),
            ("🥊", "图标设计寓意", "热血小人过招飞踢，寓意破除机械重复，势如破竹！")
        ]
        
        for icon_emoji, title, desc in features:
            row = QHBoxLayout()
            row.setSpacing(8)
            row.setContentsMargins(0, 1, 0, 1)
            
            icon_lbl = QLabel(icon_emoji)
            icon_lbl.setFont(QFont("Microsoft YaHei", 10))
            icon_lbl.setFixedWidth(20)
            icon_lbl.setAlignment(Qt.AlignCenter)
            row.addWidget(icon_lbl)
            
            text_lbl = QLabel(f"<b>{title}</b>：{desc}")
            text_lbl.setFont(QFont("Microsoft YaHei", 9))
            text_lbl.setStyleSheet("color: #334155;")
            row.addWidget(text_lbl, 1)
            
            desc_layout.addLayout(row)
        
        layout.addWidget(desc_card)
        
        # 底部按钮区
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        close_btn = QPushButton("朕已阅")
        close_btn.setFont(QFont("Microsoft YaHei", 9, QFont.Bold))
        close_btn.setObjectName("primary_btn")
        close_btn.setFixedSize(110, 32)
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)


class HelpGuideDialog(QDialog):
    """
    现代化使用指南对话框 (Modern Help Guide Dialog)
    以结构化卡片展示快捷上手指南与关键操作提示
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("暴打淘师湾 - 快速使用指南")
        self.setFixedSize(540, 510)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.setWindowIcon(get_app_icon())
        self.setFont(QFont("Microsoft YaHei", 9))
        
        self.setStyleSheet("""
            QDialog {
                background-color: #ffffff;
                font-family: 'Microsoft YaHei';
            }
            QLabel {
                font-family: 'Microsoft YaHei';
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 18)
        layout.setSpacing(10)
        
        # 标题栏
        header_row = QHBoxLayout()
        header_row.setSpacing(10)
        
        icon_lbl = QLabel()
        icon_lbl.setFixedSize(36, 36)
        icon_path = get_resource_path("assets/app_icon.png")
        if os.path.exists(icon_path):
            pixmap = QPixmap(icon_path).scaled(34, 34, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            icon_lbl.setPixmap(pixmap)
            icon_lbl.setAlignment(Qt.AlignCenter)
        header_row.addWidget(icon_lbl)
        
        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        h_title = QLabel("暴打淘师湾 极速上手手册")
        h_title.setFont(QFont("Microsoft YaHei", 13, QFont.Bold))
        h_title.setStyleSheet("color: #0f172a;")
        title_box.addWidget(h_title)
        
        h_sub = QLabel("5 步掌握全流程高效自动化作业通关")
        h_sub.setFont(QFont("Microsoft YaHei", 9))
        h_sub.setStyleSheet("color: #64748b;")
        title_box.addWidget(h_sub)
        
        header_row.addLayout(title_box, 1)
        layout.addLayout(header_row)
        
        # 指南步骤卡片
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: #f8fafc;
                border: 1px solid #e2e8f0;
                border-radius: 8px;
            }
        """)
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(8)
        card_layout.setContentsMargins(14, 12, 14, 12)
        
        steps = [
            ("1. 批量添加账号", "在左侧输入框输入或直接粘贴多行账号，支持「纯账号」或「账号:密码」两种格式，回车或点击添加即可。"),
            ("2. 选择执行模式", "单线程模式开启独立可视化浏览器，适合首次答题；多线程并发模式按 CPU 核心智能调度，极速通关。"),
            ("3. 题库极速匹配", "内置题库只读加载，绝不向外部释放临时文件；外部若放置 questions.db 会优先选用，支持自建私有题库。"),
            ("4. 驱动自适应下载", "已接入阿里云国内镜像高速下载，自动对齐本地 Edge 或 Chrome 版本，并强制豁免本地代理，开箱即用。"),
            ("5. 智能异常处置", "遇到滑块人机验证，请直接在弹出的浏览器中手动滑动，系统将自动捕获并无缝继续答题。")
        ]
        
        for step_title, step_desc in steps:
            s_box = QVBoxLayout()
            s_box.setSpacing(2)
            t_lbl = QLabel(f"<b>{step_title}</b>")
            t_lbl.setFont(QFont("Microsoft YaHei", 9))
            t_lbl.setStyleSheet("color: #1e293b;")
            s_box.addWidget(t_lbl)
            
            d_lbl = QLabel(step_desc)
            d_lbl.setFont(QFont("Microsoft YaHei", 8))
            d_lbl.setWordWrap(True)
            d_lbl.setStyleSheet("color: #64748b; line-height: 130%;")
            s_box.addWidget(d_lbl)
            
            card_layout.addLayout(s_box)
            
        layout.addWidget(card)
        
        # 底部关闭按钮
        b_row = QHBoxLayout()
        b_row.addStretch()
        ok_btn = QPushButton("我知道了")
        ok_btn.setFont(QFont("Microsoft YaHei", 9, QFont.Bold))
        ok_btn.setObjectName("primary_btn")
        ok_btn.setFixedSize(110, 32)
        ok_btn.clicked.connect(self.accept)
        b_row.addWidget(ok_btn)
        b_row.addStretch()
        layout.addLayout(b_row)


class BrandHeaderCard(QFrame):
    """
    工作台顶部品牌卡片 (Brand Header Card)
    统一展示高质感应用 Logo、软件标题、PRO 极速标签、状态微标与使用说明/关于入口
    """
    def __init__(self, on_help_clicked=None, on_about_clicked=None, parent=None):
        super().__init__(parent)
        self.setObjectName("brandHeaderCard")
        self.setFixedHeight(62)
        
        self.setStyleSheet("""
            QFrame#brandHeaderCard {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #ffffff, stop:0.82 #ffffff, stop:1 #fff7ed);
                border: 1px solid #e2e8f0;
                border-radius: 10px;
            }
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 6, 14, 6)
        layout.setSpacing(12)
        
        # 1. 品牌 Logo 图标 (圆角高保真展示)
        self.logo_label = QLabel()
        self.logo_label.setFixedSize(46, 46)
        self.logo_label.setStyleSheet("""
            background-color: #ffffff;
            border: 1px solid #ffedd5;
            border-radius: 10px;
            padding: 2px;
        """)
        icon_path = get_resource_path("assets/app_icon.png")
        if os.path.exists(icon_path):
            pixmap = QPixmap(icon_path).scaled(42, 42, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.logo_label.setPixmap(pixmap)
            self.logo_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.logo_label)
        
        # 2. 标题与状态标签组
        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)
        text_layout.setContentsMargins(0, 2, 0, 2)
        
        # 第一行：软件名 + 胶囊标签
        title_row = QHBoxLayout()
        title_row.setSpacing(8)
        title_row.setContentsMargins(0, 0, 0, 0)
        
        main_title = QLabel("暴打淘师湾")
        main_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #0f172a; font-family: 'Microsoft YaHei';")
        title_row.addWidget(main_title)
        
        # 橙色热血微胶囊
        badge_pro = QLabel("⚡ PRO 极速版")
        badge_pro.setStyleSheet("""
            font-size: 10px;
            font-weight: bold;
            background-color: #ffedd5;
            color: #c2410c;
            border: 1px solid #fed7aa;
            border-radius: 4px;
            padding: 1px 6px;
        """)
        title_row.addWidget(badge_pro)
        
        # 绿色引擎适配微标
        badge_status = QLabel("● 双引擎自适应")
        badge_status.setStyleSheet("""
            font-size: 10px;
            background-color: #ecfdf5;
            color: #047857;
            border: 1px solid #a7f3d0;
            border-radius: 10px;
            padding: 1px 8px;
        """)
        title_row.addWidget(badge_status)
        title_row.addStretch()
        text_layout.addLayout(title_row)
        
        # 第二行：副标题描述
        sub_title = QLabel("现代化全自动答题工作台 · 毫秒级双阶检索匹配 · 纯净零释放运行")
        sub_title.setStyleSheet("font-size: 11px; color: #64748b; font-family: 'Microsoft YaHei';")
        text_layout.addWidget(sub_title)
        
        layout.addLayout(text_layout, 1)
        
        # 3. 右侧快捷操作按钮区 (帮助与关于)
        btn_box = QHBoxLayout()
        btn_box.setSpacing(8)
        
        if on_help_clicked:
            help_btn = QPushButton("💡 使用指南")
            help_btn.setStyleSheet("""
                QPushButton {
                    background-color: #f8fafc;
                    border: 1px solid #cbd5e1;
                    color: #475569;
                    font-size: 11px;
                    padding: 5px 10px;
                    border-radius: 6px;
                }
                QPushButton:hover {
                    background-color: #f1f5f9;
                    color: #1e293b;
                    border-color: #94a3b8;
                }
            """)
            help_btn.clicked.connect(on_help_clicked)
            btn_box.addWidget(help_btn)
            
        about_btn = QPushButton("🥋 关于")
        about_btn.setStyleSheet("""
            QPushButton {
                background-color: #fff7ed;
                border: 1px solid #fdba74;
                color: #c2410c;
                font-size: 11px;
                font-weight: 500;
                padding: 5px 12px;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #ffedd5;
                color: #9a3412;
            }
        """)
        about_btn.clicked.connect(on_about_clicked if on_about_clicked else self._show_default_about)
        btn_box.addWidget(about_btn)
        
        layout.addLayout(btn_box)

    def _show_default_about(self):
        dlg = AboutDialog(self.window())
        dlg.exec_()

