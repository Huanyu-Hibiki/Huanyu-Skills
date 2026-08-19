"""auto-collect core/browser — Profile 管理 + 授权检查 + 导航重试。

合规：只在用户本机运行；首次授权必须可见浏览器（headless=False）；不绕过任何平台安全机制。
"""

import time
from pathlib import Path

from playwright.sync_api import sync_playwright, Browser, Page, TimeoutError as PWTimeout

PROFILE_ROOT = Path.home() / "oracle-bone-profiles"

NAV_RETRIES = 3
NAV_RETRY_DELAYS = [3, 8]


def profile_dir(platform: str) -> Path:
    d = PROFILE_ROOT / platform
    d.mkdir(parents=True, exist_ok=True)
    return d


class BrowserSession:
    """每平台一个持久 Profile 的浏览器会话。

    反风控设计（不绕过，只求像正常浏览器）：
    - 优先 channel='chrome'（本机真 Chrome 指纹；无 chrome 自动回退 chromium）
    - 专用 profile 空间不带任何自动化标记 cookie——被平台标记污染时可一键重置
    """

    def __init__(self, platform: str, headless: bool = False, slow_mo: int = 0,
                 fresh: bool = False):
        self.platform = platform
        self.headless = headless
        self.slow_mo = slow_mo
        self.fresh = fresh
        self._pw = None
        self._browser = None
        self._context = None

    def __enter__(self):
        if self.fresh:
            # fresh=True：忽略/重置持久 Profile（被平台风控污染后的"换新身份"）
            import shutil
            d = profile_dir(self.platform)
            marker = d / "oracle-bone.txt"
            if marker.exists():  # 只重置我们自己建的目录，防误删
                shutil.rmtree(d, ignore_errors=True)
                d.mkdir(parents=True, exist_ok=True)
        self._pw = sync_playwright().start()
        launch = dict(headless=self.headless, slow_mo=self.slow_mo)
        try:
            self._context = self._pw.chromium.launch_persistent_context(
                str(profile_dir(self.platform)), channel="chrome", **launch)
        except Exception:
            self._context = self._pw.chromium.launch_persistent_context(
                str(profile_dir(self.platform)), **launch)
        (profile_dir(self.platform) / "oracle-bone.txt").write_text(
            f"oracle-bone profile for {self.platform}", encoding="utf-8")
        return self

    def __exit__(self, *exc):
        try:
            if self._context:
                self._context.close()
        finally:
            if self._pw:
                self._pw.stop()

    @property
    def page(self) -> Page:
        if not self._context.pages:
            return self._context.new_page()
        return self._context.pages[0]

    def navigate(self, url: str, timeout_ms: int = 60000) -> Page:
        page = self.page
        last_err = None
        for attempt in range(1, NAV_RETRIES + 1):
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
                page.wait_for_timeout(1500)
                return page
            except PWTimeout as e:
                last_err = e
            except Exception as e:
                msg = str(e).lower()
                if any(k in msg for k in ("net::err", "aborted", "reset")) and attempt < NAV_RETRIES:
                    last_err = e
                else:
                    raise
            if attempt < NAV_RETRIES:
                time.sleep(NAV_RETRY_DELAYS[min(attempt - 1, len(NAV_RETRY_DELAYS) - 1)])
        raise RuntimeError(f"导航失败（{NAV_RETRIES} 次）：{url} — {last_err}")

    def auth_status(self, auth_markers: dict) -> str:
        """授权态保守检查：返回 authorized / unauthorized / unknown。

        auth_markers: {"login_hint": [选择器/文本...], "ok_hint": [文本...]}
        任何不确定情况都返回 unknown——绝不因一次探测失败要求重授权。
        """
        page = self.page
        body = ""
        try:
            body = page.inner_text("body", timeout=8000)
        except Exception:
            return "unknown"
        for hint in auth_markers.get("login_hint", []):
            if hint in body:
                return "unauthorized"
        for hint in auth_markers.get("ok_hint", []):
            if hint in body:
                return "authorized"
        return "unknown"

    def screenshot_debug(self, out_path: Path):
        out_path.parent.mkdir(parents=True, exist_ok=True)
        self.page.screenshot(path=str(out_path), full_page=False)
