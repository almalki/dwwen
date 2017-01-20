import logging
from django.db.models.query_utils import Q
from scraper.collector import fetch_post_content
from api.models import Post, Blog
from django.core.management.base import BaseCommand, CommandError

__author__ = 'abdulaziz'

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Re-fetch all posts with missing content field'

    def handle(self, *args, **options):
        for post in Post.objects.filter(Q(full_content__exact='') |
                Q(image__exact='')).filter(blog__type=Blog.FEED):

            try:
                fetch_post_content.delay(post.id)
            except Exception:
                logger.exception('exception scheduling re-fetch post')
                raise CommandError('Post "%s" could not be scheduled' % post.id)

            self.stdout.write('Successfully scheduled post "%s" for re-fetching' % post.id)