import logging
from urlparse import urlparse, parse_qs

__author__ = 'abdulaziz'

logger = logging.getLogger(__name__)


def video_id(value):
    """
    Examples:
    - http://youtu.be/SA2iWivDJiE
    - http://www.youtube.com/watch?v=_oPAwA_Udwc&feature=feedu
    - http://www.youtube.com/embed/SA2iWivDJiE
    - http://www.youtube.com/v/SA2iWivDJiE?version=3&amp;hl=en_US
    """
    query = urlparse(value)
    if query.hostname == 'youtu.be':
        return query.path[1:]
    if query.hostname in ('www.youtube.com', 'youtube.com'):
        if query.path == '/watch':
            p = parse_qs(query.query)
            return p['v'][0]
        if query.path[:7] == '/embed/':
            return query.path.split('/')[2]
        if query.path[:3] == '/v/':
            return query.path.split('/')[2]
    # fail?
    return None


def extract_videos(bsoup, full_soup):

    parent = None
    for child in bsoup.div.children:
        tid = child.get('id', None)
        tclass = child.get('class', None)
        if tid:
            parent = full_soup.select('#{}'.format(tid))[0].parent
        elif tclass:
            parent = full_soup.select('.{}'.format('.'.join(tclass)))[0].parent
        if parent:
            break
    iframes = parent.find_all('iframe')
    vids = []
    for iframe in iframes:
        src = iframe.get('src', None)
        if src:
            if 'youtu.be' in src or 'youtube.com' in src:
                vids.append(src)

    return vids