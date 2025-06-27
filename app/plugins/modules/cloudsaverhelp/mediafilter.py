from app.media.meta.metainfo import MetaInfo
import log
from typing import List, Dict, Any
from app.plugins.modules.cloudsaverhelp.cloudsaversdk import CloudResource
from app.media.media import Media
from app.utils.types import MediaType


class MediaFilter:
    """
    媒体过滤器类，用于过滤不匹配的媒体资源
    """

    def __init__(self):
        """初始化媒体过滤器"""
        self.media = Media()

    def filter_media(self, search_info: Dict[str, Any], media_list: List[CloudResource]) -> List[CloudResource]:
        """
        根据搜索信息自动确定调用哪个方法进行过滤

        Args:
            search_info: 搜索的媒体信息，包含type或media_type字段用于确定媒体类型
            media_list: 待过滤的媒体列表，类型为List[CloudResource]

        Returns:
            过滤后的媒体列表
        """
        if not search_info or not media_list:
            return []

        # 确定媒体类型
        media_type = search_info.get('media_type', '')
        type_code = search_info.get('type', '')

        # 根据媒体类型调用相应的过滤方法
        if media_type == "电影" or type_code == "MOV":
            log.debug(
                f"【MediaFilter】检测到电影类型，使用电影过滤器: {search_info.get('title', '')}")
            return self.filter_media_by_movie(search_info, media_list)
        elif media_type == "电视剧" or type_code == "TV":
            log.debug(
                f"【MediaFilter】检测到剧集类型，使用剧集过滤器: {search_info.get('title', '')}")
            return self.filter_media_by_tv(search_info, media_list)
        else:
            log.warning(f"【MediaFilter】未知媒体类型: {media_type}/{type_code}，无法过滤")
            return []

    def filter_media_by_movie(self, search_movie_info: Dict[str, Any], media_list: List[CloudResource]) -> List[CloudResource]:
        """
        使用MetaInfo过滤不是对应搜索电影的内容

        Args:
            search_movie_info: 搜索的电影信息，结构如下：
                {
                  "id": "DB:30429388",
                  "orgid": "30429388",
                  "title": "死神来了6：血脉诅咒",
                  "type": "MOV",
                  "media_type": "电影",
                  "year": "2025",
                  "vote": 6.9,
                  "image": "https://img3.doubanio.com/view/photo/m_ratio_poster/public/p2920455862.webp",
                  "overview": "2025 / 美国 加拿大 / 恐怖 / 亚当·B·斯坦 扎克·利波夫斯基 / 凯特琳·桑塔·胡安娜 特欧·布里奥尼斯"
                }
            media_list: 待过滤的媒体列表，类型为List[CloudResource]

        Returns:
            过滤后的媒体列表
        """
        if not search_movie_info or not media_list:
            return []

        # 获取搜索电影的元信息
        search_meta = self.media.get_media_info(title=search_movie_info.get('title', ''),
                                                mtype=MediaType.MOVIE)
        search_year = search_movie_info.get('year')

        filtered_list = []
        for media in media_list:
            title = media.get('title', '')
            content = media.get('content', '')

            # 使用Media.get_media_info获取更准确的媒体信息
            media_meta = self.media.get_media_info(title=title,
                                                   subtitle=content,
                                                   mtype=MediaType.MOVIE)

            # 判断是否为相同电影
            if self._is_same_movie(search_meta, media_meta, search_year):
                filtered_list.append(media)
            else:
                media_info = MetaInfo(title, content)
                log.debug(
                    f"【MediaFilter】过滤掉不匹配的媒体: {title}; meta_info的标题为 {media_info.cn_name}")

        # 如果过滤后没有匹配到任何数据，使用简单的标题包含比较
        if not filtered_list:
            filtered_list = self._apply_fallback_title_matching(
                search_movie_info, media_list)

        return filtered_list

    def _is_same_movie(self, search_meta, media_meta, search_year: str = None) -> bool:
        """
        判断两个媒体信息是否为同一部电影

        Args:
            search_meta: 搜索的电影元信息
            media_meta: 待比较的媒体元信息
            search_year: 搜索电影的年份

        Returns:
            是否为同一部电影
        """
        # 如果任一媒体信息为空，返回False
        if not search_meta or not media_meta:
            return False

        # 检查类型是否为电影
        if not media_meta.type or media_meta.type.value != "电影":
            return False

        # 检查标题是否匹配
        if not (search_meta.title and media_meta.title and
                (search_meta.title.lower() in media_meta.title.lower() or
                 media_meta.title.lower() in search_meta.title.lower())):
            return False

        # 如果有年份信息，检查年份是否匹配
        if search_year and media_meta.year and int(search_year) != int(media_meta.year):
            return False

        return True

    def filter_media_by_tv(self, search_tv_info: Dict[str, Any], media_list: List[CloudResource]) -> List[CloudResource]:
        """
        使用MetaInfo过滤不是对应搜索剧集的内容

        Args:
            search_tv_info: 搜索的剧集信息，包含title、season和episode等
            media_list: 待过滤的媒体列表，类型为List[CloudResource]

        Returns:
            过滤后的媒体列表
        """
        if not search_tv_info or not media_list:
            return []

        # 获取搜索剧集的元信息
        search_meta = self.media.get_media_info(title=search_tv_info.get('title', ''),
                                                mtype=MediaType.TV)
        search_season = search_tv_info.get('season')
        search_episode = search_tv_info.get('episode')

        filtered_list = []
        for media in media_list:
            title = media.get('title', '')
            content = media.get('content', '')

            # 使用Media.get_media_info获取更准确的媒体信息
            media_meta = self.media.get_media_info(title=title,
                                                   subtitle=content,
                                                   mtype=MediaType.TV)

            # 判断是否为相同剧集
            if self._is_same_tv_episode(search_meta, media_meta, search_season, search_episode):
                filtered_list.append(media)
            else:
                media_info = MetaInfo(title, content)
                log.debug(
                    f"【MediaFilter】过滤掉不匹配的媒体: {title}; meta_info的标题为 {media_info.cn_name}")

        # 如果过滤后没有匹配到任何数据，使用简单的标题包含比较
        if not filtered_list:
            filtered_list = self._apply_fallback_title_matching(
                search_tv_info, media_list)

        return filtered_list

    def _is_same_tv_episode(self, search_meta, media_meta,
                            search_season: str = None, search_episode: str = None) -> bool:
        """
        判断两个媒体信息是否为同一剧集

        Args:
            search_meta: 搜索的剧集元信息
            media_meta: 待比较的媒体元信息
            search_season: 搜索的季数
            search_episode: 搜索的集数

        Returns:
            是否为同一剧集
        """
        # 如果任一媒体信息为空，返回False
        if not search_meta or not media_meta:
            return False

        # 检查类型是否为剧集
        if not media_meta.type or media_meta.type.value != "电视剧":
            return False

        # 检查标题是否匹配
        if not (search_meta.title and media_meta.title and
                (search_meta.title.lower() in media_meta.title.lower() or
                 media_meta.title.lower() in search_meta.title.lower())):
            return False

        # 如果有季信息，检查季是否匹配
        if search_season and media_meta.begin_season and int(search_season) != int(media_meta.begin_season):
            return False

        # 如果有集信息，检查集是否匹配
        if search_episode and media_meta.begin_episode and int(search_episode) != int(media_meta.begin_episode):
            return False

        return True

    def _apply_fallback_title_matching(self, search_info: Dict[str, Any], media_list: List[CloudResource]) -> List[CloudResource]:
        """
        应用备用的标题匹配逻辑，当主要匹配方法没有结果时使用

        Args:
            search_info: 搜索的媒体信息
            media_list: 待过滤的媒体列表

        Returns:
            过滤后的媒体列表
        """
        log.debug(f"【MediaFilter】使用get_media_info没有匹配到任何数据，尝试使用简单标题包含比较")
        search_title = search_info.get('title', '').lower()
        filtered_list = []

        for media in media_list:
            title = media.get('title', '').lower()
            content = media.get('content', '').lower()

            # 简单的标题包含比较
            if self._is_title_contained(search_title, title, content):
                log.debug(f"【MediaFilter】通过简单标题比较匹配到媒体: {title}")
                filtered_list.append(media)

        return filtered_list

    def _is_title_contained(self, search_title: str, title: str, content: str = "") -> bool:
        """
        进行简单的标题包含比较

        Args:
            search_title: 搜索的标题
            title: 待比较的标题
            content: 待比较的内容

        Returns:
            是否包含
        """
        if not search_title or not title:
            return False

        # 转换为小写进行比较
        search_title = search_title.lower()
        title = title.lower()
        content = content.lower() if content else ""

        # 简单的包含比较
        if search_title in title or title in search_title:
            return True

        # 如果有内容，也进行包含比较
        if content and (search_title in content or content in search_title):
            return True

        return False
