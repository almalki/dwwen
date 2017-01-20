import StringIO
import logging
import bs4
import urllib
import urllib2
from PIL import ImageFile, Image
import urlparse
import cStringIO
import gzip
from django.core.files.uploadedfile import InMemoryUploadedFile

__author__ = 'abdulaziz'

logger = logging.getLogger(__name__)


def str_to_image(s):
    s = cStringIO.StringIO(s)
    image = Image.open(s)
    return image


def _extract_image_urls(soup, url):
    for img in soup.findAll("img", src=True):
        yield urlparse.urljoin(url, img["src"])

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
    req.add_header('User-Agent', 'dwwen_crawler')
    if referer:
        req.add_header('Referer', referer)
    return req


def _fetch_image_size(url, referer):
    """Return the size of an image by URL downloading as little as possible."""

    request = _initialize_request(url, referer)
    if not request:
        return None

    parser = ImageFile.Parser()
    response = None
    try:
        response = urllib2.urlopen(request)

        while True:
            chunk = response.read(1024)
            if not chunk:
                break

            parser.feed(chunk)
            if parser.image:
                return parser.image.size
    except urllib2.URLError:
        logger.exception('error fetching image')
        return None
    finally:
        if response:
            response.close()



def find_main_image_url(url, content):

    logger.info('finding main image from: %s', url)

    soup = bs4.BeautifulSoup(content)

    # allow the content author to specify the thumbnail:
    # <meta property="og:image" content="http://...">
    og_image = (soup.find('meta', property='og:image') or
                soup.find('meta', attrs={'name': 'og:image'}))
    if og_image and og_image['content']:
        return og_image['content']

    # <meta property="twitter:image" content="http://...">
    twitter_image = (soup.find('meta', property='twitter:image') or
                soup.find('meta', attrs={'name': 'twitter:image'}))
    if twitter_image and twitter_image.get('content'):
        return twitter_image['content']

    # <meta property="twitter:image" content="http://...">
    twitter_image = (soup.find('meta', property='twitter:image:src') or
                soup.find('meta', attrs={'name': 'twitter:image:src'}))
    if twitter_image and twitter_image.get('content'):
        return twitter_image['content']

    # <link rel="image_src" href="http://...">
    thumbnail_spec = soup.find('link', rel='image_src')
    if thumbnail_spec and thumbnail_spec.get('href'):
        return thumbnail_spec['href']

    # wp_image = soup.find('img', class_='wp-post-image')
    # if wp_image and wp_image.get('src'):
    #     return wp_image['src']

    logger.info('ok, we have no guidance from the author. look for candidates')

    # ok, we have no guidance from the author. look for the largest
    # image on the page with a few caveats. (see below)
    max_area = 0
    max_url = None
    for image_url in _extract_image_urls(soup, url):
        size = _fetch_image_size(image_url, referer=url)
        logger.info(size)
        if not size:
            logger.debug('missing image size')
            continue

        area = size[0] * size[1]

        # ignore little images
        if area < 5000:
            logger.info('ignore little %s' % image_url)
            continue

        # ignore excessively long/wide images
        if max(size) / min(size) > 3:
            logger.info('ignore dimensions %s' % image_url)
            continue

        # penalize images with "sprite" in their name
        if 'sprite' in image_url.lower():
            logger.info('penalizing sprite %s' % image_url)
            area /= 10

        if area > max_area:
            max_area = area
            max_url = image_url

    logger.info('found main image: %s', max_url)
    return max_url


def fetch_url(url, referer=None):
    logger.info('fetching url: %s', url)
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


def get_main_image(url, content):
    img_url = find_main_image_url(url, content)
    if img_url:
        return get_image(img_url, url)


def get_image(url, referer=None):
    logger.info('fetching image: %s', url)
    content_type, content = fetch_url(url, referer=referer)
    image = str_to_image(content)
    img_io = StringIO.StringIO()
    image.save(img_io, format='PNG')
    file = InMemoryUploadedFile(img_io, None, 'foo.jpg', 'image/png',
                                img_io.len, None)
    return file