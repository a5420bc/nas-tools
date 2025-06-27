import json
import os
import time
from typing import Dict, List, TypedDict

from app.utils.commons import singleton
from app.utils.http_utils import RequestUtils
import log


class LoginResponse(TypedDict):
    code: int
    success: bool
    data: Dict[str, str]


class CloudLink(TypedDict):
    cloudType: int
    link: str


class CloudResource(TypedDict):
    messageId: str
    title: str
    content: str
    cloudLinks: List[CloudLink]


class SearchResponse(TypedDict):
    code: int
    success: bool
    data: List[Dict[str, List[CloudResource]]]


# 网盘类型映射
CLOUD_TYPE_MAP = {
    1: "tianyi",
    2: "quark",
    # 3: "aliyun",
    # 4: "百度网盘",
    # 5: "迅雷网盘",
    # 可以根据实际情况添加更多类型
}

# 网盘域名映射
CLOUD_DOMAIN_MAP = {
    1: "cloud.189.cn",      # 天翼云盘
    2: "pan.quark.cn",      # 夸克网盘
    # 3: "aliyundrive.com",   # 阿里云盘
    # 4: "pan.baidu.com",     # 百度网盘
    # 5: "pan.xunlei.com",    # 迅雷网盘
}


@singleton
class CloudSaverSDK:
    """CloudSaver SDK Python版本"""

    def __init__(self, config=None):
        # 使用config.py中的环境变量获取配置目录，并使用专用的token文件名
        config_dir = os.environ.get('NASTOOL_CONFIG')
        if config_dir:
            config_dir = os.path.dirname(config_dir)
        else:
            config_dir = os.getcwd()
        self._token_path = os.path.join(config_dir, 'cloudsaver_token.json')
        self._token = self._load_token()
        self._max_retries = 3
        self._retry_delay = 1.0  # 1秒
        self._config = config or {}

        # 豆瓣热门内容类型映射
        self._douban_types = {
            'hot_movie': {'type': '全部', 'category': '热门', 'api': 'movie', 'limit': 50},
            'new_movie': {'type': '全部', 'category': '最新', 'api': 'movie', 'limit': 50},
            'unpopular_movie': {'type': '全部', 'category': '冷门佳片', 'api': 'movie', 'limit': 50},
            'hot_tv': {'type': 'tv', 'category': 'tv', 'api': 'tv', 'limit': 50},
            'hot_animation': {'type': 'tv_animation', 'category': 'tv', 'api': 'tv', 'limit': 50},
            'hot_show': {'type': 'show', 'category': 'show', 'api': 'tv', 'limit': 50}
        }

    def update_config(self, config):
        """更新配置"""
        self._config = config

    @property
    def _base_url(self) -> str:
        """获取CloudSaver基础URL"""
        return self._config.get('base_url', '')

    @property
    def _username(self) -> str:
        """获取CloudSaver用户名"""
        return self._config.get('username', '')

    @property
    def _password(self) -> str:
        """获取CloudSaver密码"""
        return self._config.get('password', '')

    @property
    def _enabled_cloud_types(self) -> List[int]:
        """获取启用的网盘类型列表"""
        return self._config.get('enabled_cloud_types', [1])  # 默认只启用天翼云盘

    @property
    def enabled(self) -> bool:
        """检查是否已启用"""
        return bool(self._base_url and self._username and self._password)

    def login(self) -> bool:
        """登录CloudSaver"""
        if not self._base_url or not self._username or not self._password:
            log.error('您还未配置 CloudSaver 请先配置后使用')
            raise Exception('您还未配置 CloudSaver 请先配置后使用')

        try:
            # 使用RequestUtils发送POST请求
            request_utils = RequestUtils(
                content_type='application/json',
                timeout=3
            )

            login_data = {
                'username': self._username,
                'password': self._password
            }

            response = request_utils.post_res(
                url=f"{self._base_url}/api/user/login",
                json=login_data
            )

            if not response:
                log.error('登录请求失败')
                return False

            if response.status_code != 200:
                log.error(f'登录失败，状态码: {response.status_code}')
                return False

            try:
                data = response.json()
            except json.JSONDecodeError:
                log.error('登录响应解析失败')
                return False

            if data.get('success') and data.get('code') == 0:
                token = data.get('data', {}).get('token')
                if token:
                    self._token = token
                    self._save_token()
                    log.info('CloudSaver 登录成功')
                    return True

            log.error(f'登录失败: {data}')
            return False

        except Exception as error:
            log.error(f'登录失败: {error}')
            return False

    def _load_token(self) -> str:
        """加载保存的token"""
        try:
            if os.path.exists(self._token_path):
                with open(self._token_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data.get('token', '')
        except Exception as error:
            log.error(f'加载 token 失败: {error}')
        return ''

    def _save_token(self) -> None:
        """保存token到文件"""
        try:
            token_dir = os.path.dirname(self._token_path)
            if not os.path.exists(token_dir):
                os.makedirs(token_dir, exist_ok=True)

            with open(self._token_path, 'w', encoding='utf-8') as f:
                json.dump({'token': self._token}, f,
                          ensure_ascii=False, indent=2)

        except Exception as error:
            log.error(f'保存 token 失败: {error}')

    def _delay(self, seconds: float) -> None:
        """延迟等待"""
        time.sleep(seconds)

    def _auto_login(self) -> bool:
        """自动登录"""
        if not self._username or not self._password:
            raise Exception('CloudSaverSDK 未启用')

        retries = 0
        while retries < self._max_retries:
            success = self.login()
            if success:
                return True

            retries += 1
            if retries < self._max_retries:
                log.info(f'CloudSaverSDK 自动登录失败，第 {retries} 次重试...')
                self._delay(self._retry_delay)

        return False

    def search(self, keyword: str, cloud_types: List[int] = None) -> List[CloudResource]:
        """搜索云盘资源

        Args:
            keyword: 搜索关键词
            cloud_types: 指定搜索的网盘类型列表，如果为None则使用配置中的类型
        """
        if not self._token:
            login_success = self._auto_login()
            if not login_success:
                raise Exception('CloudSaverSDK 自动登录失败，请检查账号密码是否正确')

        # 使用传入的类型或配置中的类型
        target_cloud_types = cloud_types or self._enabled_cloud_types
        enabled_cloud_names = [CLOUD_TYPE_MAP.get(
            ct, f"未知类型{ct}") for ct in target_cloud_types]

        try:
            log.debug(
                f'CloudSaverSDK 开始搜索: {keyword}，支持网盘类型: {enabled_cloud_names}')

            # 使用RequestUtils发送GET请求
            request_utils = RequestUtils(
                headers={
                    'Authorization': f'Bearer {self._token}'
                },
                timeout=30
            )

            response = request_utils.get_res(
                url=f"{self._base_url}/api/search",
                params={'keyword': keyword},
                raise_exception=False
            )


            # 记录响应状态
            log.debug(f"API 响应状态码: {response.status_code}")
            if not response:
                raise Exception('搜索请求失败')

            # 处理401未授权的情况
            if int(response.status_code) == 401:  # 强制转换为整数进行比较
                log.info('token 已过期，尝试自动登录...')
                login_success = self._auto_login()
                if not login_success:
                    raise Exception('token 已过期，自动登录失败')
                # 重新发起请求
                return self.search(keyword, cloud_types)

            if response.status_code != 200:
                raise Exception(f'搜索失败，状态码: {response.status_code}')

            try:
                data = response.json()
                log.debug("API 响应解析成功")
            except json.JSONDecodeError:
                raise Exception('搜索响应解析失败')

            if data.get('success') and data.get('code') == 0:
                # 提取资源列表
                resources = []
                for item in data.get('data', []):
                    resources.extend(item.get('list', []))

                # 根据cloudType和域名过滤资源
                filtered_resources = []
                for resource in resources:
                    cloud_links = resource.get('cloudLinks', [])
                    log.debug(f"处理资源: {resource.get('title', '未知标题')}, 链接数: {len(cloud_links)}")
                    if cloud_links:
                        # 检查是否有符合条件的链接
                        valid_links = []
                        for link in cloud_links:
                            cloud_type = link.get('cloudType')
                            link_url = link.get('link', '')

                            log.debug(f"资源链接网盘类型为: {cloud_type}")

                            # 检查cloudType是否在启用列表中
                            if cloud_type in enabled_cloud_names:
                                valid_links.append(link)
                            # 如果cloudType不存在，通过域名判断
                            elif not cloud_type:
                                for ct in enabled_cloud_names:
                                    domain = CLOUD_DOMAIN_MAP.get(ct, '')
                                    if domain and domain in link_url:
                                        link['cloudType'] = ct  # 补充cloudType
                                        valid_links.append(link)
                                        break

                        if valid_links:
                            resource_copy = resource.copy()
                            resource_copy['cloudLinks'] = valid_links
                            filtered_resources.append(resource_copy)

                # 按资源去重
                unique_resources = {}
                for resource in filtered_resources:
                    message_id = resource.get('messageId')
                    if message_id and message_id not in unique_resources:
                        unique_resources[message_id] = resource

                # 将每个资源的多个链接拆分为独立资源
                result = []
                for resource in unique_resources.values():
                    for cloud_link in resource.get('cloudLinks', []):
                        cloud_type = cloud_link.get('cloudType')

                        result.append({
                            'messageId': resource.get('messageId', ''),
                            'title': resource.get('title', ''),
                            'content': resource.get('content', ''),
                            'cloudType': cloud_type,
                            'cloudLinks': [cloud_link]
                        })

                # 最后按链接去重
                unique_links = {}
                for resource in result:
                    if resource['cloudLinks']:
                        link = resource['cloudLinks'][0].get('link', '')
                        if link and link not in unique_links:
                            unique_links[link] = resource

                final_result = list(unique_links.values())

                # 按网盘类型统计
                type_stats = {}
                for resource in final_result:
                    cloud_name = resource.get('cloudType', '未知')
                    type_stats[cloud_name] = type_stats.get(cloud_name, 0) + 1

                log.info(
                    f'CloudSaverSDK 搜索完成，找到 {len(final_result)} 个资源，分布: {type_stats}')
                
                # 记录找到的资源标题
                if final_result:
                    titles = [res.get('title', '未知标题') for res in final_result[:5]]
                    if len(final_result) > 5:
                        titles.append(f"...等共{len(final_result)}个资源")
                    log.debug(f"找到的资源: {', '.join(titles)}")
                return final_result

            return []

        except Exception as error:
            log.error(f'搜索失败: {error}')
            raise error

    def get_token(self) -> str:
        """获取当前token"""
        return self._token

    def set_token(self, token: str) -> None:
        """设置token"""
        self._token = token
        self._save_token()