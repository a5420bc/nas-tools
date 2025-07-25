import os.path
import pickle

from app.utils import StringUtils, ExceptionUtils
from app.utils.commons import SingletonMeta
from config import Config


class IndexerHelper(metaclass=SingletonMeta):
    _indexers = []

    def __init__(self):
        self.init_config()

    def init_config(self):
        try:
            with open(os.path.join(Config().get_config_path(),
                                   "sites.dat"),
                      "rb") as f:
                self._indexers = pickle.load(f).get("indexer")
        except Exception as err:
            ExceptionUtils.exception_traceback(err)

    def get_all_indexers(self):
        return self._indexers

    def get_indexer_info(self, url, public=False):
        for indexer in self._indexers:
            if not public and indexer.get("public"):
                continue
            if StringUtils.url_equal(indexer.get("domain"), url):
                return indexer
        return None

    def get_indexer(self,
                    url,
                    siteid=None,
                    cookie=None,
                    name=None,
                    rule=None,
                    public=None,
                    proxy=False,
                    parser=None,
                    ua=None,
                    headers=None,
                    render=None,
                    language=None,
                    pri=None):
        if not url:
            return None
        for indexer in self._indexers:
            if not indexer.get("domain"):
                continue
            if StringUtils.url_equal(indexer.get("domain"), url):
                return IndexerConf(datas=indexer,
                                   siteid=siteid,
                                   cookie=cookie,
                                   name=name,
                                   rule=rule,
                                   public=public,
                                   proxy=proxy,
                                   parser=parser,
                                   ua=ua,
                                   headers=headers,
                                   render=render,
                                   builtin=True,
                                   language=language,
                                   pri=pri)
        return None


class IndexerConf(object):

    def __init__(self,
                 datas=None,
                 siteid=None,
                 cookie=None,
                 name=None,
                 rule=None,
                 public=None,
                 proxy=None,
                 parser=None,
                 ua=None,
                 headers=None,
                 render=None,
                 builtin=True,
                 language=None,
                 pri=None):
        if not datas:
            return
        # 索引ID
        self.id = datas.get('id')
        # 名称
        self.name = name if name else datas.get('name')
        # 是否内置站点
        self.builtin = builtin
        # 域名
        self.domain = datas.get('domain')
        # 搜索
        self.search = datas.get('search', {})
        # 批量搜索，如果为空对象则表示不支持批量搜索
        self.batch = self.search.get("batch", {}) if builtin else {}
        # 解析器
        self.parser = parser if parser is not None else datas.get('parser')
        # 是否启用渲染
        self.render = render and datas.get("render")
        # 浏览
        self.browse = datas.get('browse', {})
        # 种子过滤
        self.torrents = datas.get('torrents', {})
        # 分类
        self.category = datas.get('category', {})
        # 站点ID
        self.siteid = siteid
        # Cookie
        self.cookie = cookie
        # User-Agent
        self.ua = ua
        # 请求头
        self.headers = headers
        # 过滤规则
        self.rule = rule
        # 是否公开站点
        self.public = public if public is not None else datas.get('public')
        # 是否使用代理
        self.proxy = proxy if proxy is not None else datas.get('proxy')
        # 仅支持的特定语种
        self.language = language if language else datas.get('language')
        # 索引器优先级
        self.pri = pri if pri else 0
