"""
HTTP 请求工具模块

封装 HTTP 请求操作，提供统一的请求接口和错误处理。
"""

import json
import urllib.request
import ssl
import time
import os
from typing import Optional, Dict, Any, List
from .logger import get_logger

logger = get_logger(__name__)

DEFAULT_TIMEOUT = 30
DEFAULT_RETRY_DELAY = 0.5
DEFAULT_USER_AGENT = 'WeLink-Reporter/1.0'
GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN', '')


class HttpClient:
    """
    HTTP 客户端类
    
    提供 GET 请求方法，支持 SSL 配置和错误处理。
    
    Attributes:
        ssl_context: SSL 上下文配置
        timeout: 请求超时时间
        user_agent: User-Agent 头
        retry_delay: 重试延迟时间
    
    Example:
        client = HttpClient()
        data = client.get("https://api.github.com/repos/owner/repo/issues")
    """
    
    def __init__(
        self,
        timeout: int = DEFAULT_TIMEOUT,
        user_agent: str = DEFAULT_USER_AGENT,
        retry_delay: float = DEFAULT_RETRY_DELAY,
        verify_ssl: bool = False
    ):
        """
        初始化 HTTP 客户端
        
        Args:
            timeout: 请求超时时间（秒）
            user_agent: User-Agent 头
            retry_delay: 重试延迟时间（秒）
            verify_ssl: 是否验证 SSL证书
        """
        self.timeout = timeout
        self.user_agent = user_agent
        self.retry_delay = retry_delay
        
        self.ssl_context = ssl.create_default_context()
        if not verify_ssl:
            self.ssl_context.check_hostname = False
            self.ssl_context.verify_mode = ssl.CERT_NONE
    
    def get(self, url: str) -> Optional[List[Dict[str, Any]]]:
        """
        发送 GET 请求并返回 JSON 数据
        
        Args:
            url: 请求 URL
        
        Returns:
            解析后的 JSON 数据，失败时返回空列表
        
        Note:
            请求失败时会打印错误日志，不会抛出异常
        """
        try:
            logger.debug(f"Requesting: {url}")
            headers = {'User-Agent': self.user_agent}
            
            if 'github.com' in url and GITHUB_TOKEN:
                headers['Authorization'] = f'token {GITHUB_TOKEN}'
            
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(
                req,
                context=self.ssl_context,
                timeout=self.timeout
            ) as response:
                data = json.loads(response.read().decode('utf-8'))
                logger.debug(f"Successfully fetched data from {url}")
                return data
        except urllib.error.HTTPError as e:
            logger.error(f"HTTP Error {e.code}: {e.reason} - {url}")
            return []
        except urllib.error.URLError as e:
            logger.error(f"URL Error: {e.reason} - {url}")
            return []
        except json.JSONDecodeError as e:
            logger.error(f"JSON Decode Error: {e} - {url}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error fetching {url}: {e}")
            return []
    
    def get_with_delay(self, url: str, delay: float = None) -> Optional[List[Dict[str, Any]]]:
        """
        发送 GET 请求并添加延迟（用于避免 API 限流）
        
        Args:
            url: 请求 URL
            delay: 延迟时间，默认使用 retry_delay
        
        Returns:
            解析后的 JSON 数据
        """
        if delay is None:
            delay = self.retry_delay
        
        result = self.get(url)
        time.sleep(delay)
        return result