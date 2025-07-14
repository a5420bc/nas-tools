from datetime import datetime
from functools import lru_cache
import time
import requests

from app.utils import RequestUtils
from app.utils.types import MediaType
import log


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
        
        # 记录请求开始时间
        start_time = time.time()
        resp = cls._req.get_res(url=req_url, params=params)
        request_time = time.time() - start_time
        log.info(f"[Bangumi] 请求 {req_url} 耗时: {request_time:.3f}秒")
        
        if not resp:
            return None
            
        # 记录JSON解析开始时间
        json_start = time.time()
        result = resp.json()
        json_time = time.time() - json_start
        log.info(f"[Bangumi] JSON解析耗时: {json_time:.3f}秒")
        
        return result

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
        infos = self.calendar()
        if not infos:
            return []
        start_pos = (int(page) - 1) * self._page_num
        ret_list = []
        pos = 0
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

        return ret_list
