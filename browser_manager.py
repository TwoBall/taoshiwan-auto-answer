# -*- coding: utf-8 -*-
"""
浏览器驱动统一适配与管理模块 (Browser Manager)
支持 Microsoft Edge 和 Google Chrome 双引擎智能自适应与无缝切换
"""

import os
import sys
import subprocess
import platform
import glob
import io
import zipfile
import urllib.request
import ssl
import json
from typing import Dict, Any, List, Set, Tuple, Optional, Callable

try:
    import psutil
except ImportError:
    psutil = None


# 浏览器进程关键字
BROWSER_PROCESS_NAMES = {
    "edge": ["msedge.exe", "msedgedriver.exe"],
    "chrome": ["chrome.exe", "chromedriver.exe"]
}


def _get_registry_app_path(app_name: str) -> Optional[str]:
    """从 Windows 注册表获取指定程序的安装路径"""
    if platform.system() != "Windows":
        return None
    try:
        import winreg
        key_path = rf"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\{app_name}"
        for hkey in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
            try:
                with winreg.OpenKey(hkey, key_path) as reg_key:
                    path, _ = winreg.QueryValueEx(reg_key, "")
                    if path and os.path.exists(path):
                        return path
            except OSError:
                continue
    except Exception:
        pass
    return None


def _get_executable_version(exec_path: str) -> Optional[str]:
    """通过 Windows API 原生读取可执行文件版本，极速且避免编码解码冲突"""
    if not exec_path or not os.path.exists(exec_path):
        return None

    if platform.system() == "Windows":
        try:
            import ctypes
            from ctypes import wintypes

            size = ctypes.windll.version.GetFileVersionInfoSizeW(exec_path, None)
            if size:
                res = ctypes.create_string_buffer(size)
                if ctypes.windll.version.GetFileVersionInfoW(exec_path, 0, size, res):
                    lpt = ctypes.c_void_p()
                    u_len = ctypes.c_uint()
                    if ctypes.windll.version.VerQueryValueW(res, r'\\', ctypes.byref(lpt), ctypes.byref(u_len)):
                        class VS_FIXEDFILEINFO(ctypes.Structure):
                            _fields_ = [
                                ('dwSignature', wintypes.DWORD),
                                ('dwStrucVersion', wintypes.DWORD),
                                ('dwFileVersionMS', wintypes.DWORD),
                                ('dwFileVersionLS', wintypes.DWORD),
                                ('dwProductVersionMS', wintypes.DWORD),
                                ('dwProductVersionLS', wintypes.DWORD),
                                ('dwFileFlagsMask', wintypes.DWORD),
                                ('dwFileFlags', wintypes.DWORD),
                                ('dwFileOS', wintypes.DWORD),
                                ('dwFileType', wintypes.DWORD),
                                ('dwFileSubtype', wintypes.DWORD),
                                ('dwFileDateMS', wintypes.DWORD),
                                ('dwFileDateLS', wintypes.DWORD)
                            ]
                        info = VS_FIXEDFILEINFO.from_address(lpt.value)
                        return f"{info.dwProductVersionMS >> 16}.{info.dwProductVersionMS & 0xffff}.{info.dwProductVersionLS >> 16}.{info.dwProductVersionLS & 0xffff}"
        except Exception:
            pass

    # 兜底：通过命令行带明确编码与容错处理
    try:
        result = subprocess.run([exec_path, "--version"], capture_output=True, text=True, errors='replace', timeout=3)
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except Exception:
        pass

    return None


def detect_available_browsers() -> Dict[str, Dict[str, Any]]:
    """
    检测系统当前可用的 Edge 与 Chrome 浏览器
    返回检测结果字典，包含是否可用、路径、版本等
    """
    results = {
        "edge": {"available": False, "path": None, "version": None, "name": "Microsoft Edge"},
        "chrome": {"available": False, "path": None, "version": None, "name": "Google Chrome"}
    }

    # 1. 检测 Microsoft Edge
    edge_paths = [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        os.path.expanduser(r"~\AppData\Local\Microsoft\Edge\Application\msedge.exe")
    ]
    # 注册表补全
    reg_edge = _get_registry_app_path("msedge.exe")
    if reg_edge and reg_edge not in edge_paths:
        edge_paths.insert(0, reg_edge)

    for p in edge_paths:
        if os.path.exists(p):
            results["edge"]["available"] = True
            results["edge"]["path"] = p
            results["edge"]["version"] = _get_executable_version(p)
            break

    # 尝试通过环境变量 msedge 检查
    if not results["edge"]["available"]:
        try:
            res = subprocess.run(["msedge", "--version"], capture_output=True, text=True, timeout=3)
            if res.returncode == 0:
                results["edge"]["available"] = True
                results["edge"]["version"] = res.stdout.strip()
        except Exception:
            pass

    # 2. 检测 Google Chrome
    chrome_paths = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expanduser(r"~\AppData\Local\Google\Chrome\Application\chrome.exe")
    ]
    reg_chrome = _get_registry_app_path("chrome.exe")
    if reg_chrome and reg_chrome not in chrome_paths:
        chrome_paths.insert(0, reg_chrome)

    for p in chrome_paths:
        if os.path.exists(p):
            results["chrome"]["available"] = True
            results["chrome"]["path"] = p
            results["chrome"]["version"] = _get_executable_version(p)
            break

    if not results["chrome"]["available"]:
        try:
            res = subprocess.run(["chrome", "--version"], capture_output=True, text=True, timeout=3)
            if res.returncode == 0:
                results["chrome"]["available"] = True
                results["chrome"]["version"] = res.stdout.strip()
        except Exception:
            pass

    return results


def resolve_browser_type(preference: str = "auto") -> str:
    """
    根据用户偏好与本地安装情况决断最终使用的浏览器类型
    :param preference: 'auto' | 'edge' | 'chrome'
    :return: 'edge' | 'chrome'
    """
    detected = detect_available_browsers()
    edge_ok = detected["edge"]["available"]
    chrome_ok = detected["chrome"]["available"]

    pref = preference.lower().strip() if preference else "auto"

    if pref == "edge":
        if edge_ok:
            return "edge"
        if chrome_ok:
            return "chrome"  # 降级容错
        return "edge"

    if pref == "chrome":
        if chrome_ok:
            return "chrome"
        if edge_ok:
            return "edge"  # 降级容错
        return "chrome"

    # auto 模式：在 Windows 下优先使用系统标配的 Edge，若无则使用 Chrome
    if edge_ok:
        return "edge"
    if chrome_ok:
        return "chrome"

    # 若都未能明确在路径中检测到，默认采用 edge（Windows 默认自带）
    return "edge"


def track_browser_processes(target_browser: Optional[str] = None) -> Set[int]:
    """
    跟踪当前已存在的相关浏览器进程 PID
    :param target_browser: 'edge' | 'chrome' | None (None 表示同时跟踪两种)
    """
    if not psutil:
        return set()

    target_keywords = []
    if target_browser:
        target_keywords = BROWSER_PROCESS_NAMES.get(target_browser.lower(), [])
    else:
        target_keywords = BROWSER_PROCESS_NAMES["edge"] + BROWSER_PROCESS_NAMES["chrome"]

    target_keywords = [k.lower() for k in target_keywords]

    existing_pids = set()
    try:
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                name = proc.info.get('name')
                if name and any(k in name.lower() for k in target_keywords):
                    existing_pids.add(proc.info['pid'])
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
    except Exception:
        pass

    return existing_pids


def kill_specific_processes(pids: List[int], log_callback: Optional[Callable[[str], None]] = None):
    """
    精确终止指定 PID 列表的进程，不影响用户日常浏览器的其他窗口
    """
    if not psutil or not pids:
        return

    for pid in pids[:]:
        try:
            proc = psutil.Process(pid)
            if proc.is_running():
                proc.kill()
                if log_callback:
                    log_callback(f"已精准关闭自动化关联进程 PID: {pid}")
        except (psutil.NoSuchProcess, psutil.AccessDenied, ValueError):
            pass
        except Exception as e:
            if log_callback:
                log_callback(f"关闭进程 PID {pid} 出错: {str(e)}")


def _ensure_no_proxy_for_webdriver():
    """
    确保 localhost 和 127.0.0.1 在 no_proxy 豁免名单中，
    防止本地系统代理劫持 Python 对本地 WebDriver 服务的 HTTP 控制请求
    """
    for key in ("no_proxy", "NO_PROXY"):
        current = os.environ.get(key, "")
        items = set(filter(None, [x.strip() for x in current.split(",")]))
        items.update(["localhost", "127.0.0.1", "::1"])
        os.environ[key] = ",".join(items)


def _find_or_download_edgedriver(edge_version: Optional[str] = None, log_fn: Optional[Callable[[str], None]] = None) -> Optional[str]:
    """
    智能查找或从国内高速开源镜像（npmmirror 阿里云镜像）下载匹配的 EdgeDriver
    彻底规避微软海外 Azure 服务器连接失败（tls handshake eof）缺陷
    """
    def _log(m):
        if log_fn:
            log_fn(m)

    # 1. 优先检查常规本地缓存路径
    cache_base = os.path.expanduser("~/.cache/selenium/msedgedriver")
    if os.path.exists(cache_base):
        matches = glob.glob(os.path.join(cache_base, "**", "msedgedriver.exe"), recursive=True)
        if matches:
            if edge_version:
                major = edge_version.split(".")[0]
                for p in matches:
                    if edge_version in p or major in p:
                        return p
            return matches[0]

    # 检查程序同级或驱动目录
    local_candidates = [
        "msedgedriver.exe",
        os.path.join("drivers", "msedgedriver.exe"),
        os.path.join(os.path.dirname(sys.executable) if hasattr(sys, '_MEIPASS') else ".", "msedgedriver.exe")
    ]
    for cand in local_candidates:
        if os.path.exists(cand):
            return os.path.abspath(cand)

    # 2. 如果未找到本地驱动，但探测到了本地 Edge 版本，尝试国内阿里云镜像源自动下载
    if edge_version and platform.system() == "Windows":
        try:
            target_dir = os.path.join(cache_base, "win64", edge_version)
            target_exe = os.path.join(target_dir, "msedgedriver.exe")
            if os.path.exists(target_exe):
                return target_exe

            major_str = edge_version.split(".")[0]
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE

            # 自动查询镜像源上同一大版本的可用版本列表，进行最佳对齐
            matched_version = edge_version
            try:
                meta_url = "https://registry.npmmirror.com/-/binary/edgedriver/"
                req_meta = urllib.request.Request(meta_url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req_meta, timeout=5, context=ctx) as r:
                    data = json.loads(r.read().decode("utf-8"))
                    avail = [x["name"].strip("/") for x in data if x.get("name", "").startswith(major_str + ".")]
                    if avail and edge_version not in avail:
                        matched_version = avail[-1]
            except Exception:
                pass

            _log(f"📥 正在从国内高速镜像源下载 EdgeDriver (版本: {matched_version})...")
            url = f"https://registry.npmmirror.com/-/binary/edgedriver/{matched_version}/edgedriver_win64.zip"
            
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
                if resp.status == 200:
                    os.makedirs(target_dir, exist_ok=True)
                    content = resp.read()
                    with zipfile.ZipFile(io.BytesIO(content)) as z:
                        z.extractall(target_dir)
                    found = glob.glob(os.path.join(target_dir, "**", "msedgedriver.exe"), recursive=True)
                    if found:
                        _log(f"✅ EdgeDriver 国内镜像下载解压成功: {found[0]}")
                        return found[0]
        except Exception as e:
            _log(f"⚠️ 国内镜像下载 EdgeDriver 提示: {str(e)}")

    return None


def _find_or_download_chromedriver(chrome_version: Optional[str] = None, log_fn: Optional[Callable[[str], None]] = None) -> Optional[str]:
    """
    智能查找或从国内高速开源镜像（npmmirror 阿里云镜像）下载匹配的 ChromeDriver
    彻底规避 Google 官方服务器在国内网络被墙/超时导致自动化无法启动的问题
    支持 Chrome 115+ (Chrome for Testing 规范) 与历史经典版本
    """
    def _log(m):
        if log_fn:
            log_fn(m)

    # 1. 优先检查常规本地缓存路径
    cache_base = os.path.expanduser("~/.cache/selenium/chromedriver")
    if os.path.exists(cache_base):
        matches = glob.glob(os.path.join(cache_base, "**", "chromedriver.exe"), recursive=True)
        if matches:
            if chrome_version:
                major = chrome_version.split(".")[0]
                for p in matches:
                    if chrome_version in p or major in p:
                        return p
            return matches[0]

    # 检查程序同级或驱动目录
    local_candidates = [
        "chromedriver.exe",
        os.path.join("drivers", "chromedriver.exe"),
        os.path.join(os.path.dirname(sys.executable) if hasattr(sys, '_MEIPASS') else ".", "chromedriver.exe")
    ]
    for cand in local_candidates:
        if os.path.exists(cand):
            return os.path.abspath(cand)

    # 2. 如果未找到本地驱动，但探测到了本地 Chrome 版本，尝试国内阿里云镜像源自动下载
    if chrome_version and platform.system() == "Windows":
        try:
            target_dir = os.path.join(cache_base, "win64", chrome_version)
            target_exe = os.path.join(target_dir, "chromedriver.exe")
            if os.path.exists(target_exe):
                return target_exe

            major_str = chrome_version.split(".")[0]
            major = int(major_str) if major_str.isdigit() else 115

            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE

            # 自动查询镜像源上同一大版本的可用版本列表，进行最佳对齐
            matched_version = chrome_version
            if major >= 115:
                try:
                    meta_url = "https://registry.npmmirror.com/-/binary/chrome-for-testing/"
                    req_meta = urllib.request.Request(meta_url, headers={"User-Agent": "Mozilla/5.0"})
                    with urllib.request.urlopen(req_meta, timeout=5, context=ctx) as r:
                        data = json.loads(r.read().decode("utf-8"))
                        avail = [x["name"].strip("/") for x in data if x.get("name", "").startswith(major_str + ".")]
                        if avail and chrome_version not in avail:
                            matched_version = avail[-1]
                except Exception:
                    pass

            _log(f"📥 正在从国内高速镜像源下载 ChromeDriver (版本: {matched_version})...")
            
            candidates = []
            if major >= 115:
                candidates.append(f"https://registry.npmmirror.com/-/binary/chrome-for-testing/{matched_version}/win64/chromedriver-win64.zip")
                candidates.append(f"https://npmmirror.com/mirrors/chrome-for-testing/{matched_version}/win64/chromedriver-win64.zip")
            else:
                candidates.append(f"https://registry.npmmirror.com/-/binary/chromedriver/{matched_version}/chromedriver_win32.zip")
                candidates.append(f"https://npmmirror.com/mirrors/chromedriver/{matched_version}/chromedriver_win32.zip")

            for url in candidates:
                try:
                    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                    with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
                        if resp.status == 200:
                            os.makedirs(target_dir, exist_ok=True)
                            content = resp.read()
                            with zipfile.ZipFile(io.BytesIO(content)) as z:
                                z.extractall(target_dir)
                            found = glob.glob(os.path.join(target_dir, "**", "chromedriver.exe"), recursive=True)
                            if found:
                                _log(f"✅ ChromeDriver 国内镜像下载解压成功: {found[0]}")
                                return found[0]
                except Exception:
                    continue
        except Exception as e:
            _log(f"⚠️ 国内镜像下载 ChromeDriver 提示: {str(e)}")

    return None


def create_webdriver(
    browser_type: str = "auto",
    options_list: Optional[List[str]] = None,
    show_browser: bool = True,
    log_callback: Optional[Callable[[str], None]] = None,
    allow_fallback: bool = True
) -> Tuple[Any, str]:
    """
    统一创建 WebDriver 实例，支持 Edge 和 Chrome，并在异常时支持自动回退
    :param browser_type: 'auto' | 'edge' | 'chrome'
    :param options_list: 命令行参数列表 (如 BROWSER_OPTIONS)
    :param show_browser: 是否显示窗口
    :param log_callback: 日志输出函数
    :param allow_fallback: 发生失败时是否尝试使用备选浏览器
    :return: (driver, actual_browser_type)
    """
    from selenium import webdriver

    # 优先打通本地 WebDriver 代理穿透白名单
    _ensure_no_proxy_for_webdriver()

    def _log(msg: str):
        if log_callback:
            log_callback(msg)
        else:
            print(msg)

    detected_browsers = detect_available_browsers()
    chosen_type = resolve_browser_type(browser_type)
    _log(f"🌐 正在准备启动浏览器驱动 (目标: {chosen_type.upper()})...")

    # 尝试启动指定类型的浏览器
    def _instantiate(b_type: str):
        if b_type == "edge":
            from selenium.webdriver.edge.options import Options as EdgeOptions
            from selenium.webdriver.edge.service import Service as EdgeService

            edge_options = EdgeOptions()
            edge_options.use_chromium = True
            if options_list:
                for opt in options_list:
                    edge_options.add_argument(opt)

            # 防止 Edge 与系统后台日常运行的 Edge 冲突
            edge_options.add_argument("--disable-features=msEdgeStartupBoost")
            edge_options.add_argument("--no-first-run")
            edge_options.add_argument("--no-default-browser-check")

            if not show_browser:
                edge_options.add_argument("--headless=new")
                _log("Edge 运行在无头模式")
            else:
                _log("Edge 窗口将显示，便于监控与调试")

            # 屏蔽无用日志和自动化提示黄条
            edge_options.add_experimental_option('excludeSwitches', ['enable-logging', 'enable-automation'])
            edge_options.add_experimental_option('useAutomationExtension', False)

            # 优先查找或通过国内镜像拉取本地驱动
            edge_ver = detected_browsers.get("edge", {}).get("version")
            driver_path = _find_or_download_edgedriver(edge_ver, _log)

            if driver_path and os.path.exists(driver_path):
                _log(f"使用本地 EdgeDriver: {driver_path}")
                service = EdgeService(executable_path=driver_path)
                driver = webdriver.Edge(options=edge_options, service=service)
            else:
                try:
                    service = EdgeService()
                    driver = webdriver.Edge(options=edge_options, service=service)
                except Exception:
                    driver = webdriver.Edge(options=edge_options)
            return driver

        elif b_type == "chrome":
            from selenium.webdriver.chrome.options import Options as ChromeOptions
            from selenium.webdriver.chrome.service import Service as ChromeService

            chrome_options = ChromeOptions()
            if options_list:
                for opt in options_list:
                    chrome_options.add_argument(opt)

            chrome_options.add_argument("--no-first-run")
            chrome_options.add_argument("--no-default-browser-check")

            if not show_browser:
                chrome_options.add_argument("--headless=new")
                _log("Chrome 运行在无头模式")
            else:
                _log("Chrome 窗口将显示，便于监控与调试")

            chrome_options.add_experimental_option('excludeSwitches', ['enable-logging', 'enable-automation'])
            chrome_options.add_experimental_option('useAutomationExtension', False)

            # 优先查找或通过国内镜像拉取本地驱动
            chrome_ver = detected_browsers.get("chrome", {}).get("version")
            driver_path = _find_or_download_chromedriver(chrome_ver, _log)

            if driver_path and os.path.exists(driver_path):
                _log(f"使用本地 ChromeDriver: {driver_path}")
                service = ChromeService(executable_path=driver_path)
                driver = webdriver.Chrome(options=chrome_options, service=service)
            else:
                try:
                    service = ChromeService()
                    driver = webdriver.Chrome(options=chrome_options, service=service)
                except Exception:
                    driver = webdriver.Chrome(options=chrome_options)
            return driver
        else:
            raise ValueError(f"不支持的浏览器类型: {b_type}")

    # 执行启动，首选失败时支持回退
    candidate_types = [chosen_type]
    if allow_fallback:
        fallback_type = "chrome" if chosen_type == "edge" else "edge"
        candidate_types.append(fallback_type)

    last_error = None
    for current_type in candidate_types:
        try:
            _log(f"🚀 尝试初始化 {current_type.upper()} WebDriver...")
            driver = _instantiate(current_type)
            _log(f"✅ {current_type.upper()} WebDriver 初始化成功！")
            return driver, current_type
        except Exception as e:
            last_error = e
            _log(f"⚠️ {current_type.upper()} 初始化失败: {str(e)}")
            if current_type != candidate_types[-1]:
                _log("🔄 正在尝试自动回退到备用浏览器...")

    raise RuntimeError(f"未能成功启动任何可用浏览器驱动。最后一次错误: {str(last_error)}")
