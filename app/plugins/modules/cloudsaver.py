import json
from app.media.douban import DouBan
from app.plugins.modules.cloudsaverhelp.cloudsaversdk import CloudResource
from typing import Dict, List
from app.plugins.modules._base import _IPluginModule
from app.plugins.modules.cloudsaverhelp import CloudSaverSDK
from app.plugins.modules.cloudsaverhelp import MediaFilter
from app.plugins.modules.cloudsaverhelp.cloud189autosave import Cloud189AutoSaveSDK
from typing import Dict, List
from threading import Event
from datetime import datetime
from jinja2 import Template
import log

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

DOUBAN_METHOD_MAP = {
    "hot_movie": "get_douban_hot_movie",
    "new_movie": "get_douban_new_movie",
    "hot_tv": "get_douban_hot_tv",
    "hot_animation": "get_douban_hot_anime",
    "hot_show": "get_douban_hot_show",
}


class CloudSaver(_IPluginModule):
    # 插件名称
    module_name = "豆瓣云盘热门订阅插件"
    # 插件描述
    module_desc = "使用CloudSaver进行资源搜索，自动保存豆瓣热门影视到云盘。"
    # 插件图标
    module_icon = "cloud.jpg"
    # 主题色
    module_color = "#4CAF50"
    # 插件版本
    module_version = "1.0"
    # 插件作者
    module_author = "CloudSaver"
    # 作者主页
    author_url = "https://github.com/a5420bc"
    # 插件配置项ID前缀
    module_config_prefix = "cloudsaver_"
    # 加载顺序
    module_order = 20
    # 可使用的用户级别
    auth_level = 2

    # 退出事件
    _event = Event()
    # 私有属性
    _enable = False
    _base_url = ""
    _username = ""
    _password = ""
    _cloudsaver_sdk = None
    _cloud189_sdk = None
    _quark_folder_id = ""
    _quark_cookie = ""
    _tianyi_folder_id = ""
    _tianyi_username = ""
    _tianyi_account_id = ""
    _tianyi_auto_save_path = ""
    _aliyun_folder_id = ""
    _baidu_folder_id = ""
    _douban_content_types = []
    _min_douban_rating = 0.0  # 最低豆瓣评分要求

    def init_config(self, config: dict = None):
        """初始化配置"""
        self._enable = config.get("enable", False)
        self._base_url = config.get("base_url", "")
        self._username = config.get("username", "")
        self._password = config.get("password", "")

          # 获取启用的网盘类型
        enabled_cloud_types = config.get("enabled_cloud_types", [])
        if isinstance(enabled_cloud_types, list):
                self._enabled_cloud_types = [
                    int(ct) for ct in enabled_cloud_types if str(ct).isdigit()]
        else:
            self._enabled_cloud_types = [1]  # 默认只启用天翼云盘

        # 天翼云盘配置
        self._tianyi_account_id = config.get("tianyi_account_id", "")
        self._tianyi_auto_save_path = config.get("tianyi_auto_save_path", "")
        
        # 初始化天翼云盘SDK
        self._douban_content_types = config.get(
            "douban_content_types", [])
        data = config.get("douban_content_types")
        log.info(f"获取豆瓣订阅类型{data}")

        # 获取最低豆瓣评分要求
        self._min_douban_rating = float(
            config.get("min_douban_rating", 0.0))
        log.info(f"设置最低豆瓣评分要求: {self._min_douban_rating}")
        # 获取网盘配置
        self._quark_folder_id = config.get("quark_folder_id", "")
        self._quark_cookie = config.get("quark_cookie", "")
        self._tianyi_folder_id = config.get("tianyi_folder_id", "")
        self._tianyi_captcha = config.get("tianyi_captcha", "")
        self._tianyi_account_id = config.get("tianyi_account_id")
        self._tianyi_auto_save_path = config.get("tianyi_auto_save_path", "")
        self._aliyun_folder_id = config.get("aliyun_folder_id", "")
        self._baidu_folder_id = config.get("baidu_folder_id", "")

        # 初始化CloudSaver SDK
        self._cloudsaver_sdk = CloudSaverSDK(config={
            'base_url': self._base_url,
            'username': self._username,
            'password': self._password,
            'enabled_cloud_types': self._enabled_cloud_types
        })

        # 初始化天翼云盘SDK
        if self._tianyi_account_id:
            cloud189_base_url = config.get("cloud189_base_url", "")
            cloud189_api_key = config.get("cloud189_api_key", "")
            if not cloud189_base_url:
                self.warning("Cloud189 API地址未配置，天翼云盘功能将不可用")
            if not cloud189_api_key:
                self.warning("Cloud189 API密钥未配置，天翼云盘功能将不可用")
            self._cloud189_sdk = Cloud189AutoSaveSDK({
                "base_url": cloud189_base_url,
                "api_key": cloud189_api_key,
                "account_id": self._tianyi_account_id,
                "auto_save_path": self._tianyi_auto_save_path,
                "target_folder_id": self._tianyi_folder_id
            })

        self.refresh_rss()

    def get_state(self):
        """获取插件状态"""
        return self._enable and self._base_url and self._username and self._password

    @staticmethod
    def get_fields():
        """获取配置字段"""
        return [
            {
                'type': 'div',
                'content': [
                    [
                        {
                            'title': '启用CloudSaver搜索',
                            'required': "",
                            'tooltip': '开启后，可以使用CloudSaver进行云盘资源搜索',
                            'type': 'switch',
                            'id': 'enable',
                        }
                    ],
                    [
                        {
                            'title': 'CloudSaver服务器地址',
                            'required': "required",
                            'tooltip': 'CloudSaver服务器的完整地址，如：https://your-server.com',
                            'type': 'text',
                            'content': [
                                {
                                    'id': 'base_url',
                                    'placeholder': 'https://your-cloudsaver-server.com',
                                }
                            ]
                        }
                    ],
                    [
                        {
                            'title': '用户名',
                            'required': "required",
                            'tooltip': 'CloudSaver账号用户名',
                            'type': 'text',
                            'content': [
                                {
                                    'id': 'username',
                                    'placeholder': '请输入用户名',
                                }
                            ]
                        },
                        {
                            'title': '密码',
                            'required': "required",
                            'tooltip': 'CloudSaver账号密码',
                            'type': 'password',
                            'content': [
                                {
                                    'id': 'password',
                                    'placeholder': '请输入密码',
                                }
                            ]
                        },
                    ]
                ]
            },
            {
                'type': 'details',
                'summary': '网盘类型设置',
                'tooltip': '选择要搜索的网盘类型',
                'content': [
                    [
                        {
                            'id': 'enabled_cloud_types',
                            'type': 'form-selectgroup',
                            'content': {
                                '1': {
                                    'id': '1',
                                    'name': '天翼云盘',
                                },
                                '2': {
                                    'id': '2',
                                    'name': '夸克网盘',
                                },
                                '3': {
                                    'id': '3',
                                    'name': '阿里云盘',
                                },
                                '4': {
                                    'id': '4',
                                    'name': '百度网盘',
                                },
                                '5': {
                                    'id': '5',
                                    'name': '迅雷网盘',
                                }
                            }
                        }
                    ]
                ]
            },
            {
                'type': 'details',
                'summary': '豆瓣订阅配置',
                'tooltip': '选择要获取的豆瓣热门内容类型以及设置最低订阅分数',
                'content': [
                    [
                        {
                            'id': 'douban_content_types',
                            'type': 'form-selectgroup',
                                    'content':  {
                                        'hot_movie': {
                                            'id': 'hot_movie',
                                            'name': '热门电影',
                                        },
                                        'new_movie': {
                                            'id': 'new_movie',
                                            'name': '最新电影',
                                        },
                                        'hot_tv': {
                                            'id': 'hot_tv',
                                            'name': '热门电视剧',
                                        },
                                        'hot_animation': {
                                            'id': 'hot_animation',
                                            'name': '热门动画',
                                        },
                                        'hot_show': {
                                            'id': 'hot_show',
                                            'name': '热门综艺',
                                        }
                                    }
                        },
                    ],
                    [
                        {
                            'title': '最低豆瓣评分',
                            'required': "",
                            'tooltip': '只订阅评分大于等于此值的内容，设置为0表示不过滤评分。注意：评分为0或无评分的内容视为满足要求',
                            'type': 'text',
                            'content': [
                                {
                                    'id': 'min_douban_rating',
                                    'placeholder': '0.0',
                                }
                            ]
                        }
                    ]
                ]
            },
            {
                'type': 'details',
                'summary': '夸克网盘设置',
                'tooltip': '配置夸克网盘的保存文件夹ID和Cookie',
                'content': [
                    [
                        {
                            'title': '夸克网盘文件夹ID',
                            'required': "",
                            'tooltip': '夸克网盘中用于保存文件的文件夹ID，可在夸克网盘分享链接中获取',
                            'type': 'text',
                            'content': [
                                {
                                    'id': 'quark_folder_id',
                                    'placeholder': '请输入夸克网盘文件夹ID',
                                }
                            ]
                        }
                    ],
                ]
            },
            {
                'type': 'details',
                'summary': '天翼云盘设置',
                'tooltip': '配置天翼云盘的保存文件夹ID和登录信息',
                'content': [
                    [
                        {
                            'title': '天翼云盘文件夹ID',
                            'required': "",
                            'tooltip': '天翼云盘中用于保存文件的文件夹ID，可在天翼云盘分享链接中获取',
                            'type': 'text',
                            'content': [
                                {
                                    'id': 'tianyi_folder_id',
                                    'placeholder': '请输入天翼云盘文件夹ID',
                                }
                            ]
                        }
                    ],
                    [
                        {
                            'title': 'cloud189-auto-save帐号ID',
                            'required': "",
                            'tooltip': '天翼云自动转存系统帐号ID',
                            'type': 'text',
                            'content': [
                                {
                                    'id': 'tianyi_account_id',
                                    'placeholder': '请输入天翼云自动转存系统帐号ID',
                                }
                            ]
                        }
                    ],
                    [
                        {
                            'title': 'Cloud189 API地址',
                            'required': "",
                            'tooltip': 'Cloud189自动转存服务的API地址，如：https://your-cloud189-server.com',
                            'type': 'text',
                            'content': [
                                {
                                    'id': 'cloud189_base_url',
                                    'placeholder': 'https://your-cloud189-server.com',
                                }
                            ]
                        },
                        {
                            'title': 'Cloud189 API密钥',
                            'required': "required",
                            'tooltip': 'Cloud189自动转存服务的API密钥',
                            'type': 'password',
                            'content': [
                                {
                                    'id': 'cloud189_api_key',
                                    'placeholder': '请输入API密钥',
                                }
                            ]
                        },
                        {
                            'title': '自动保存路径',
                            'required': "",
                            'tooltip': '天翼云盘中自动保存的路径，初始路径为/全部文件/，后面添加自定义目录',
                            'type': 'text',
                            'content': [
                                {
                                    'id': 'tianyi_auto_save_path',
                                    'placeholder': '例如：/全部文件/电影/豆瓣热门',
                                }
                            ]
                        }
                    ]
                ]
            },
            {
                'type': 'details',
                'summary': '阿里云盘设置',
                'tooltip': '配置阿里云盘的保存文件夹ID',
                'content': [
                    [
                        {
                            'title': '阿里云盘文件夹ID',
                            'required': "",
                            'tooltip': '阿里云盘中用于保存文件的文件夹ID，可在阿里云盘分享链接中获取',
                            'type': 'text',
                            'content': [
                                {
                                    'id': 'aliyun_folder_id',
                                    'placeholder': '请输入阿里云盘文件夹ID',
                                }
                            ]
                        }
                    ]
                ]
            },
            {
                'type': 'details',
                'summary': '百度网盘设置',
                'tooltip': '配置百度网盘的保存文件夹ID',
                'content': [
                    [
                        {
                            'title': '百度网盘文件夹ID',
                            'required': "",
                            'tooltip': '百度网盘中用于保存文件的文件夹ID，可在百度网盘分享链接中获取',
                            'type': 'text',
                            'content': [
                                {
                                    'id': 'baidu_folder_id',
                                    'placeholder': '请输入百度网盘文件夹ID',
                                }
                            ]
                        }
                    ]
                ]
            },
        ]

    def get_douban_content(self, content_type: str) -> List[Dict]:
        """获取指定类型的豆瓣内容"""
        method_name = DOUBAN_METHOD_MAP.get(content_type)
        if not method_name:
            self.warn(f"未知的豆瓣内容类型: {content_type}")
            return []

        douban = DouBan()
        method = getattr(douban, method_name, None)
        if not method:
            self.warn(f"豆瓣API中不存在方法: {method_name}")
            return []

        results = method()
        self.info(f"获取豆瓣内容 {content_type} 成功，共 {len(results)} 条")
        
        # 调试信息
        print("豆瓣内容结果列表:")
        for i, res in enumerate(results):
            title = res.get('title', '无标题')
            douban_id = res.get('orgid') or res.get('id', '').replace('DB:', '')
            print(f"  {i+1}. 标题: {title}, ID: {douban_id}")

        # TODO 调试用，限制结果数量
        results = results[2:3]
        print(f"限制为只处理第一个结果: {results[0].get('title', '无标题')}")
        return results

    def filter_by_rating(self, results: List[Dict], min_rating: float) -> List[Dict]:
        """根据评分过滤豆瓣内容"""
        return [res for res in results
               if not res.get('vote') or float(res.get('vote', 0)) >= min_rating]

    def search_cloud_resources(self, douban_results: List[Dict]) -> List[CloudResource]:
        """搜索云盘资源"""
        if not self._cloudsaver_sdk or not self._cloudsaver_sdk.enabled:
            self.warn("CloudSaver SDK未初始化或未启用")
            return []

        cloud_resources = []
        for result in douban_results:
            title = result.get('title', '')
            douban_id = result.get('orgid') or result.get('id', '').replace('DB:', '')
            
            if not title or not douban_id:
                self.warn(f"跳过无效的豆瓣结果 - 标题:{title}, ID:{douban_id}")
                continue

            try:
                self.info(f"开始搜索云盘资源 - 标题:{title}, 豆瓣ID:{douban_id}")
                # 搜索云盘资源
                resources = self._cloudsaver_sdk.search(title)
                if not resources:
                    self.info(f"未找到标题为'{title}'的云盘资源")
                    continue
                    
                self.info(f"找到 {len(resources)} 条云盘资源")
                # 使用MediaFilter过滤资源
                media_filter = MediaFilter()
                filtered_resources = media_filter.filter_media(result, resources)
                if not filtered_resources:
                    self.info("经过MediaFilter过滤后无匹配资源")
                    continue
                    
                self.info(f"过滤后剩余 {len(filtered_resources)} 条匹配资源")
                cloud_resources.extend(filtered_resources)
            except Exception as e:
                self.error(f"搜索云盘资源失败: {str(e)}")
                import traceback
                self.debug(f"错误详情:\n{traceback.format_exc()}")

        return cloud_resources

    def save_to_cloud(self, resources: List[CloudResource]) -> bool:
        """保存资源到云盘"""
        if not resources:
            return False

        self.info(f"开始保存资源到云盘，共 {len(resources)} 条资源")
        for i, resource in enumerate(resources, 1):
            self.info(f"资源 {i}/{len(resources)}: {resource}")

        success = True
        for resource in resources:
            try:
                # 直接按照字典结构处理
                if resource["cloudType"] == "tianyi" and self._cloud189_sdk:
                    share_link = resource["cloudLinks"][0]["link"]
                    self._cloud189_sdk.save_to_cloud(share_link, resource['title'])
                # 可以添加其他云盘类型的处理
            except Exception as e:
                self.error(f"保存到云盘失败: {e}")
                success = False

        return success

    def refresh_rss(self):
        """刷新豆瓣RSS内容"""
        if not self._douban_content_types:
            self.warn("未配置豆瓣内容类型，无法刷新RSS")
            return

        # 调试模式：只处理第一个内容类型
        self._douban_content_types = self._douban_content_types[:1]
        self.info(f"调试模式：只处理第一个内容类型 {self._douban_content_types[0]}")

        try:
            for content_type in self._douban_content_types:
                self.info(f"开始处理内容类型: {content_type}")
                
                # 1. 获取豆瓣内容
                douban_results = self.get_douban_content(content_type)
                if not douban_results:
                    self.info(f"未获取到 {content_type} 类型的豆瓣内容")
                    continue
                self.info(f"获取到 {len(douban_results)} 条豆瓣内容")

                # 2. 过滤评分
                filtered_results = self.filter_by_rating(douban_results, self._min_douban_rating)
                if not filtered_results:
                    self.info("没有满足评分要求的内容")
                    continue
                self.info(f"过滤后剩余 {len(filtered_results)} 条满足评分要求的内容")

                # 3. 搜索云盘资源
                cloud_resources = self.search_cloud_resources(filtered_results)
                if not cloud_resources:
                    self.info("未找到匹配的云盘资源")
                    continue
                self.info(f"找到 {len(cloud_resources)} 条云盘资源")

                # 4. 保存到云盘
                if self.save_to_cloud(cloud_resources):
                    self.info(f"成功保存 {len(cloud_resources)} 条资源到云盘")
                else:
                    self.error("保存到云盘失败")
        except Exception as e:
            self.error(f"处理内容类型 {content_type} 失败: {str(e)}")

    def search_resources(self, keyword: str) -> List[CloudResource]:
        """搜索云盘资源"""
        if not self._cloudsaver_sdk or not self._cloudsaver_sdk.enabled:
            self.warn("CloudSaver未配置或未启用")
            return []

        try:
            results = self._cloudsaver_sdk.search(
                keyword, self._enabled_cloud_types)

            # 记录搜索历史
            if results:
                for result in results:
                    cloud_type_name = CLOUD_TYPE_MAP.get(
                        result.get('cloudType'), '未知')

                    # 尝试从结果中获取豆瓣ID
                    douban_id = result.get('doubanId') or result.get('id')

                    if douban_id:
                        # 使用豆瓣ID作为key记录搜索历史
                        self.__update_history_with_douban_id(
                            douban_id=douban_id,
                            title=result.get('title', keyword),
                            content=result.get('content', ''),
                            cloud_type=cloud_type_name,
                            state='FOUND',
                            cloud_links=result.get('cloudLinks', [])
                        )
                        self.info(
                            f"已保存到历史记录: {result.get('title', keyword)}，ID: {douban_id}")
                    else:
                        # 如果没有豆瓣ID，使用旧的方法记录历史
                        self.__update_history(
                            title=result.get('title', keyword),
                            content=result.get('content', ''),
                            cloud_type=cloud_type_name,
                            state='FOUND',
                            cloud_links=result.get('cloudLinks', [])
                        )
            else:
                # 即使没找到结果也记录搜索历史
                self.__update_history(
                    title=keyword,
                    content=f"搜索关键词: {keyword}",
                    cloud_type="搜索记录",
                    state='NEW'
                )

            return results
        except Exception as e:
            self.error(f"搜索失败: {str(e)}")
            # 记录搜索失败的历史
            self.__update_history(
                title=keyword,
                content=f"搜索失败: {str(e)}",
                cloud_type="搜索记录",
                state='ERROR'
            )
            return []

    def get_douban_hot_content(self) -> List[Dict]:
        """获取豆瓣热门内容"""
        if not self._cloudsaver_sdk or not self._cloudsaver_sdk.enabled:
            self.warn("CloudSaver未配置或未启用")
            return []

        if not self._douban_content_types:
            self.warn("未配置豆瓣内容类型")
            return []

        try:
            return self._cloudsaver_sdk.get_douban_hot_content(self._douban_content_types)
        except Exception as e:
            self.error(f"获取豆瓣热门内容失败: {str(e)}")
            return []

    def search_douban_content_in_cloud(self, content_list: List[Dict]) -> List[Dict]:
        """在云盘中搜索豆瓣内容"""
        if not self._cloudsaver_sdk or not self._cloudsaver_sdk.enabled:
            self.warn("CloudSaver未配置或未启用")
            return []

        try:
            return self._cloudsaver_sdk.search_douban_content_in_cloud(content_list, self._enabled_cloud_types)
        except Exception as e:
            self.error(f"在云盘中搜索豆瓣内容失败: {str(e)}")
            return []

    def test_connection(self) -> bool:
        """测试连接"""
        if not self._cloudsaver_sdk or not self._cloudsaver_sdk.enabled:
            return False

        try:
            return self._cloudsaver_sdk.login()
        except Exception as e:
            self.error(f"连接测试失败: {str(e)}")
            return False

    def get_page(self):
        """
        插件的额外页面，返回页面标题和页面内容
        :return: 标题，页面内容，确定按钮响应函数
        """
        results = self.get_history()
        template = """
             <div class="table-responsive table-modal-body">
               <table class="table table-vcenter card-table table-hover table-striped">
                 <thead>
                 <tr>
                   <th></th>
                   <th>标题</th>
                   <th>网盘类型</th>
                   <th>状态</th>
                   <th>添加时间</th>
                   <th></th>
                 </tr>
                 </thead>
                 <tbody>
                 {% if HistoryCount > 0 %}
                   {% for Item in CloudSaverHistory %}
                     <tr id="cloudsaver_history_{{ Item.id }}">
                       <td class="w-5">
                         <img class="rounded w-5" src="{{ Item.image }}"
                              onerror="this.src='../static/img/no-image.png'" alt=""
                              style="min-width: 50px"/>
                       </td>
                       <td>
                         <div>{{ Item.title }}</div>
                         {% if Item.content %}
                           <div class="text-muted text-nowrap">
                           {{ Item.content[:50] }}{% if Item.content|length > 50 %}...{% endif %}
                           </div>
                         {% endif %}
                       </td>
                       <td>
                         {{ Item.cloud_type }}
                       </td>
                       <td>
                         {% if Item.state == 'SAVED' %}
                           <span class="badge bg-green">已保存</span>
                         {% elif Item.state == 'FOUND' %}
                           <span class="badge bg-blue">已找到</span>
                         {% elif Item.state == 'NEW' %}
                           <span class="badge bg-blue">新增</span>
                         {% else %}
                           <span class="badge bg-orange">处理中</span>
                         {% endif %}
                       </td>
                       <td>
                         <small>{{ Item.add_time or '' }}</small>
                       </td>
                       <td>
                         <div class="dropdown">
                           <a href="#" class="btn-action" data-bs-toggle="dropdown"
                              aria-expanded="false">
                             <svg xmlns="http://www.w3.org/2000/svg" class="icon icon-tabler icon-tabler-dots-vertical {{ class }}"
                                  width="24" height="24" viewBox="0 0 24 24"
                                  stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                               <path stroke="none" d="M0 0h24v24H0z" fill="none"></path>
                               <circle cx="12" cy="12" r="1"></circle>
                               <circle cx="12" cy="19" r="1"></circle>
                               <circle cx="12" cy="5" r="1"></circle>
                             </svg>
                           </a>
                           <div class="dropdown-menu dropdown-menu-end">
                             <a class="dropdown-item text-danger"
                                href='javascript:CloudSaver_delete_history("{{ Item.id }}")'>
                               删除
                             </a>
                           </div>
                         </div>
                       </td>
                     </tr>
                   {% endfor %}
                 {% else %}
                   <tr>
                     <td colspan="6" align="center">没有数据</td>
                   </tr>
                 {% endif %}
                 </tbody>
               </table>
             </div>
           """
        return "搜索历史", Template(template).render(HistoryCount=len(results),
                                                 CloudSaverHistory=results), None

    @staticmethod
    def get_script():
        """
        删除CloudSaver搜索历史记录的JS脚本
        """
        return """
          // 删除CloudSaver搜索历史记录
          function CloudSaver_delete_history(id){
            ajax_post("run_plugin_method", {"plugin_id": 'CloudSaver', 'method': 'delete_search_history', 'history_id': id}, function (ret) {
              $("#cloudsaver_history_" + id).remove();
            });

          }
        """

    def delete_search_history(self, history_id):
        """
        删除搜索历史
        """
        return self.delete_history(key=history_id)

    def __update_history(self, title, content, cloud_type, state, cloud_links=None):
        """
        插入历史记录
        """
        if not title:
            return

        # 生成唯一ID
        history_id = f"{title}_{cloud_type}_{int(datetime.now().timestamp())}"

        value = {
            "id": history_id,
            "title": title,
            "content": content or "",
            "cloud_type": cloud_type or "未知",
            "state": state,
            "image": "../static/img/plugins/cloud.jpg",  # 使用默认云盘图标
            "cloud_links": cloud_links or [],
            "add_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        if self.get_history(key=history_id):
            self.update_history(key=history_id, value=value)
        else:
            self.history(key=history_id, value=value)

    def stop_service(self):
        """停止服务"""
        self._event.set()

    def __update_history_with_douban_id(self, douban_id, title, content, cloud_type, state, image=None, cloud_links=None):
        """
        使用豆瓣ID作为key插入历史记录
        """
        if not douban_id or not title:
            return

        value = {
            "id": douban_id,
            "title": title,
            "content": content or "",
            "cloud_type": cloud_type or "未知",
            "state": state,
            "image": image or "../static/img/plugins/cloud.jpg",  # 使用默认云盘图标或传入的图片
            "cloud_links": cloud_links or [],
            "add_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        if self.get_history(key=douban_id):
            self.update_history(key=douban_id, value=value)
        else:
            self.history(key=douban_id, value=value)
