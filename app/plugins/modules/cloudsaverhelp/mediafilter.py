import datetime
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

        filtered_list = self.filter_search_results(media_list, search_meta, datetime.datetime.now())

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

        filtered_list = self.filter_search_results(media_list, search_meta, datetime.datetime.now())

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

    def filter_search_results(self, result_array: list,
                              match_media,
                              start_time):
        """
        从搜索结果中匹配符合资源条件的记录
        """
        ret_array = []
        index_sucess = 0
        index_rule_fail = 0
        index_match_fail = 0
        index_error = 0
        for item in result_array:
            try:
                # 名称
                torrent_name = item.get('title')
                # 描述
                description = item.get('content')
                if not torrent_name:
                    index_error += 1
                    continue
                if match_media:
                    description = description if description else ""
                    torrent_name = torrent_name if torrent_name else ""
                meta_info = MetaInfo(title=torrent_name,
                                        subtitle=f"{description}",
                                        mtype=match_media.media_type,
                                        cn_name=match_media.org_string,
                                        en_name=match_media.original_title,
                                        tmdb_id=match_media.tmdb_id,
                                        imdb_id=match_media.imdb_id)
                meta_info.set_tmdb_info(self.media.get_tmdb_info(mtype=match_media.media_type,
                                                            tmdbid=match_media.tmdb_id,
                                                            append_to_response="all"))

                if not meta_info.get_name():
                    log.info(f"{torrent_name} 无法识别到名称")
                    index_match_fail += 1
                    continue

                # 识别媒体信息
                if not match_media:
                    # 不过滤
                    media_info = meta_info
                else:
                    # 0-识别并模糊匹配；1-识别并精确匹配
                    if meta_info.imdb_id \
                            and match_media.imdb_id \
                            and str(meta_info.imdb_id) == str(match_media.imdb_id):
                        # IMDBID匹配，合并媒体数据
                        media_info = self.media.merge_media_info(meta_info, match_media)
                    else:
                        # 查询缓存
                        cache_info = self.media.get_cache_info(meta_info)
                        if match_media \
                                and str(cache_info.get("id")) == str(match_media.tmdb_id):
                            # 缓存匹配，合并媒体数据
                            media_info = self.media.merge_media_info(meta_info, match_media)
                        else:
                            # 重新识别
                            media_info = self.media.get_media_info(title=torrent_name, subtitle=description, chinese=False)
                            if not media_info:
                                log.warn(f"{torrent_name} 识别媒体信息出错！")
                                index_error += 1
                                continue
                            elif not media_info.tmdb_info:
                                log.info(
                                    f"{torrent_name} 识别为 {media_info.get_name()} 未匹配到媒体信息")
                                index_match_fail += 1
                                continue
                            # TMDBID是否匹配
                            if str(media_info.tmdb_id) != str(match_media.tmdb_id):
                                log.info(
                                    f"{torrent_name} 识别为 "
                                    f"{media_info.type.value}/{media_info.get_title_string()}/{media_info.tmdb_id} "
                                    f"与 {match_media.type.value}/{match_media.get_title_string()}/{match_media.tmdb_id} 不匹配")
                                index_match_fail += 1
                                continue
                            # 合并媒体数据
                            media_info = self.media.merge_media_info(media_info, match_media)
                # 匹配到了
                log.info(
                    f"{torrent_name} {description} 识别为 {media_info.get_title_string()} "
                    f"{media_info.get_season_episode_string()} 匹配成功")
                index_sucess += 1
                ret_array.append(item)
            except Exception as err:
                print(str(err))
        # 循环结束
        # 计算耗时
        end_time = datetime.datetime.now()
        log.info(
            f"{len(result_array)} 条数据中，"
            f"过滤 {index_rule_fail}，"
            f"不匹配 {index_match_fail}，"
            f"错误 {index_error}，"
            f"有效 {index_sucess}，"
            f"耗时 {(end_time - start_time).seconds} 秒")
        return ret_array
