from django.conf import settings
from django.core.management.base import BaseCommand
from mysolr.mysolr import Solr
from api import search_serializers
from api.models import Post

__author__ = 'abdulaziz'


class Command(BaseCommand):
    help = 'Index all posts in solr'

    def handle(self, *args, **options):

        solr = Solr(settings.POSTS_SOLR_URL)
        for post in Post.objects.all().prefetch_related('tags'):

            # Create documents
            serializer = search_serializers.SolrPostSerializer(instance=post)
            post_data = serializer.data
            post_data['published_date'] = post_data['created_date'].strftime('%Y-%m-%dT%H:%M:%SZ')
            post_data['created_date'] = post_data['created_date'].strftime('%Y-%m-%dT%H:%M:%SZ')
            post_data['last_update_date'] = post_data['last_update_date'].strftime('%Y-%m-%dT%H:%M:%SZ')
            documents = [
                post_data
            ]
            # Index using json is faster!
            solr.update(documents, 'json', commit=False)

        # Manual commit
        solr.commit()
