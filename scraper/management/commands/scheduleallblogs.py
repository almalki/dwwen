import logging
from scraper.collector import fetch_rss
from api.models import Blog
from django.core.management.base import BaseCommand, CommandError

__author__ = 'abdulaziz'

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Schedule all active blogs for update'

    def handle(self, *args, **options):
        for blog in Blog.objects.filter(status=Blog.ACTIVE):
            try:
                fetch_rss.delay(blog.id, blog.rss_url,
                                last_modified=blog.http_last_modified, etag=blog.http_etag)
            except Exception:
                logger.exception('exception scheduling blogs')
                raise CommandError('Blog "%s" could not be scheduled' % blog.id)

            self.stdout.write('Successfully scheduled blog "%s"' % blog.id)