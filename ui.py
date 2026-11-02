"""
现代化图形用户界面 (Modern GUI with Fluent / Flat Design)
包含响应式双栏工作台、数据指标统计卡片、状态彩色药丸徽章与全功能分级日志控制台。
"""

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QLineEdit, QPushButton, QTextEdit, QTableWidget, 
                             QTableWidgetItem, QHeaderView, QTabWidget, QGroupBox, 
                             QCheckBox, QMessageBox, QSplitter, QFrame, QSlider, QProgressBar, 
                             QSpinBox, QComboBox, QMenu, QAction)
from PyQt5.QtCore import Qt, QTimer, QPoint
from PyQt5.QtGui import QIcon, QFont
import time
import re

from config import DEFAULT_PASSWORD, UI_CONFIG, OPERATION_DELAY
from automation import BrowserAutomation
from question_importer import QuestionImporter
from multi_thread_manager import MultiThreadManager
from system_monitor import ResourceWidget
from browser_manager import detect_available_browsers, resolve_browser_type
from styles import (MODERN_STYLE_SHEET, StatusBadgeDelegate, MetricCard, 
                    BrandHeaderCard, AboutDialog, HelpGuideDialog, get_app_icon)
from log_widget import LogConsoleWidget


class AutoAnswerApp(QMainWindow):
    def __init__(self, question_db):
        super().__init__()
        self.setWindowTitle(UI_CONFIG["window_title"])
        self.setWindowIcon(get_app_icon())
        # 默认工作台采用 1040x700 舒展分辨率，并设定优雅最小尺寸
        self.setGeometry(*UI_CONFIG.get("window_geometry", (100, 100, 1040, 700)))
        self.setMinimumSize(880, 580)
        
        self.accounts = []
        self.current_account_index = 0
        self.question_db = question_db
        self.browser_automation = None
        self.delay_multiplier = 1.0  # 延迟倍数
        self.multi_thread_manager = MultiThreadManager(question_db)
        self.is_multithread_mode = False
        
        # 强制窗口字体为纯矢量微软雅黑
        app_font = QFont("Microsoft YaHei")
        app_font.setPointSize(9)
        self.setFont(app_font)
        
        # 注入全局现代化样式表
        self.setStyleSheet(MODERN_STYLE_SHEET)
        
        self.initUI()
        self.setup_multithread_signals()
        
    def initUI(self):
        # 中央主窗口部件
        central_widget = QWidget()
        central_widget.setObjectName("centralWidget")
        self.setCentralWidget(central_widget)
        
        # 顶层垂直总布局（包含顶部品牌栏、工作台主体和底部现代进度条）
        overall_layout = QVBoxLayout(central_widget)
        overall_layout.setContentsMargins(10, 8, 10, 8)
        overall_layout.setSpacing(8)
        
        # 顶部品牌卡片 (Logo、标题、PRO 极速标签、状态微标与使用说明/关于入口)
        self.brand_header = BrandHeaderCard(
            on_help_clicked=self.show_help_guide,
            on_about_clicked=self.show_about_dialog
        )
        overall_layout.addWidget(self.brand_header)
        
        # 采用 QSplitter 实现响应式双栏工作台布局（左侧操作与管理面板，右侧多功能监控与日志）
        self.main_splitter = QSplitter(Qt.Horizontal)
        self.main_splitter.setChildrenCollapsible(False)
        
        # =====================================================================
        # 左侧面板：功能选项卡容器 (自动答题 / 题库管理 / 系统设置)
        # =====================================================================
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 4, 0)
        left_layout.setSpacing(6)
        
        self.tab_widget = QTabWidget()
        
        # ---------------------------------------------------------------------
        # 选项卡 1：自动答题主控台
        # ---------------------------------------------------------------------
        auto_answer_tab = QWidget()
        auto_answer_layout = QVBoxLayout(auto_answer_tab)
        auto_answer_layout.setContentsMargins(8, 10, 8, 8)
        auto_answer_layout.setSpacing(8)
        
        # 顶部数据指标卡片群 (Metric Cards)
        metric_container = QWidget()
        metric_layout = QHBoxLayout(metric_container)
        metric_layout.setContentsMargins(0, 0, 0, 0)
        metric_layout.setSpacing(8)
        
        self.card_total = MetricCard("总账号", "0", accent_color="#2563eb", bg_tint="#eff6ff")
        self.card_pending = MetricCard("待处理", "0", accent_color="#64748b", bg_tint="#f8fafc")
        self.card_running = MetricCard("答题中", "0", accent_color="#d97706", bg_tint="#fffbeb")
        self.card_completed = MetricCard("已完成", "0", accent_color="#059669", bg_tint="#ecfdf5")
        self.card_failed = MetricCard("异常失败", "0", accent_color="#dc2626", bg_tint="#fef2f2")
        
        metric_layout.addWidget(self.card_total)
        metric_layout.addWidget(self.card_pending)
        metric_layout.addWidget(self.card_running)
        metric_layout.addWidget(self.card_completed)
        metric_layout.addWidget(self.card_failed)
        auto_answer_layout.addWidget(metric_container)
        
        # 账号输入与快速添加区
        account_input_card = QFrame()
        account_input_card.setStyleSheet("""
            QFrame {
                background-color: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 8px;
                padding: 6px;
            }
        """)
        account_input_layout = QVBoxLayout(account_input_card)
        account_input_layout.setContentsMargins(8, 8, 8, 8)
        account_input_layout.setSpacing(6)
        
        input_row1 = QHBoxLayout()
        input_row1.setSpacing(6)
        
        self.account_edit = QLineEdit()
        self.account_edit.setPlaceholderText("账号（单账号或直接粘贴多行批量添加）")
        input_row1.addWidget(self.account_edit, 3)
        
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.Password)
        self.password_edit.setPlaceholderText(f"默认密码 {DEFAULT_PASSWORD}")
        input_row1.addWidget(self.password_edit, 2)
        
        add_account_btn = QPushButton("添加账号")
        add_account_btn.setObjectName("primary_btn")
        add_account_btn.clicked.connect(self.add_account)
        input_row1.addWidget(add_account_btn, 1)
        
        account_input_layout.addLayout(input_row1)
        
        # 辅助提示
        hint_label = QLabel("💡 提示：支持单账号或多行批量添加（格式可为 每行账号 或 账号:密码）")
        hint_label.setStyleSheet("font-size: 11px; color: #64748b;")
        account_input_layout.addWidget(hint_label)
        
        auto_answer_layout.addWidget(account_input_card)
        
        # 账号列表卡片
        accounts_card = QFrame()
        accounts_card.setStyleSheet("""
            QFrame {
                background-color: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 8px;
            }
        """)
        accounts_layout = QVBoxLayout(accounts_card)
        accounts_layout.setContentsMargins(8, 8, 8, 8)
        accounts_layout.setSpacing(6)
        
        table_header_layout = QHBoxLayout()
        table_title = QLabel("待处理账号列表")
        table_title.setStyleSheet("font-weight: bold; font-size: 13px; color: #1e293b;")
        table_header_layout.addWidget(table_title)
        table_header_layout.addStretch()
        
        reset_selected_btn = QPushButton("重置选中为待处理")
        reset_selected_btn.setToolTip("将选中的账号状态重置为待处理")
        reset_selected_btn.clicked.connect(self.reset_selected_accounts)
        table_header_layout.addWidget(reset_selected_btn)
        
        delete_account_btn = QPushButton("删除选中")
        delete_account_btn.setObjectName("danger_action_btn")
        delete_account_btn.clicked.connect(self.delete_account)
        table_header_layout.addWidget(delete_account_btn)
        
        accounts_layout.addLayout(table_header_layout)
        
        # 账号表格 (应用现代斑马纹、整行选中与状态彩色徽章)
        self.accounts_table = QTableWidget(0, 3)
        self.accounts_table.setHorizontalHeaderLabels(["账号", "密码", "当前状态"])
        self.accounts_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.accounts_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.accounts_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.accounts_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.accounts_table.setAlternatingRowColors(True)
        self.accounts_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.accounts_table.customContextMenuRequested.connect(self.show_account_context_menu)
        
        # 为“当前状态”列绑定现代彩色胶囊徽章代理
        self.accounts_table.setItemDelegateForColumn(2, StatusBadgeDelegate(self))
        accounts_layout.addWidget(self.accounts_table)
        
        auto_answer_layout.addWidget(accounts_card, 1)
        
        # 底部操作控制卡片
        operations_card = QFrame()
        operations_card.setStyleSheet("""
            QFrame {
                background-color: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 8px;
            }
        """)
        operations_layout = QHBoxLayout(operations_card)
        operations_layout.setContentsMargins(8, 8, 8, 8)
        operations_layout.setSpacing(10)
        
        # 兼容性复选框（保持与原无头控制兼容）
        self.show_browser_checkbox = QCheckBox()
        self.show_browser_checkbox.setChecked(True)
        self.show_browser_checkbox.setVisible(False)
        
        self.start_btn = QPushButton("开始自动答题")
        self.start_btn.setObjectName("start_btn")
        self.start_btn.clicked.connect(self.start_automation)
        operations_layout.addWidget(self.start_btn, 3)
        
        self.pause_btn = QPushButton("暂停")
        self.pause_btn.setObjectName("pause_btn")
        self.pause_btn.clicked.connect(self.pause_automation)
        self.pause_btn.setEnabled(False)
        operations_layout.addWidget(self.pause_btn, 1)
        
        self.stop_btn = QPushButton("停止")
        self.stop_btn.setObjectName("stop_btn")
        self.stop_btn.clicked.connect(self.stop_automation)
        self.stop_btn.setEnabled(False)
        operations_layout.addWidget(self.stop_btn, 1)
        
        auto_answer_layout.addWidget(operations_card)
        
        # ---------------------------------------------------------------------
        # 选项卡 2：题库管理中心
        # ---------------------------------------------------------------------
        question_db_tab = QWidget()
        question_db_layout = QVBoxLayout(question_db_tab)
        question_db_layout.setContentsMargins(8, 10, 8, 8)
        question_db_layout.setSpacing(8)
        
        # 题库导入卡片
        import_card = QFrame()
        import_card.setStyleSheet("""
            QFrame {
                background-color: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 8px;
            }
        """)
        import_card_layout = QVBoxLayout(import_card)
        import_card_layout.setContentsMargins(8, 8, 8, 8)
        import_card_layout.setSpacing(6)
        
        import_title = QLabel("题库快速导入")
        import_title.setStyleSheet("font-weight: bold; font-size: 13px; color: #1e293b;")
        import_card_layout.addWidget(import_title)
        
        self.question_text = QTextEdit()
        self.question_text.setAcceptRichText(False)
        self.question_text.setPlaceholderText(
            "粘贴题目文本，系统支持两类格式自动解析：\n"
            "格式 1（选择题）：\n"
            "1.(30分)题目内容...\nA.选项A\nB.选项B\n【正确答案：】A\n\n"
            "格式 2（简单主观题/解答题）：\n"
            "1.(40分)题目内容...\n参考解答内容..."
        )
        self.question_text.setMaximumHeight(130)
        import_card_layout.addWidget(self.question_text)
        
        import_action_row = QHBoxLayout()
        import_action_row.setSpacing(6)
        
        smart_import_btn = QPushButton("智能导入 (自动识别)")
        smart_import_btn.setObjectName("primary_btn")
        smart_import_btn.clicked.connect(self.import_questions)
        import_action_row.addWidget(smart_import_btn)
        
        subjective_import_btn = QPushButton("简单主观题导入")
        subjective_import_btn.clicked.connect(self.import_simple_subjective_questions)
        import_action_row.addWidget(subjective_import_btn)
        
        import_from_account_btn = QPushButton("从已完成账号提取")
        import_from_account_btn.setToolTip("登录其他已做完作业的账号，自动逆向提取题库与答案")
        import_from_account_btn.clicked.connect(self.import_from_completed_account)
        import_action_row.addWidget(import_from_account_btn)
        
        import_card_layout.addLayout(import_action_row)
        question_db_layout.addWidget(import_card)
        
        # 题库浏览与管理卡片
        view_card = QFrame()
        view_card.setStyleSheet("""
            QFrame {
                background-color: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 8px;
            }
        """)
        view_layout = QVBoxLayout(view_card)
        view_layout.setContentsMargins(8, 8, 8, 8)
        view_layout.setSpacing(6)
        
        view_header_layout = QHBoxLayout()
        view_title = QLabel("题库列表 (已物化索引加速)")
        view_title.setStyleSheet("font-weight: bold; font-size: 13px; color: #1e293b;")
        view_header_layout.addWidget(view_title)
        view_header_layout.addStretch()
        
        refresh_btn = QPushButton("刷新题库")
        refresh_btn.clicked.connect(self.refresh_questions)
        view_header_layout.addWidget(refresh_btn)
        
        delete_question_btn = QPushButton("删除选中题目")
        delete_question_btn.setObjectName("danger_action_btn")
        delete_question_btn.clicked.connect(self.delete_question)
        view_header_layout.addWidget(delete_question_btn)
        
        view_layout.addLayout(view_header_layout)
        
        # 题库表格
        self.questions_table = QTableWidget(0, 3)
        self.questions_table.setHorizontalHeaderLabels(["题目内容", "参考答案", "题目类型"])
        self.questions_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.questions_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.questions_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.questions_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.questions_table.setAlternatingRowColors(True)
        view_layout.addWidget(self.questions_table)
        
        question_db_layout.addWidget(view_card, 1)
        
        # ---------------------------------------------------------------------
        # 选项卡 3：环境与性能设置
        # ---------------------------------------------------------------------
        settings_tab = QWidget()
        settings_layout = QVBoxLayout(settings_tab)
        settings_layout.setContentsMargins(8, 10, 8, 8)
        settings_layout.setSpacing(10)
        
        # 浏览器内核适配卡片
        browser_card = QFrame()
        browser_card.setStyleSheet("QFrame { background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; }")
        browser_card_layout = QVBoxLayout(browser_card)
        browser_card_layout.setContentsMargins(10, 10, 10, 10)
        browser_card_layout.setSpacing(6)
        
        b_title = QLabel("浏览器内核适配 (Edge / Chrome 双引擎)")
        b_title.setStyleSheet("font-weight: bold; font-size: 13px; color: #1e293b;")
        browser_card_layout.addWidget(b_title)
        
        b_select_row = QHBoxLayout()
        b_select_row.setSpacing(8)
        b_select_row.addWidget(QLabel("首选自动化内核:"))
        
        self.browser_combo = QComboBox()
        self.browser_combo.addItem("智能自适应 (推荐，优先 Windows 自带 Edge)", "auto")
        self.browser_combo.addItem("Microsoft Edge (微软自带)", "edge")
        self.browser_combo.addItem("Google Chrome (谷歌浏览器)", "chrome")
        self.browser_combo.currentIndexChanged.connect(self.on_browser_selection_changed)
        b_select_row.addWidget(self.browser_combo, 1)
        browser_card_layout.addLayout(b_select_row)
        
        self.browser_status_label = QLabel("正在检测本地可用浏览器...")
        self.browser_status_label.setStyleSheet("font-size: 11px; color: #64748b; margin-top: 2px;")
        browser_card_layout.addWidget(self.browser_status_label)
        
        settings_layout.addWidget(browser_card)
        
        # 多线程并发配置卡片（修复了此前缺失初始化的崩溃隐患）
        multithread_card = QFrame()
        multithread_card.setStyleSheet("QFrame { background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; }")
        multithread_card_layout = QVBoxLayout(multithread_card)
        multithread_card_layout.setContentsMargins(10, 10, 10, 10)
        multithread_card_layout.setSpacing(6)
        
        mt_title = QLabel("多线程并发加速")
        mt_title.setStyleSheet("font-weight: bold; font-size: 13px; color: #1e293b;")
        multithread_card_layout.addWidget(mt_title)
        
        mt_row = QHBoxLayout()
        self.multithread_checkbox = QCheckBox("启用多线程并发模式")
        self.multithread_checkbox.setToolTip("启用后将同时拉起多个独立浏览器会话并行作答不同账号")
        self.multithread_checkbox.stateChanged.connect(self.on_multithread_changed)
        mt_row.addWidget(self.multithread_checkbox)
        
        mt_row.addSpacing(20)
        mt_row.addWidget(QLabel("线程数量:"))
        self.thread_count_spinbox = QSpinBox()
        self.thread_count_spinbox.setMinimum(1)
        self.thread_count_spinbox.setMaximum(32)
        self.thread_count_spinbox.setEnabled(False)
        
        # 根据硬件 CPU 核心智能设定建议并发数
        try:
            from cpu_optimization import get_cpu_optimizer
            cpu_optimizer = get_cpu_optimizer()
            optimal_threads = cpu_optimizer.get_optimal_thread_count()
            cpu_info = cpu_optimizer.get_cpu_info()
            self.thread_count_spinbox.setValue(optimal_threads)
            self.thread_count_spinbox.setToolTip(
                f"CPU 信息: {cpu_info['physical_cores']} 物理核心, {cpu_info['logical_cores']} 逻辑核心\n"
                f"建议并发数: {optimal_threads}"
            )
            help_desc = f"CPU: {cpu_info['physical_cores']} 物理核心/{cpu_info['logical_cores']} 逻辑核心，已启用 CPU 亲和度调度"
        except Exception:
            self.thread_count_spinbox.setValue(2)
            help_desc = "提示：多线程模式会同时开启多个浏览器窗口，请结合电脑性能调整并发数"
            
        mt_row.addWidget(self.thread_count_spinbox)
        mt_row.addStretch()
        multithread_card_layout.addLayout(mt_row)
        
        mt_desc = QLabel(help_desc)
        mt_desc.setStyleSheet("font-size: 11px; color: #64748b;")
        multithread_card_layout.addWidget(mt_desc)
        
        settings_layout.addWidget(multithread_card)
        
        # 操作延迟控制卡片
        delay_card = QFrame()
        delay_card.setStyleSheet("QFrame { background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; }")
        delay_card_layout = QVBoxLayout(delay_card)
        delay_card_layout.setContentsMargins(10, 10, 10, 10)
        delay_card_layout.setSpacing(6)
        
        d_title = QLabel("操作与网络延迟控制")
        d_title.setStyleSheet("font-weight: bold; font-size: 13px; color: #1e293b;")
        delay_card_layout.addWidget(d_title)
        
        self.delay_value_label = QLabel(f"当前延迟: {OPERATION_DELAY['default']:.2f} 秒")
        self.delay_value_label.setStyleSheet("font-size: 12px; color: #2563eb; font-weight: 500;")
        delay_card_layout.addWidget(self.delay_value_label)
        
        self.delay_slider = QSlider(Qt.Horizontal)
        self.delay_slider.setMinimum(int(OPERATION_DELAY['min'] * 100))
        self.delay_slider.setMaximum(int(OPERATION_DELAY['max'] * 100))
        self.delay_slider.setValue(int(OPERATION_DELAY['default'] * 100))
        self.delay_slider.setToolTip(f"调节操作间延迟时间 ({OPERATION_DELAY['min']}s - {OPERATION_DELAY['max']}s)")
        self.delay_slider.valueChanged.connect(self.on_delay_changed)
        delay_card_layout.addWidget(self.delay_slider)
        
        range_row = QHBoxLayout()
        range_row.addWidget(QLabel(f"{OPERATION_DELAY['min']}s (极速)"))
        range_row.addStretch()
        range_row.addWidget(QLabel(f"{OPERATION_DELAY['max']}s (平稳)"))
        delay_card_layout.addLayout(range_row)
        
        settings_layout.addWidget(delay_card)
        
        # 硬件与系统监控组件
        sys_card = QFrame()
        sys_card.setStyleSheet("QFrame { background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; }")
        sys_card_layout = QVBoxLayout(sys_card)
        sys_card_layout.setContentsMargins(10, 10, 10, 10)
        
        self.resource_widget = ResourceWidget()
        sys_card_layout.addWidget(self.resource_widget)
        settings_layout.addWidget(sys_card)
        
        settings_layout.addStretch()
        
        # 装填三大选项卡
        self.tab_widget.addTab(auto_answer_tab, "自动答题工作台")
        self.tab_widget.addTab(question_db_tab, "题库管理中心")
        self.tab_widget.addTab(settings_tab, "运行环境与设置")
        left_layout.addWidget(self.tab_widget)
        
        self.main_splitter.addWidget(left_panel)
        
        # =====================================================================
        # 右侧面板：现代化全功能日志控制台
        # =====================================================================
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(4, 0, 0, 0)
        right_layout.setSpacing(6)
        
        self.log_console = LogConsoleWidget()
        right_layout.addWidget(self.log_console)
        
        self.main_splitter.addWidget(right_panel)
        
        # 设置左右响应式初始分割比例 5:5
        self.main_splitter.setStretchFactor(0, 1)
        self.main_splitter.setStretchFactor(1, 1)
        self.main_splitter.setSizes([520, 520])
        
        overall_layout.addWidget(self.main_splitter, 1)
        
        # =====================================================================
        # 底部现代扁平化进度条
        # =====================================================================
        self.status_bar = QProgressBar()
        self.status_bar.setFixedHeight(24)
        self.status_bar.setTextVisible(True)
        self.status_bar.setFormat("系统就绪")
        overall_layout.addWidget(self.status_bar)
        
        # 进度平滑动画计时器
        self.progress_animation_timer = QTimer()
        self.progress_animation_timer.timeout.connect(self.animate_progress)
        self.target_progress = 0
        self.current_progress = 0
        self.progress_step = 1
        
        # 错误闪烁状态
        self.error_flash_timer = None
        self.flash_count = 0
        
        # 启动自检与初始化
        self.refresh_questions()
        self.check_environment()
        self.clean_log_files(silent=True)
        self.update_metric_cards()

    # =====================================================================
    # 数据指标统计与联动
    # =====================================================================
    def update_metric_cards(self):
        """实时统计并更新顶部指标卡片数值"""
        total = len(self.accounts)
        pending = 0
        running = 0
        completed = 0
        failed = 0
        
        for acc in self.accounts:
            st = acc.get("status", "待处理")
            if "已完成" in st or "成功" in st:
                completed += 1
            elif "进行" in st or "答题" in st or "登录" in st or "处理中" in st:
                running += 1
            elif "失败" in st or "错误" in st or "异常" in st:
                failed += 1
            else:
                pending += 1
                
        self.card_total.set_value(total)
        self.card_pending.set_value(pending)
        self.card_running.set_value(running)
        self.card_completed.set_value(completed)
        self.card_failed.set_value(failed)

    def show_account_context_menu(self, pos: QPoint):
        """表格右键快捷菜单"""
        selected_rows = self.accounts_table.selectionModel().selectedRows()
        menu = QMenu(self)
        
        if selected_rows:
            reset_action = QAction("🔄 重置为待处理", self)
            reset_action.triggered.connect(self.reset_selected_accounts)
            menu.addAction(reset_action)
            
            delete_action = QAction("🗑️ 删除选中账号", self)
            delete_action.triggered.connect(self.delete_account)
            menu.addAction(delete_action)
            
            menu.addSeparator()
            
        clear_all_action = QAction("🧹 清空全部账号", self)
        clear_all_action.triggered.connect(self.clear_all_accounts)
        menu.addAction(clear_all_action)
        
        menu.exec_(self.accounts_table.viewport().mapToGlobal(pos))

    def reset_selected_accounts(self):
        """重置选中账号为待处理"""
        selected_rows = self.accounts_table.selectionModel().selectedRows()
        if not selected_rows:
            self.update_status_bar("请先选择要重置的账号！", is_error=True)
            return
        for row in selected_rows:
            idx = row.row()
            self.update_account_status(idx, "待处理")
        self.log(f"已重置 {len(selected_rows)} 个账号状态为待处理")
        self.update_metric_cards()

    def clear_all_accounts(self):
        """清空所有账号"""
        if not self.accounts:
            return
        reply = QMessageBox.question(self, "确认清空", "确定要清空账号列表中的所有账号吗？",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.accounts.clear()
            self.accounts_table.setRowCount(0)
            self.update_metric_cards()
            self.log("已清空账号列表")

    # =====================================================================
    # 状态栏与进度动画
    # =====================================================================
    def update_status_bar(self, message, progress=None, is_error=False):
        """更新底部状态栏信息与进度"""
        self.status_bar.setFormat(message)
        if progress is not None:
            self.target_progress = progress
            if not self.progress_animation_timer.isActive():
                self.progress_animation_timer.start(20)
        
        if is_error:
            self.start_error_flash()
        else:
            self.stop_error_flash()
            
    def update_progress(self, progress, description):
        """更新自动化运行进度"""
        self.update_status_bar(description, progress=progress)

    def animate_progress(self):
        """平滑更新进度条显示"""
        if self.current_progress < self.target_progress:
            dist = self.target_progress - self.current_progress
            self.progress_step = max(1, dist // 10)
            self.current_progress = min(self.current_progress + self.progress_step, self.target_progress)
        elif self.current_progress > self.target_progress:
            dist = self.current_progress - self.target_progress
            self.progress_step = max(1, dist // 10)
            self.current_progress = max(self.current_progress - self.progress_step, self.target_progress)
            
        self.status_bar.setValue(self.current_progress)
        if self.current_progress == self.target_progress:
            self.progress_animation_timer.stop()

    def start_error_flash(self):
        if self.error_flash_timer:
            self.error_flash_timer.stop()
        self.error_flash_timer = QTimer()
        self.error_flash_timer.timeout.connect(self.flash_error)
        self.flash_count = 0
        self.error_flash_timer.start(300)

    def stop_error_flash(self):
        if self.error_flash_timer:
            self.error_flash_timer.stop()
            self.error_flash_timer = None
        self.status_bar.setStyleSheet("")

    def flash_error(self):
        self.flash_count += 1
        if self.flash_count % 2 == 0:
            self.status_bar.setStyleSheet("""
                QProgressBar {
                    border: 1px solid #f87171;
                    background-color: #fef2f2;
                    color: #b91c1c;
                }
                QProgressBar::chunk {
                    background-color: #ef4444;
                }
            """)
        else:
            self.status_bar.setStyleSheet("")
            
        if self.flash_count >= 12:
            self.stop_error_flash()

    # =====================================================================
    # 账号管理业务逻辑
    # =====================================================================
    def add_account(self):
        account = self.account_edit.text().strip()
        password = self.password_edit.text().strip()
        
        if not account:
            self.update_status_bar("请输入账号！", is_error=True)
            return
            
        # 多行账号检测
        if re.search(r'[\r\n]', account):
            self.log("检测到多行账号文本，开始批量解析添加...")
            self.process_multiple_accounts(account)
            self.account_edit.clear()
            return
            
        if not password:
            password = DEFAULT_PASSWORD
            
        if not account.isdigit():
            self.update_status_bar(f"账号格式无效: {account} (只能包含数字)", is_error=True)
            return
            
        for existing in self.accounts:
            if existing["username"] == account:
                self.update_status_bar(f"账号已存在: {account}", is_error=True)
                return
                
        row_pos = self.accounts_table.rowCount()
        self.accounts_table.insertRow(row_pos)
        self.accounts_table.setItem(row_pos, 0, QTableWidgetItem(account))
        self.accounts_table.setItem(row_pos, 1, QTableWidgetItem("*" * len(password)))
        self.accounts_table.setItem(row_pos, 2, QTableWidgetItem("待处理"))
        
        self.accounts.append({"username": account, "password": password, "status": "待处理"})
        self.account_edit.clear()
        self.password_edit.clear()
        self.log(f"已添加账号: {account}")
        self.update_metric_cards()

    def process_multiple_accounts(self, text):
        lines = re.split(r'[\r\n]+', text.strip())
        added_count = 0
        self.log(f"开始批量导入账号，共检测到 {len(lines)} 行")
        
        for i, line in enumerate(lines, 1):
            line = line.strip()
            if not line:
                continue
            if ':' in line:
                parts = line.split(':', 1)
                acc = parts[0].strip()
                pwd = parts[1].strip()
            else:
                acc = line
                pwd = DEFAULT_PASSWORD
                
            if not acc.isdigit():
                self.log(f"跳过非纯数字账号: {acc}", color="orange")
                continue
                
            if any(existing["username"] == acc for existing in self.accounts):
                continue
                
            row_pos = self.accounts_table.rowCount()
            self.accounts_table.insertRow(row_pos)
            self.accounts_table.setItem(row_pos, 0, QTableWidgetItem(acc))
            self.accounts_table.setItem(row_pos, 1, QTableWidgetItem("*" * len(pwd)))
            self.accounts_table.setItem(row_pos, 2, QTableWidgetItem("待处理"))
            
            self.accounts.append({"username": acc, "password": pwd, "status": "待处理"})
            added_count += 1
            
        self.log(f"批量导入完成，成功新增 {added_count} 个有效账号", color="green")
        self.update_metric_cards()

    def delete_account(self):
        selected_rows = self.accounts_table.selectionModel().selectedRows()
        if not selected_rows:
            self.update_status_bar("请先选择要删除的账号！", is_error=True)
            return
            
        for row in sorted(selected_rows, reverse=True):
            index = row.row()
            acc = self.accounts[index]["username"]
            self.accounts_table.removeRow(index)
            self.accounts.pop(index)
            self.log(f"已删除账号: {acc}")
            
        self.update_metric_cards()

    def update_account_status(self, account_index, status):
        if 0 <= account_index < self.accounts_table.rowCount():
            self.accounts_table.setItem(account_index, 2, QTableWidgetItem(status))
            self.accounts[account_index]["status"] = status
            self.update_metric_cards()

    # =====================================================================
    # 设置与偏好控制
    # =====================================================================
    def on_delay_changed(self, value):
        delay_seconds = value / 100.0
        self.delay_value_label.setText(f"当前延迟: {delay_seconds:.2f} 秒")
        self.delay_multiplier = delay_seconds / OPERATION_DELAY['default']
        if hasattr(self, 'browser_automation') and self.browser_automation:
            self.browser_automation.set_operation_delay(delay_seconds)

    def get_current_delay(self):
        return self.delay_slider.value() / 100.0

    def on_browser_selection_changed(self, index):
        selected_type = self.get_selected_browser()
        self.log(f"已切换浏览器引擎偏好: {selected_type.upper()}")
        if hasattr(self, 'multi_thread_manager') and self.multi_thread_manager:
            self.multi_thread_manager.set_browser_type(selected_type)

    def get_selected_browser(self):
        if hasattr(self, 'browser_combo'):
            return self.browser_combo.currentData() or "auto"
        return "auto"

    def log(self, message, color=None):
        """向现代化日志控制台写入日志"""
        if hasattr(self, 'log_console'):
            self.log_console.log(message, color=color)
        self.auto_clean_log_files()

    def clear_log(self):
        if hasattr(self, 'log_console'):
            self.log_console.clear_logs()

    # =====================================================================
    # 题库管理业务逻辑
    # =====================================================================
    def import_questions(self):
        text = self.question_text.toPlainText().strip()
        if not text:
            self.update_status_bar("请先输入题目文本！", is_error=True)
            return
            
        importer = QuestionImporter(self.question_db)
        try:
            result = importer.import_from_text(text)
            if result["success"]:
                self.update_status_bar(f"成功导入 {result['imported_count']} 个题目！")
                self.log(f"智能导入成功：共导入 {result['imported_count']} 个题目", color="green")
                self.question_text.clear()
                self.refresh_questions()
            else:
                self.update_status_bar(result["message"], is_error=True)
                self.log(f"智能导入失败: {result['message']}", color="red")
        except Exception as e:
            self.update_status_bar(f"导入发生错误: {str(e)}", is_error=True)
            self.log(f"智能导入错误: {str(e)}", color="red")

    def import_simple_subjective_questions(self):
        text = self.question_text.toPlainText().strip()
        if not text:
            self.update_status_bar("请先输入题目文本！", is_error=True)
            return
            
        importer = QuestionImporter(self.question_db)
        try:
            result = importer.import_simple_subjective_from_text(text)
            if result["success"]:
                self.update_status_bar(f"成功导入 {result['imported_count']} 个简单主观题！")
                self.log(f"主观题导入成功：共导入 {result['imported_count']} 个题目", color="green")
                self.question_text.clear()
                self.refresh_questions()
            else:
                self.update_status_bar(result["message"], is_error=True)
                self.log(f"主观题导入失败: {result['message']}", color="red")
        except Exception as e:
            self.update_status_bar(f"导入发生错误: {str(e)}", is_error=True)
            self.log(f"主观题导入错误: {str(e)}", color="red")

    def import_from_completed_account(self):
        from PyQt5.QtWidgets import QDialog
        dialog = QDialog(self)
        dialog.setWindowTitle("从已完成账号提取题库")
        dialog.setFixedSize(400, 200)
        dialog.setModal(True)
        
        layout = QVBoxLayout(dialog)
        layout.setSpacing(10)
        
        info_label = QLabel("请输入已完成作业的账号信息，系统将自动登录并提取全套题目与答案：")
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        acc_row = QHBoxLayout()
        acc_row.addWidget(QLabel("账号:"))
        account_input = QLineEdit()
        account_input.setPlaceholderText("输入账号")
        acc_row.addWidget(account_input)
        layout.addLayout(acc_row)
        
        pwd_row = QHBoxLayout()
        pwd_row.addWidget(QLabel("密码:"))
        password_input = QLineEdit()
        password_input.setEchoMode(QLineEdit.Password)
        password_input.setPlaceholderText(f"留空使用默认密码({DEFAULT_PASSWORD})")
        pwd_row.addWidget(password_input)
        layout.addLayout(pwd_row)
        
        btn_row = QHBoxLayout()
        start_btn = QPushButton("开始提取")
        start_btn.setObjectName("primary_btn")
        cancel_btn = QPushButton("取消")
        btn_row.addStretch()
        btn_row.addWidget(start_btn)
        btn_row.addWidget(cancel_btn)
        layout.addLayout(btn_row)
        
        cancel_btn.clicked.connect(dialog.reject)
        
        def start_import():
            account = account_input.text().strip()
            password = password_input.text().strip() or DEFAULT_PASSWORD
            if not account:
                self.update_status_bar("请输入账号！", is_error=True)
                return
            dialog.accept()
            self.update_status_bar("正在从已完成账号提取题库...", progress=0)
            self.start_question_import_thread(account, password)
            
        start_btn.clicked.connect(start_import)
        dialog.exec_()

    def start_question_import_thread(self, account, password):
        from PyQt5.QtCore import QThread, pyqtSignal
        
        class QuestionImportThread(QThread):
            log_signal = pyqtSignal(str)
            finished_signal = pyqtSignal(bool, str, int)
            progress_signal = pyqtSignal(int, str)
            
            def __init__(self, account, password, question_db, delay_multiplier=1.0, browser_type=None):
                super().__init__()
                self.account = account
                self.password = password
                self.question_db = question_db
                self.delay_multiplier = delay_multiplier
                self.browser_type = browser_type
                
            def run(self):
                try:
                    from automation import QuestionBankImporter
                    importer = QuestionBankImporter(self.question_db, show_browser=True, browser_type=self.browser_type)
                    importer.log_signal.connect(self.log_signal.emit)
                    importer.progress_signal.connect(self.progress_signal.emit)
                    importer.set_delay_multiplier(self.delay_multiplier)
                    
                    result = importer.import_from_completed_account(self.account, self.password)
                    if result["success"]:
                        self.finished_signal.emit(True, f"成功导入 {result['imported_count']} 个题目！", result['imported_count'])
                    else:
                        self.finished_signal.emit(False, result["message"], 0)
                except Exception as e:
                    self.finished_signal.emit(False, f"提取过程中发生错误: {str(e)}", 0)

        self.import_thread = QuestionImportThread(account, password, self.question_db, self.delay_multiplier, self.get_selected_browser())
        self.import_thread.log_signal.connect(self.log)
        self.import_thread.progress_signal.connect(lambda pct, desc: self.update_status_bar(desc, progress=pct))
        
        def on_import_finished(success, message, count):
            if success:
                self.update_status_bar(f"题库提取成功！共导入 {count} 个题目", progress=100)
                self.refresh_questions()
                QMessageBox.information(self, "提取成功", message)
            else:
                self.update_status_bar(f"题库提取失败: {message}", is_error=True)
                QMessageBox.warning(self, "提取失败", message)
                
        self.import_thread.finished_signal.connect(on_import_finished)
        self.import_thread.start()

    def refresh_questions(self):
        questions = self.question_db.get_all_questions()
        self.questions_table.setRowCount(0)
        
        for q in questions:
            row_pos = self.questions_table.rowCount()
            self.questions_table.insertRow(row_pos)
            
            content = q[1]
            if len(content) > 55:
                content = content[:52] + "..."
            self.questions_table.setItem(row_pos, 0, QTableWidgetItem(content))
            
            ans = q[2]
            if len(ans) > 35:
                ans = ans[:32] + "..."
            self.questions_table.setItem(row_pos, 1, QTableWidgetItem(ans))
            
            q_type = "选择题" if q[3] == "choice" else "主观题"
            self.questions_table.setItem(row_pos, 2, QTableWidgetItem(q_type))
            self.questions_table.item(row_pos, 0).setData(Qt.UserRole, q[0])
            
        self.log(f"已刷新题库，当前已物化缓存题目数: {len(questions)}")

    def delete_question(self):
        selected_rows = self.questions_table.selectionModel().selectedRows()
        if not selected_rows:
            self.update_status_bar("请先选择要删除的题目！", is_error=True)
            return
            
        reply = QMessageBox.question(self, "确认删除", f"确定要删除选中的 {len(selected_rows)} 个题目吗？",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply != QMessageBox.Yes:
            return
            
        deleted_count = 0
        for row in sorted(selected_rows, reverse=True):
            idx = row.row()
            qid = self.questions_table.item(idx, 0).data(Qt.UserRole)
            try:
                self.question_db.delete_question(qid)
                deleted_count += 1
            except Exception as e:
                self.log(f"删除题目 ID:{qid} 失败: {str(e)}", color="red")
                
        self.refresh_questions()
        self.log(f"已成功删除 {deleted_count} 个题目", color="green")

    # =====================================================================
    # 环境检查与日志文件自动清理
    # =====================================================================
    def check_environment(self):
        import platform
        self.log("正在进行自动化运行环境探测...")
        os_info = platform.system() + " " + platform.release()
        self.log(f"✓ 操作系统: {os_info}")
        
        detected = detect_available_browsers()
        edge_info = detected.get("edge", {})
        chrome_info = detected.get("chrome", {})
        
        found = False
        parts = []
        if edge_info.get("available"):
            found = True
            v = f" (v{edge_info['version']})" if edge_info.get('version') else ""
            self.log(f"✓ Microsoft Edge 已就绪: {edge_info.get('path') or '系统默认'}{v}", color="green")
            parts.append("Edge ✓")
            
        if chrome_info.get("available"):
            found = True
            v = f" (v{chrome_info['version']})" if chrome_info.get('version') else ""
            self.log(f"✓ Google Chrome 已就绪: {chrome_info.get('path') or '系统默认'}{v}", color="green")
            parts.append("Chrome ✓")
            
        if found:
            self.log(f"✓ 双引擎驱动探测完成，支持内核: {' / '.join(parts)}", color="green")
            if hasattr(self, 'browser_status_label'):
                self.browser_status_label.setText(f"环境就绪: {' | '.join(parts)}")
                self.browser_status_label.setStyleSheet("font-size: 11px; color: #059669; font-weight: bold;")
        else:
            self.log("✗ 系统未检测到 Edge 或 Chrome 浏览器！", color="red")
            if hasattr(self, 'browser_status_label'):
                self.browser_status_label.setText("未检测到可用浏览器，请安装 Edge 或 Chrome")
                self.browser_status_label.setStyleSheet("font-size: 11px; color: #dc2626; font-weight: bold;")

    def auto_clean_log_files(self):
        import os
        now = time.time()
        if hasattr(self, '_last_auto_clean_check') and now - self._last_auto_clean_check < 60:
            return
        self._last_auto_clean_check = now
        for log_file in ['app_error.log', 'dist/app_error.log']:
            if os.path.exists(log_file):
                try:
                    if os.path.getsize(log_file) > 300 * 1024:
                        with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                            lines = f.readlines()
                        if len(lines) > 500:
                            with open(log_file, 'w', encoding='utf-8') as f:
                                f.write("=== 日志已自动轮转归档，保留最新 500 行 ===\n")
                                f.writelines(lines[-500:])
                except Exception:
                    pass

    def clean_log_files(self, silent=False):
        import os
        log_files = ['app_error.log', 'dist/app_error.log']
        for log_file in log_files:
            if os.path.exists(log_file) and os.path.getsize(log_file) > 5 * 1024 * 1024:
                try:
                    with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                        lines = f.readlines()
                    if len(lines) > 1000:
                        with open(log_file, 'w', encoding='utf-8') as f:
                            f.write("=== 超大日志已清理，保留最新 1000 行 ===\n")
                            f.writelines(lines[-1000:])
                except Exception as e:
                    if not silent:
                        self.log(f"清理日志出错: {str(e)}", color="orange")

    # =====================================================================
    # 自动化调度与执行
    # =====================================================================
    def setup_multithread_signals(self):
        self.multi_thread_manager.log_signal.connect(self.log)
        self.multi_thread_manager.status_signal.connect(self.update_account_status)
        self.multi_thread_manager.progress_signal.connect(self.update_progress)
        self.multi_thread_manager.all_finished_signal.connect(self.on_automation_finished)

    def on_multithread_changed(self, state):
        self.is_multithread_mode = (state == Qt.Checked)
        self.thread_count_spinbox.setEnabled(self.is_multithread_mode)
        if self.is_multithread_mode:
            self.log(f"已启用多线程并发模式 (设定线程数: {self.thread_count_spinbox.value()})", color="blue")
        else:
            self.log("已切换为单线程串行模式")

    def start_automation(self):
        if not self.accounts:
            self.log("请先添加待答题账号！", color="orange")
            self.update_status_bar("账号列表为空，请先添加账号", is_error=True)
            return
            
        if self.is_multithread_mode:
            self.start_multithread_automation()
        else:
            self.start_singlethread_automation()

    def start_singlethread_automation(self):
        if self.browser_automation and self.browser_automation.isRunning():
            self.log("自动化答题已在运行中...")
            return
            
        browser = self.get_selected_browser()
        self.browser_automation = BrowserAutomation(self.accounts, self.question_db, browser_type=browser)
        self.browser_automation.set_operation_delay(self.delay_multiplier * OPERATION_DELAY['default'])
        
        self.browser_automation.log_signal.connect(self.log)
        self.browser_automation.status_signal.connect(self.update_account_status)
        self.browser_automation.progress_signal.connect(self.update_progress)
        self.browser_automation.finished.connect(self.on_automation_finished)
        
        self.browser_automation.start()
        
        self.start_btn.setEnabled(False)
        self.pause_btn.setEnabled(True)
        self.stop_btn.setEnabled(True)
        self.pause_btn.setText("暂停")
        
        self.log(f"启动单线程自动答题 (驱动引擎: {browser.upper()})，共 {len(self.accounts)} 个账号", color="green")
        self.update_status_bar(f"正在答题 - 共 {len(self.accounts)} 个账号", progress=0)

    def start_multithread_automation(self):
        if self.multi_thread_manager.running:
            self.log("多线程自动化答题已在运行中...")
            return
            
        thread_count = self.thread_count_spinbox.value()
        browser = self.get_selected_browser()
        
        self.multi_thread_manager.set_thread_count(thread_count)
        self.multi_thread_manager.set_delay_multiplier(self.delay_multiplier)
        self.multi_thread_manager.set_browser_type(browser)
        
        self.multi_thread_manager.start_automation(self.accounts)
        
        self.start_btn.setEnabled(False)
        self.pause_btn.setEnabled(True)
        self.stop_btn.setEnabled(True)
        self.pause_btn.setText("暂停")
        
        self.log(f"启动多线程并发答题 (并发数: {thread_count}, 引擎: {browser.upper()})", color="green")

    def pause_automation(self):
        if self.is_multithread_mode:
            if self.multi_thread_manager.paused:
                self.multi_thread_manager.resume_automation()
                self.pause_btn.setText("暂停")
                self.log("已恢复多线程答题")
                self.update_status_bar("多线程答题已恢复")
            else:
                self.multi_thread_manager.pause_automation()
                self.pause_btn.setText("恢复")
                self.log("已暂停多线程答题", color="orange")
                self.update_status_bar("多线程答题已暂停")
        else:
            if self.browser_automation and self.browser_automation.isRunning():
                if self.browser_automation.paused:
                    self.browser_automation.paused = False
                    self.pause_btn.setText("暂停")
                    self.log("已恢复自动答题")
                    self.update_status_bar("自动答题已恢复")
                else:
                    self.browser_automation.paused = True
                    self.pause_btn.setText("恢复")
                    self.log("已暂停自动答题", color="orange")
                    self.update_status_bar("自动答题已暂停")

    def stop_automation(self):
        reply = QMessageBox.question(self, "确认停止", "确定要停止当前的自动答题任务吗？",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply != QMessageBox.Yes:
            return
            
        self.stop_btn.setEnabled(False)
        self.start_btn.setEnabled(False)
        self.pause_btn.setEnabled(False)
        
        self.log("正在平稳停止答题并回收浏览器资源...", color="orange")
        self.update_status_bar("正在停止自动答题...")
        
        try:
            from cleanup_manager import get_cleanup_manager
            cleanup_manager = get_cleanup_manager()
            cleanup_manager.log_signal.connect(self.log)
            cleanup_manager.cleanup_finished.connect(self.on_stop_cleanup_finished)
            
            if self.is_multithread_mode:
                workers = self.multi_thread_manager.workers if hasattr(self.multi_thread_manager, 'workers') else []
                drivers = []
                for w in workers:
                    if hasattr(w, 'automation') and w.automation and hasattr(w.automation, 'driver'):
                        drivers.append(w.automation.driver)
                self.multi_thread_manager.running = False
                cleanup_manager.immediate_cleanup(drivers=drivers, workers=workers)
            else:
                drivers = []
                if self.browser_automation and hasattr(self.browser_automation, 'driver'):
                    drivers.append(self.browser_automation.driver)
                if self.browser_automation and self.browser_automation.isRunning():
                    self.browser_automation.running = False
                cleanup_manager.immediate_cleanup(drivers=drivers)
        except Exception as e:
            self.log(f"停止清理过程异常: {str(e)}", color="red")
            self.on_stop_cleanup_finished()

    def on_stop_cleanup_finished(self):
        if self.is_multithread_mode and hasattr(self, 'multi_thread_manager'):
            self.multi_thread_manager.workers = []
            
        self.start_btn.setEnabled(True)
        self.pause_btn.setEnabled(False)
        self.stop_btn.setEnabled(False)
        self.pause_btn.setText("暂停")
        
        self.log("自动答题已彻底停止，系统就绪", color="blue")
        self.update_status_bar("自动答题已停止")
        self.update_metric_cards()

    def on_automation_finished(self):
        self.start_btn.setEnabled(True)
        self.pause_btn.setEnabled(False)
        self.stop_btn.setEnabled(False)
        self.pause_btn.setText("暂停")
        
        mode_str = "多线程" if self.is_multithread_mode else "单线程"
        self.log(f"🎉 {mode_str}自动答题任务已全部完成！", color="green")
        self.update_status_bar(f"{mode_str}自动答题已完成", progress=100)
        self.update_metric_cards()
        
        try:
            import winsound
            winsound.MessageBeep(winsound.MB_OK)
        except Exception:
            pass
            
        QMessageBox.information(self, "任务完成", "所有账号的自动答题任务已全部完成！")

    def show_about_dialog(self):
        """弹出关于对话框，展示大号Logo、软件版本与核心特性"""
        dlg = AboutDialog(self)
        dlg.exec_()

    def show_help_guide(self):
        """弹出使用指南对话框"""
        dlg = HelpGuideDialog(self)
        dlg.exec_()


    def closeEvent(self, event):
        """窗口关闭保护与资源回收"""
        is_running = (
            (hasattr(self, 'multi_thread_manager') and self.multi_thread_manager.running) or
            (hasattr(self, 'browser_automation') and self.browser_automation and self.browser_automation.isRunning())
        )
        if is_running:
            reply = QMessageBox.question(
                self, "确认退出", 
                "程序当前正在执行答题任务，确定要退出吗？\n退出时将安全回收浏览器驱动资源。",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                event.ignore()
                return
                
        if hasattr(self, 'resource_widget'):
            self.resource_widget.stop_monitoring()
            
        try:
            from cleanup_manager import get_cleanup_manager
            cleanup_manager = get_cleanup_manager()
            cleanup_manager.cleanup_browser_processes_fast(browser_type=self.get_selected_browser())
        except Exception as e:
            print(f"安全退出时清理异常: {str(e)}")
            
        event.accept()
