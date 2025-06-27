from app.media.douban import DouBan
from app.plugins.modules.cloudsaverhelp.cloudsaversdk import CloudResource
from typing import Dict, List
from app.plugins.modules._base import _IPluginModule
from app.plugins.modules.cloudsaverhelp import CloudSaverSDK
from app.plugins.modules.cloudsaverhelp import MediaFilter
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
    _quark_folder_id = ""
    _quark_cookie = ""
    _tianyi_folder_id = ""
    _tianyi_username = ""
    _tianyi_pasword = ""
    _tianyi_captcha = ""
    _aliyun_folder_id = ""
    _baidu_folder_id = ""
    _douban_content_types = []

    def init_config(self, config: dict = None):
        """初始化配置"""
        if config:
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

            # 获取豆瓣内容类型
            self._douban_content_types = config.get(
                "douban_content_types", [])
            data = config.get("douban_content_types")
            log.info(f"获取豆瓣订阅类型{data}")

            # 获取网盘配置
            self._quark_folder_id = config.get("quark_folder_id", "")
            self._quark_cookie = config.get("quark_cookie", "")
            self._tianyi_folder_id = config.get("tianyi_folder_id", "")
            self._tianyi_username = config.get("tianyi_username", "")
            self._tianyi_password = config.get("tianyi_password", "")
            self._tianyi_captcha = config.get("tianyi_captcha", "")
            self._aliyun_folder_id = config.get("aliyun_folder_id", "")
            self._baidu_folder_id = config.get("baidu_folder_id", "")

            # 初始化CloudSaver SDK
            self._cloudsaver_sdk = CloudSaverSDK(config={
                'base_url': self._base_url,
                'username': self._username,
                'password': self._password,
                'enabled_cloud_types': self._enabled_cloud_types
            })
        else:
            # 提供默认配置用于测试
            self._enable = False
            self._base_url = "http://43.142.68.146:8008/"
            self._username = "a5420bc"
            self._password = "jin198250"
            self._enabled_cloud_types = [1]
            self._douban_content_types = []
            self._quark_folder_id = ""
            self._quark_cookie = ""
            self._tianyi_folder_id = ""
            self._tianyi_username = ""
            self._tianyi_password = ""
            self._tianyi_captcha = ""
            self._aliyun_folder_id = ""
            self._baidu_folder_id = ""

            self._cloudsaver_sdk = CloudSaverSDK(config={
                'base_url': self._base_url,
                'username': self._username,
                'password': self._password,
                'enabled_cloud_types': self._enabled_cloud_types
            })
            log.info("我开始搜索啦")
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
                'summary': '豆瓣热门内容类型',
                'tooltip': '选择要获取的豆瓣热门内容类型',
                'content': [
                    [
                        {
                            'id': 'douban_content_types',
                            'type': 'form-selectgroup',
                            'content': {
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
                    [
                        {
                            'title': '夸克网盘Cookie',
                            'required': "",
                            'tooltip': '夸克网盘的Cookie信息，用于身份验证，可通过浏览器开发者工具获取',
                            'type': 'textarea',
                            'content': [
                                {
                                    'id': 'quark_cookie',
                                    'placeholder': '请输入夸克网盘Cookie',
                                    'rows': 3
                                }
                            ]
                        }
                    ]
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
                            'title': '天翼云盘用户名',
                            'required': "",
                            'tooltip': '天翼云盘登录用户名（手机号）',
                            'type': 'text',
                            'content': [
                                {
                                    'id': 'tianyi_username',
                                    'placeholder': '请输入天翼云盘用户名',
                                }
                            ]
                        },
                        {
                            'title': '天翼云盘密码',
                            'required': "",
                            'tooltip': '天翼云盘登录密码',
                            'type': '*',
                            'content': [
                                {
                                    'id': 'tianyi_*',
                                    'placeholder': '请输入天翼云盘密码',
                                }
                            ]
                        }
                    ],
                    [
                        {
                            'title': '天翼云盘验证码',
                            'required': "",
                            'tooltip': '天翼云盘登录验证码（如需要）',
                            'type': 'text',
                            'content': [
                                {
                                    'id': 'tianyi_captcha',
                                    'placeholder': '请输入验证码（如需要）',
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

    def refresh_rss(self):
        """
        刷新豆瓣RSS内容
        根据配置的豆瓣内容类型，调用对应的豆瓣API方法获取内容
        """
        if not self._douban_content_types:
            self.warn("未配置豆瓣内容类型，无法刷新RSS")
            return []

        # 创建豆瓣API实例
        douban = DouBan()
        all_results = []
        
        # 调试模式：只处理第一个内容类型
        if self._douban_content_types:
            self.info(f"调试模式：只处理第一个内容类型 {self._douban_content_types[0]}，跳过其余内容类型")
            self._douban_content_types = self._douban_content_types[:1]

        # 遍历配置的豆瓣内容类型
        for content_type in self._douban_content_types:
            # 从映射中获取对应的方法名
            method_name = DOUBAN_METHOD_MAP.get(content_type)
            if not method_name:
                self.warn(f"未知的豆瓣内容类型: {content_type}")
                continue

            try:
                # 使用getattr动态调用对应的方法
                method = getattr(douban, method_name)
                if not method:
                    self.warn(f"豆瓣API中不存在方法: {method_name}")
                    continue

                # 调用方法获取结果
                # 调用方法获取结果
                results = method()

                # 打印调试信息
                self.info(f"获取豆瓣内容 {content_type} 成功，共 {len(results)} 条")
                
                # 打印每个结果的标题和ID，检查是否有重复
                print("豆瓣内容结果列表:")
                for i, res in enumerate(results):
                    title = res.get('title', '无标题')
                    douban_id = res.get('orgid') or res.get('id', '').replace('DB:', '')
                    print(f"  {i+1}. 标题: {title}, ID: {douban_id}")
                
                #TODO
                results = results[:1]
                print(f"限制为只处理第一个结果: {results[0].get('title', '无标题')}")
                
                # 使用CloudSaverSDK搜索云盘资源
                if results and self._cloudsaver_sdk and self._cloudsaver_sdk.enabled:
                    for result in results:
                        try:
                            # 获取标题和豆瓣ID
                            title = result.get('title', '')
                            douban_id = result.get('orgid') or result.get('id', '').replace('DB:', '')
                            
                            if not title or not douban_id:
                                continue
                            
                            # 使用豆瓣ID作为key查询历史记录
                            history_record = self.get_history(key=douban_id)
                            
                            # 如果已经有历史记录，且状态为SAVED或FOUND，则跳过搜索
                            if history_record and history_record.get('state') in ['SAVED', 'FOUND']:
                                self.info(f"媒体已经在历史记录中: {title}，豆瓣ID: {douban_id}，状态: {history_record.get('state')}，跳过搜索")
                                result['cloud_resources'] = history_record.get('cloud_links', [])
                                result['found_in_cloud'] = True
                                continue
                                
                            self.info(f"开始搜索云盘资源: {title}，豆瓣ID: {douban_id}")
                            # 使用CloudSaverSDK搜索云盘资源
                            cloud_resources = self._cloudsaver_sdk.search(title, self._enabled_cloud_types)
                            
                            if cloud_resources:
                                self.info(f"找到云盘资源: {title}，共 {len(cloud_resources)} 条")
                                
                                # 创建MediaFilter实例
                                media_filter = MediaFilter()
                                
                                # 使用MediaFilter过滤资源
                                filtered_resources = media_filter.filter_media(result, cloud_resources)
                                
                                if filtered_resources:
                                    self.info(f"过滤后的资源: {title}，共 {len(filtered_resources)} 条")
                                    # 将过滤后的资源添加到结果中
                                    result['cloud_resources'] = filtered_resources
                                    result['found_in_cloud'] = True
                                    
                                    # 记录搜索历史，使用豆瓣ID作为key
                                    self.__update_history_with_douban_id(
                                        douban_id=douban_id,
                                        title=title,
                                        content=filtered_resources[0].get('content', ''),
                                        cloud_type=CLOUD_TYPE_MAP.get(filtered_resources[0].get('cloudType'), '未知'),
                                        state='FOUND',
                                        image=result.get('image', '../static/img/plugins/cloud.jpg'),
                                        cloud_links=filtered_resources
                                    )
                                    self.info(f"已保存到历史记录: {title}，豆瓣ID: {douban_id}")
                                else:
                                    self.info(f"未找到匹配的云盘资源: {title}")
                                    result['cloud_resources'] = []
                                    result['found_in_cloud'] = False
                            else:
                                self.info(f"未找到云盘资源: {title}")
                                result['cloud_resources'] = []
                                result['found_in_cloud'] = False
                        except Exception as e:
                            self.error(f"搜索云盘资源失败: {title}, 错误: {str(e)}")
                            result['cloud_resources'] = []
                            result['found_in_cloud'] = False
                # 添加到总结果中
                if results:
                    for result in results:
                        result['content_type'] = content_type
                    all_results.extend(results)
            except Exception as e:
                self.error(f"获取豆瓣内容 {content_type} 失败: {str(e)}")

        return all_results

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
                        self.info(f"已保存到历史记录: {result.get('title', keyword)}，ID: {douban_id}")
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
