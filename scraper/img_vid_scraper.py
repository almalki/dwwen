__author__ = 'abdulaziz'

# The contents of this file are subject to the Common Public Attribution
# License Version 1.0. (the "License"); you may not use this file except in
# compliance with the License. You may obtain a copy of the License at
# http://code.reddit.com/LICENSE. The License is based on the Mozilla Public
# License Version 1.1, but Sections 14 and 15 have been added to cover use of
# software over a computer network and provide for limited attribution for the
# Original Developer. In addition, Exhibit A has been modified to be consistent
# with Exhibit B.
#
# Software distributed under the License is distributed on an "AS IS" basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied. See the License for
# the specific language governing rights and limitations under the License.
#
# The Original Code is reddit.
#
# The Original Developer is the Initial Developer.  The Initial Developer of
# the Original Code is reddit Inc.
#
# All portions of the code written by reddit are Copyright (c) 2006-2013 reddit
# Inc. All Rights Reserved.
###############################################################################

import cStringIO
import logging
import math
import urllib
import urllib2
import urlparse
import gzip

from bs4 import BeautifulSoup
from PIL import Image, ImageFile




logger = logging.getLogger(__name__)


def _image_to_str(image):
    s = cStringIO.StringIO()
    image.save(s, image.format)
    return s.getvalue()


def str_to_image(s):
    s = cStringIO.StringIO(s)
    image = Image.open(s)
    return image


def _clean_url(url):
    """url quotes unicode data out of urls"""
    url = url.encode('utf8')
    url = ''.join(urllib.quote(c) if ord(c) >= 127 else c for c in url)
    return url


def _initialize_request(url, referer):
    url = _clean_url(url)

    if not url.startswith(("http://", "https://")):
        return

    req = urllib2.Request(url)
    req.add_header('Accept-Encoding', 'gzip')
    #if g.useragent:
        #TODO
     #   req.add_header('User-Agent', 'Mozilla')
    if referer:
        req.add_header('Referer', referer)
    return req


def _fetch_url(url, referer=None):
    request = _initialize_request(url, referer=referer)
    if not request:
        return None, None
    response = urllib2.urlopen(request)
    response_data = response.read()
    content_encoding = response.info().get("Content-Encoding")
    if content_encoding and content_encoding.lower() in ["gzip", "x-gzip"]:
        buf = cStringIO.StringIO(response_data)
        f = gzip.GzipFile(fileobj=buf)
        response_data = f.read()
    return response.headers.get("Content-Type"), response_data



def _make_image_from_url(url, referer):
    if not url:
        return
    content_type, content = _fetch_url(url, referer=referer)
    if not content:
        return
    image = str_to_image(content)
    return image


class ThumbnailScraper(object):
    def __init__(self, url, content, content_type):
        self.url = url
        self.content = content
        self.content_type = content_type

    def scrape(self):
        imgs, videos = self._find_objects()
        images = []
        for url in imgs:
            try:
                image = _make_image_from_url(url, referer=self.url)
                images.append(image)
            except Exception:
                logger.exception("could not load image")
        return images, list(videos)

    def _extract_image_urls(self, soup):
        for img in soup.findAll("img", src=True):
            yield urlparse.urljoin(self.url, img["src"])

    def _extract_video_urls(self, soup):
        for vid in soup.findAll("iframe", src=True):
            if 'youtube.com/' in vid['src']:
                yield vid["src"]


    def _find_objects(self):

        images = set()
        videos = set()

        content_type, content = self.content_type, self.content

        if content_type and "html" in content_type and content:
            soup = BeautifulSoup(content)
        else:
            return None, None

        # ok, we have no guidance from the author. look for the largest
        # image on the page with a few caveats. (see below)

        for image_url in self._extract_image_urls(soup):
            images.add(image_url)

        for video_url in self._extract_video_urls(soup):
            videos.add(video_url)
        return images, videos