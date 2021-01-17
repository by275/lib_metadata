
# -*- coding: utf-8 -*-
import os, requests, re, json, time
import traceback, unicodedata
from datetime import datetime

from lxml import html


from framework import app, SystemModelSetting, py_urllib
from framework.util import Util
from system import SystemLogicTrans
from system.logic_site import SystemLogicSite

import  framework.wavve.api as Wavve
from lib_metadata import MetadataServerUtil

from .plugin import P
from .entity_base import EntityMovie, EntityThumb, EntityActor, EntityRatings, EntityExtra, EntitySearchItemTv, EntityShow
from .site_util import SiteUtil
logger = P.logger


channelname_map = {
    u'카카오M' : 'kakaoTV',
    u'KBS 2TV' : 'KBS2',
    u'KBS 1TV' : 'KBS1',
}
mpaa_map = {'0' : u'모든 연령 시청가', '7' : u'7세 이상 시청가', '12' : u'12세 이상 시청가', '15' : u'15세 이상 시청가', '19' : u'19세 이상 시청가'}


class SiteWavve(object):
    site_name = 'wavve'


    @classmethod 
    def change_daum_channelname(cls, channelname):
        if channelname in channelname_map:
            return channelname_map[channelname]
        return channelname


class SiteWavveTv(SiteWavve):
    module_char = 'K'
    site_char = 'W'


    @classmethod 
    def search(cls, keyword, **kwargs):
        try:
            ret = {}
            search_list = Wavve.search_tv(keyword)
            if search_list:
                show_list = []
                """
                for item in search_list['list']:
                    if item['displaykeywords'].find('[스페셜]') != -1:
                        continue
                    entity = EntitySearchItemTv(cls.site_name)
                    entity.code = cls.module_char + cls.site_char + item['programid']
                    entity.title = item['displaykeywords']
                    entity.image_url = 'https://' + item['image']
                    entity.studio = item['channelname']
                    #entity.genre = cls.tving_base_image + item['cate_nm']
                    #entity.premiered = item['releasedate']
                    data['list'].append(entity.as_dict())
                """
                count_100 = 0
                for idx, item in enumerate(search_list):
                    entity = EntitySearchItemTv(cls.site_name)
                    entity.title = item['title_list'][0]['text']
                    if entity.title.find('[스페셜]') != -1:
                        continue
                    entity.code = (kwargs['module_char'] if 'module_char' in kwargs else cls.module_char) + cls.site_char + item['event_list'][1]['url'].split('=')[1]
                    entity.image_url = 'https://' + item['thumbnail']
                    #entity.studio = item['channelname']
                    #entity.genre = cls.tving_base_image + item['cate_nm']
                    #entity.premiered = item['releasedate']
                    if SiteUtil.compare_show_title(entity.title, keyword):
                        entity.score = 100 - count_100
                        count_100 += 1
                    else:
                        entity.score = 60 - idx * 5
                    show_list.append(entity.as_dict())
                ret['ret'] = 'success'
                ret['data'] = show_list
                
            else:
                ret['ret'] = 'empty'
        except Exception as exception: 
            logger.error('Exception:%s', exception)
            logger.error(traceback.format_exc())
            ret['ret'] = 'exception'
            ret['data'] = str(exception)
        return ret


    @classmethod 
    def apply_tv_by_search(cls, show):
        try:
            data = cls.search(show['title'])
            if data['ret'] == 'success':
                data = data['data']
                for item in data:
                    logger.debug(item)
                    if SiteUtil.compare_show_title(item['title'], show['title']) and SiteUtil.compare(cls.change_daum_channelname(item['title']), show['title']):
                        # and SiteUtil.compare(item['premiered'], show['premiered']):
                        info = Wavve.vod_programs_programid(item['code'][2:])
                        #if info['firstreleasedate'] == show['premiered']:
                        #    logger.debug(info)
                        cls._apply_tv_by_program(show, info)
                        break
        except Exception as exception: 
            logger.error('Exception:%s', exception)
            logger.error(traceback.format_exc())

    
    @classmethod
    def _apply_tv_by_program(cls, show, program_info):
        try:
            show['extra_info']['wavve_id'] = program_info['programid']
            

            if True:
                show['plot'] = program_info['programsynopsis'].replace('<br>', '\r\n')
            
            if True:
                score = 70
                show['thumb'].append(EntityThumb(aspect='landscape', value='https://' + program_info['image'], site=cls.site_name, score=0).as_dict())   
                show['thumb'].append(EntityThumb(aspect='poster', value='https://' + program_info['posterimage'], site=cls.site_name, score=score).as_dict()) 
            
            if True:
                page = 1
                epi = None
                while True:
                    episode_data = Wavve.vod_program_contents_programid(program_info['programid'], page=page)
                    for epi in episode_data['list']:
                        try: 
                            tmp = epi['episodenumber'].split('-')
                            if len(tmp) == 1:
                                epi_no = int(tmp[0])
                            else:
                                epi_no = int(tmp[1]) / 2
                        except: continue
                        if epi_no not in show['extra_info']['episodes']:
                            show['extra_info']['episodes'][epi_no] = {}

                        show['extra_info']['episodes'][epi_no][cls.site_name] = {
                            'code' : cls.module_char + cls.site_char + epi['contentid'],
                            'thumb' : 'https://' + epi['image'],
                            'plot' : epi['synopsis'].replace('<br>', '\r\n'),
                            'premiered' : epi['releasedate'],
                            'title' : epi['episodetitle'],
                        }
                    page += 1
                    if episode_data['pagecount'] == episode_data['count']:# or page == 6:
                        break
                # 방송정보에 없는 데이터 에피소드에서 빼서 입력
                if epi:
                    show['mpaa'] = mpaa_map[epi['targetage']]
                    
                    if len(show['actor']) == 0:
                        for item in epi['episodeactors'].split(','):
                            actor = EntityActor(item.strip())
                            actor.name = item.strip()
                            show['actor'].append(actor.as_dict())

        except Exception as exception: 
            logger.error('Exception:%s', exception)
            logger.error(traceback.format_exc())


    @classmethod 
    def info(cls, code):
        try:
            ret = {}
            program_info = Wavve.vod_programs_programid(code[2:])
            #ogger.debug(tving_program)
            
            show = EntityShow(cls.site_name, code)
            show.title = program_info['programtitle']
            show.originaltitle = show.title
            show.sorttitle = show.title 
            show.studio = cls.change_daum_channelname(program_info['channelname'])
            #show.plot = program_info['programsynopsis'].replace('<br>', '\r\n')
            show.premiered = program_info['firstreleasedate']
            show.year = int(show.premiered.split('-')[0])
            if program_info['closedate'] == '':
                show.status = 1
            else:
                show.status = 2

            if program_info['tags']['list']:
                show.genre = [program_info['tags']['list'][0]['text']]
            #show.episode = home_data['episode']
            
            show = show.as_dict()
            cls._apply_tv_by_program(show, program_info)
            ret['ret'] = 'success'
            ret['data'] = show

        except Exception as exception: 
            logger.error('Exception:%s', exception)
            logger.error(traceback.format_exc())
            ret['ret'] = 'exception'
            ret['data'] = str(exception)
        return ret            