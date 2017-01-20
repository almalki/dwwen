from django.core.management.base import BaseCommand
from auth.models import DwwenUser
import sys

__author__ = 'abdulaziz'


class NotRunningInTTYException(Exception):
    pass


class Command(BaseCommand):
    help = 'delete all test users'

    def handle(self, *args, **options):
        qs = DwwenUser.objects.filter(email__endswith='@dwwen.com', username__istartswith='user')
        count = qs.count()

        try:
            answer = None
            # Get a confirmation
            while answer is None:
                answer = raw_input('Delete {} test users? (enter yes to confirm)'.format(count))
                if not answer:
                    continue
                if answer == 'yes':
                    qs.delete()

        except KeyboardInterrupt:
            self.stderr.write("\nOperation cancelled.")
            sys.exit(1)