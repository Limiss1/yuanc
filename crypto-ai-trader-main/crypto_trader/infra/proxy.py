import logging
import os
import sys
import urllib.request
from typing import Optional

logger = logging.getLogger(__name__)


def detect_system_proxy() -> Optional[str]:
    if os.environ.get('HTTP_PROXY') or os.environ.get('HTTPS_PROXY'):
        proxy = os.environ.get('HTTPS_PROXY') or os.environ.get('HTTP_PROXY')
        if proxy:
            logger.info(f"[PROXY] Using proxy from environment: {proxy}")
            return proxy

    if os.environ.get('http_proxy') or os.environ.get('https_proxy'):
        proxy = os.environ.get('https_proxy') or os.environ.get('http_proxy')
        if proxy:
            logger.info(f"[PROXY] Using proxy from environment: {proxy}")
            return proxy

    if sys.platform == 'win32':
        try:
            proxy_handler = urllib.request.ProxyHandler()
            proxy_dict = proxy_handler.proxies
            if proxy_dict:
                for key in ['https', 'http']:
                    proxy_url = proxy_dict.get(key, '')
                    if proxy_url and proxy_url not in ('', 'None'):
                        logger.info(f"[PROXY] Using system proxy ({key}): {proxy_url}")
                        return proxy_url
        except Exception:
            pass

        try:
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Internet Settings",
                0, winreg.KEY_READ
            )
            try:
                proxy_enable, _ = winreg.QueryValueEx(key, "ProxyEnable")
                if proxy_enable:
                    proxy_server, _ = winreg.QueryValueEx(key, "ProxyServer")
                    if proxy_server:
                        if not proxy_server.startswith('http'):
                            proxy_server = f'http://{proxy_server}'
                        logger.info(f"[PROXY] Using IE/system proxy: {proxy_server}")
                        return proxy_server
            finally:
                winreg.CloseKey(key)
        except Exception:
            pass

    logger.info("[PROXY] No system proxy detected, using direct connection")
    return None
