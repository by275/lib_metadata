
# -*- coding: utf-8 -*-
import os, traceback

import requests
from lxml import html

from framework import SystemModelSetting
from system import SystemLogicTrans

from .plugin import P
from .site_util import SiteUtil

logger = P.logger

class SiteHentaku(object):
    @staticmethod
    def get_actor_info(entity_actor, proxy_url=None, retry=True):
        try:
            url = 'https://hentaku.co/starsearch.php'
            page = requests.post(url, headers=SiteUtil.default_headers, data={'name' : entity_actor['originalname']})
            page.encoding = 'utf-8'
            data = '<meta http-equiv=\"Content-Type\" content=\"text/html; charset=utf-8\">' + page.text
            tree = html.fromstring(data)
            nodes = tree.xpath('//img')
            if nodes:
                entity_actor['thumb'] = SiteUtil.process_image_mode('3', nodes[0].attrib['src'].strip())
                nodes = tree.xpath('//div[@class="avstar_info_b"]')
                tmps = nodes[0].text_content().split('/')
                entity_actor['name'] = tmps[0].strip()
                entity_actor['name2'] = tmps[1].strip()
                entity_actor['site'] = 'hentaku'
            return entity_actor
        except ValueError:
            # 2020-06-01
            # 단시간에 많은 요청시시 Error발생
            if retry:
                logger.debug(u'단시간 많은 요청으로 재요청')
                time.sleep(2)
                return SiteHentaku.get_actor_info(entity_actor, proxy_url=proxy_url, retry=False)
        except Exception as exception: 
            logger.error('Exception:%s', exception)
            logger.error(traceback.format_exc())
        return entity_actor
