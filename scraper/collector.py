from datetime import datetime
from bs4 import BeautifulSoup
from lxml.html import document_fromstring
from pytz import UTC
from api.models import Blog, Post, PostTag
import html2text
import requests
from django.conf import settings
from dwwen_web.utils import summary
from scraper.image_scraper import get_main_image, get_image
from readability.readability import Document

__author__ = 'abdulaziz'


from django_rq import job
import logging
import feedparser

# Get an instance of a logger
logger = logging.getLogger(__name__)


@job
def fetch_rss(blog_id, rss_url, last_modified=None, etag=None):
    f = feedparser.parse(rss_url, modified=last_modified, etag=etag)
    logger.info('Blog: %s, rss_url: %s, last_modified: %s, etag: %s, fetched. HTTP response status: %s',
                blog_id, rss_url, last_modified, etag, getattr(f, 'status', None))

    blog = Blog.objects.get(pk=blog_id)
    if f.status == 301:
        blog.rss_url = f.href
        blog.save()
    if f.status == 410:
        blog.status = Blog.GONE
        blog.save()
    if f.status == 200:  # no change since last fetch

        if not blog.image:
            try:
                set_blog_image(blog, f)
            except:
                # at least we tried, not critical
                pass

        # if we fail to schedule a post, let the whole thing fail
        for entry in f.entries:
                create_post(entry, blog)

        logger.info('updating blog last_update and http_last_modified: blog_id: %s', blog_id)

        retag = getattr(f, 'etag', None)
        modified = getattr(f, 'modified', None)
        if retag:
            blog.etag = f.etag
        if modified:
            blog.http_last_modified = f.modified
        if modified or retag:
            blog.save()


@job
def fetch_post_content(post_id, image_url=None):
    logger.info('f545 %s', post_id)
    post = Post.objects.get(pk=post_id)

    r = requests.get(post.link)
    page_html = r.text
    logger.info('http resp status: %s', r.status_code)
    if r.status_code == requests.codes.ok:
        article = None
        boilerpipe_article = None


        # boilerpipe fails with cooments, lets use readability if it has reasonable length
        negative_keywords = ['popular-posts', 'widget-content', 'item-content', 'PopularPosts', 'sidebar',
                                 'popular-posts']
        positive_keywords = ['post-entry', 'post-body', 'entry-content', 'instapaper_body', 'entry', 'post',
                                 'hentry']
        doc = Document(page_html, negative_keywords=negative_keywords, positive_keywords=positive_keywords,
                           options={'debug': True}, debug=True)
        readability_article = doc.summary()

        if readability_article and len(readability_article) > 300:
            article = readability_article

        else:
            try:
                resp = requests.post(settings.BOILERPIPE_URL, data={"url": post.link})
                boilerpipe_article = resp.text
            except:
                pass

            if boilerpipe_article:
                article = boilerpipe_article
            else:
                article = post.content

        markdown = html2text.html2text(article)
        soup = BeautifulSoup(article)
        article_text = soup.get_text()

        try:
            image = get_main_image(post.link, page_html)
            if image:
                post.image = image

        except Exception as e:
            logger.exception('could not fetch post image')

        if article_text:
            post.full_content = article_text
        if article:
            post.content_html = article
        if markdown:
            post.markdown = markdown

        post.save()
        # id#story c#entry-content
        #BLOG_POST_XPATHS = [XPath(i) for i in ('/html/body[@itemtype="http://schema.org/BlogPosting"]', )]
    else:
        r.raise_for_status()


def create_post(entry, blog):
    if getattr(entry, 'published_parsed', None):
        import calendar
        pubdtime = calendar.timegm(entry.published_parsed)
        pupdate = datetime.fromtimestamp(pubdtime, tz=UTC)
    else:
        pupdate = datetime.now(tz=UTC)

    link = getattr(entry, 'feedburner_origlink', None) or entry.link
    try:
        post = Post.all_objects.get(blog_id=blog.id, link=link)
        logger.info('this post already fetched, id: %s, link: %s', post.id, post.link)
    except Post.DoesNotExist:

        article_content = None
        if getattr(entry, 'content', None):
            content_soup = BeautifulSoup(' '.join([c.value for c in entry.content]))
            article_content = content_soup.get_text()
        article_content = article_content or ''

        summary_soup = BeautifulSoup(entry.summary)
        article_summary = summary_soup.get_text()

        if not article_content:
            article_content = article_summary

        article_summary = summary(article_summary)

        post = Post.objects.create(title=entry.title, published_date=pupdate, blog=blog,
                                   link=link, summary=article_summary, content=article_content)
        tags = getattr(entry, 'tags', None)
        if tags:
            for tag in tags:
                logger.info('insering tags for post: %s', post.id)
                if tag['term']:
                    PostTag.objects.create(post=post, tag=tag['term'])

        mt = entry.get("media_thumbnail", None)
        thumbnail_url = None
        #if mt:
        #    thumbnail_url = mt[0]["url"]
        fetch_post_content.delay(post.id, image_url=thumbnail_url)


def set_blog_image(blog, parser):
    # if blog has no image(logo), try to get it from feed specs
    logo_url = None
    feed_image = getattr(parser.feed, 'logo', None)
    if feed_image:
        logo_url = feed_image
    else:
        feed_image = getattr(parser.feed, 'image', None)
        if feed_image:
            logo_url = feed_image.get('href', None)
    if not logo_url:
        logo_url = getattr(parser.feed, 'icon', None)

    if logo_url:
        file = get_image(logo_url, referer=blog.blog_url)
        blog.image = file
        blog.save()