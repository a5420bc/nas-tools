from datetime import datetime
import json
from typing import Dict, List, Optional, TypedDict
from app.utils.http_utils import RequestUtils
from app.utils.commons import singleton
from app.plugins.modules._base import _IPluginModule
import log


class AccountInfo(TypedDict):
    id: str
    username: str
    capacity: Dict[str, Dict[str, str]]


class FavoriteFolder(TypedDict):
    id: str
    path: str


class TaskResponse(TypedDict):
    success: bool
    data: Optional[List[Dict[str, str]]]
    error: Optional[str]


@singleton
class Cloud189AutoSaveSDK(object):
    """Cloud189 Auto Save SDK Python版本"""
    
    def __init__(self, config=None):
        if not config:
            config = {}
        required_keys = ['base_url', 'api_key', 'account_id']
        missing_keys = [key for key in required_keys if key not in config]
        if missing_keys:
            log.warn(f"Cloud189AutoSaveSDK 缺少必要配置参数: {missing_keys}")
        self._config = config
        self._max_retries = 3
        self._retry_delay = 1.0  # 1秒
    
    def update_config(self, config):
        """更新配置"""
        self._config = config
    
    @property
    def _base_url(self) -> str:
        """获取服务器基础URL"""
        return self._config.get('base_url', '').rstrip('/')
    
    @property
    def _api_key(self) -> str:
        """获取API密钥"""
        return self._config.get('api_key', '')
    
    @property
    def enabled(self) -> bool:
        """检查是否已启用"""
        enabled = bool(self._base_url and self._api_key)
        log.debug(f"Cloud189AutoSaveSDK enabled check - base_url: {self._base_url}, api_key: {'*' * len(self._api_key) if self._api_key else ''}, enabled: {enabled}")
        return enabled
    
    def _get_headers(self) -> Dict[str, str]:
        """获取请求头"""
        return {
            'x-api-key': self._api_key,
            'Content-Type': 'application/json'
        }
    
    def get_accounts(self) -> List[AccountInfo]:
        """获取账号列表"""
        if not self.enabled:
            log.error('Cloud189AutoSave 未配置或未启用')
            return []
        
        try:
            request_utils = RequestUtils(
                headers=self._get_headers(),
                timeout=10
            )
            
            response = request_utils.get_res(
                url=f"{self._base_url}/api/accounts",
                raise_exception=False
            )
            
            if not response:
                log.error('获取账号列表请求失败')
                return []
            
            if response.status_code != 200:
                log.error(f'获取账号列表失败，状态码: {response.status_code}')
                return []
            
            try:
                data = response.json()
                if data.get('success'):
                    return data.get('data', [])
                else:
                    log.error(f'获取账号列表失败: {data}')
                    return []
            except json.JSONDecodeError:
                log.error('账号列表响应解析失败')
                return []
                
        except Exception as error:
            log.error(f'获取账号列表失败: {error}')
            return []
    
    def get_favorites(self, account_id: str) -> List[FavoriteFolder]:
        """获取常用目录"""
        if not self.enabled:
            log.error('Cloud189AutoSave 未配置或未启用')
            return []
        
        try:
            request_utils = RequestUtils(
                headers=self._get_headers(),
                timeout=10
            )
            
            response = request_utils.get_res(
                url=f"{self._base_url}/api/favorites/{account_id}",
                raise_exception=False
            )
            
            if not response:
                log.error('获取常用目录请求失败')
                return []
            
            if response.status_code != 200:
                log.error(f'获取常用目录失败，状态码: {response.status_code}')
                return []
            
            try:
                data = response.json()
                if data.get('success'):
                    return data.get('data', [])
                else:
                    log.error(f'获取常用目录失败: {data}')
                    return []
            except json.JSONDecodeError:
                log.error('常用目录响应解析失败')
                return []
                
        except Exception as error:
            log.error(f'获取常用目录失败: {error}')
            return []
    
    def create_task(self, account_id: str, share_link: str, target_folder_id: str = None,
                   target_folder: str = None, overwrite_folder: bool = False, task_name: str = None) -> TaskResponse:
        """创建任务
        :param account_id: 账号ID
        :param share_link: 分享链接
        :param target_folder_id: 目标文件夹ID
        :param target_folder: 目标文件夹路径
        :param overwrite_folder: 是否覆盖已存在目录
        :param task_name: 任务名称(可选)
        """
        if not self.enabled:
            log.error('Cloud189AutoSave 未配置或未启用')
            return {'success': False, 'data': None, 'error': '未配置'}
        
        try:
            request_utils = RequestUtils(
                headers=self._get_headers(),
                timeout=30
            )
            
            task_data = {
                'accountId': account_id,
                'shareLink': share_link,
                'taskName': task_name or f"CloudSaver_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            }
            
            if target_folder_id:
                task_data['targetFolderId'] = target_folder_id
            if target_folder:
                task_data['targetFolder'] = target_folder
            if overwrite_folder:
                task_data['overwriteFolder'] = 1
            
            # 打印请求数据(脱敏处理)
            log.debug(
                "创建任务请求数据: \n"
                f"accountId: '{account_id[:3]}...'\n"
                f"shareLink: '{share_link[:20]}...'\n"
                f"taskName: '{task_data['taskName']}'\n"
                f"targetFolder: '{target_folder}'\n"
                f"targetFolderId: '{target_folder_id}'\n"
                f"overwriteFolder: {overwrite_folder}"
            )
            
            response = request_utils.post_res(
                url=f"{self._base_url}/api/tasks",
                json=task_data
            )
            
            if not response:
                log.error('创建任务请求失败')
                return {'success': False, 'data': None, 'error': '请求失败'}
            
            # 打印响应状态码和内容
            log.debug(f"创建任务响应: 状态码={response.status_code}, 内容={response.text[:200]}")
            
            try:
                data = response.json()
                if not data.get('success'):
                    log.error(f"创建任务失败: {data.get('error')}")
                return data
            except json.JSONDecodeError:
                log.error('创建任务响应解析失败')
                return {'success': False, 'data': None, 'error': '响应解析失败'}
                
        except Exception as error:
            log.error(f'创建任务失败: {error}')
            return {'success': False, 'data': None, 'error': str(error)}
    
    def execute_task(self, task_id: str) -> bool:
        """执行任务"""
        if not self.enabled:
            log.error('Cloud189AutoSave 未配置或未启用')
            return False
        
        try:
            request_utils = RequestUtils(
                headers=self._get_headers(),
                timeout=30
            )
            
            response = request_utils.post_res(
                url=f"{self._base_url}/api/tasks/{task_id}/execute"
            )
            
            if not response:
                log.error('执行任务请求失败')
                return False
            
            if response.status_code == 200:
                log.info(f'任务 {task_id} 执行成功')
                return True
            else:
                log.error(f'执行任务失败，状态码: {response.status_code}')
                return False
                
        except Exception as error:
            log.error(f'执行任务失败: {error}')
            return False
    
    def get_version(self) -> Dict:
        """获取版本信息"""
        if not self.enabled:
            log.error('Cloud189AutoSave 未配置或未启用')
            return {'success': False, 'error': '未配置'}
            
        try:
            request_utils = RequestUtils(
                headers=self._get_headers(),
                timeout=10
            )
            
            response = request_utils.get_res(
                url=f"{self._base_url}/api/version",
                raise_exception=False
            )
            
            if not response:
                log.error('获取版本信息请求失败')
                return {'success': False, 'error': '请求失败'}
                
            if response.status_code != 200:
                log.error(f'获取版本信息失败，状态码: {response.status_code}')
                return {'success': False, 'error': f'状态码: {response.status_code}'}
                
            try:
                return response.json()
            except json.JSONDecodeError:
                log.error('版本信息响应解析失败')
                return {'success': False, 'error': '响应解析失败'}
                
        except Exception as error:
            log.error(f'获取版本信息失败: {error}')
            return {'success': False, 'error': str(error)}

    def save_to_cloud(self, share_link: str, task_name: str = None, overwrite: bool = False) -> bool:
        """保存分享链接到云盘（完整流程）
        :param share_link: 分享链接
        :param task_name: 任务名称（可选）
        :param overwrite: 是否覆盖已存在目录
        """
        log.info(f'开始保存分享链接到云盘: {share_link} ({task_name})')
        
        # 打印调用参数
        account_id = self._config.get('account_id')
        auto_save_path = self._config.get('auto_save_path')
        log.debug(f"调用create_task参数: account_id={account_id}, share_link={share_link}, "
                f"target_folder_id={self._config.get('target_folder_id')}, "
                f"target_folder={auto_save_path}, overwrite_folder={overwrite}, "
                f"task_name={task_name}")
        
        # 1. 创建任务 (使用SDK内部配置)
        task_result = self.create_task(
            account_id=account_id,
            share_link=share_link,
            target_folder_id=self._config.get('target_folder_id'),
            target_folder=auto_save_path,
            overwrite_folder=overwrite,
            task_name=task_name
        )
        
        if not task_result.get('success'):
            error = task_result.get('error', '未知错误')
            if error == 'folder already exists':
                log.warn('目录已存在，如需覆盖请设置overwrite=True')
                return False
            else:
                log.error(f'创建任务失败: {error}')
                return False
        
        # 2. 获取任务ID
        task_data = task_result.get('data', [])
        if not task_data:
            log.error('创建任务成功但未返回任务ID')
            return False
        
        task_id = task_data[0].get('id')
        if not task_id:
            log.error('任务ID为空')
            return False
        
        log.info(f'任务创建成功，任务ID: {task_id}')
        
        # 3. 执行任务
        if self.execute_task(task_id):
            log.info('保存到云盘成功')
            return True
        else:
            log.error('执行任务失败')
            return False