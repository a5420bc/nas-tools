from datetime import datetime
from functools import lru_cache
import time
import logging

import requests

from app.utils import RequestUtils
from app.utils.types import MediaType


logger = logging.getLogger(__name__)


class Bangumi(object):
    """
    https://bangumi.github.io/api/
    """

    _urls = {
        "calendar": "calendar",
        "detail": "v0/subjects/%s",
    }
    _base_url = "https://api.bgm.tv/"
    _req = RequestUtils(session=requests.Session())
    _page_num = 30

    def __init__(self):
        pass

    @classmethod
    @lru_cache(maxsize=128)
    def __invoke(cls, url, **kwargs):
        req_url = cls._base_url + url
        params = {}
        if kwargs:
            params.update(kwargs)
        resp = cls._req.get_res(url=req_url, params=params)
        return resp.json() if resp else None

    def calendar(self):
        """
        获取每日放送
        """
        return self.__invoke(self._urls["calendar"], _ts=datetime.strftime(datetime.now(), '%Y%m%d'))

    def detail(self, bid):
        """
        获取番剧详情
        """
        return self.__invoke(self._urls["detail"] % bid, _ts=datetime.strftime(datetime.now(), '%Y%m%d'))

    @staticmethod
    def __dict_item(item, weekday):
        """
        转换为字典
        """
        bid = item.get("id")
        detail = item.get("url")
        title = item.get("name_cn") or item.get("name")
        air_date = item.get("air_date")
        rating = item.get("rating")
        if rating:
            score = rating.get("score")
        else:
            score = 0
        images = item.get("images")
        if images:
            image = images.get("large")
        else:
            image = ''
        summary = item.get("summary")
        return {
            'id': "BG:%s" % bid,
            'orgid': bid,
            'title': title,
            'year': air_date[:4] if air_date else "",
            'type': 'TV',
            'media_type': MediaType.TV.value,
            'vote': score,
            'image': image,
            'overview': summary,
            'url': detail,
            'weekday': weekday
        }

    def get_bangumi_calendar(self, page=1, week=None):
        """
        获取每日放送
        """
        start_time = time.time()
        
        # API请求阶段
        api_start = time.time()
        infos = self.calendar()
        api_time = time.time() - api_start
        logger.debug(f"Bangumi API请求耗时: {api_time:.3f}s")
        
        if not infos:
            return []
            
        # 数据处理阶段
        process_start = time.time()
        start_pos = (int(page) - 1) * self._page_num
        ret_list = []
        pos = 0
        
        # 记录原始数据量
        total_items = sum(len(info.get("items", [])) for info in infos)
        logger.debug(f"开始处理数据，总条目数: {total_items}")
        
        for info in infos:
            weeknum = info.get("weekday", {}).get("id")
            if week and int(weeknum) != int(week):
                continue
            weekday = info.get("weekday", {}).get("cn")
            items = info.get("items")
            for item in items:
                if pos >= start_pos:
                    ret_list.append(self.__dict_item(item, weekday))
                pos += 1
                if pos >= start_pos + self._page_num:
                    break
        
        process_time = time.time() - process_start
        total_time = time.time() - start_time
        logger.debug(f"数据处理耗时: {process_time:.3f}s")
        logger.debug(f"总耗时: {total_time:.3f}s, 返回结果数: {len(ret_list)}")
        
        return ret_list
