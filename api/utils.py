import logging
import time
from django.conf import settings
from django.core import exceptions
from django.core.paginator import PageNotAnInteger, EmptyPage
from django_rq.decorators import job
import feedparser
from rest_framework import serializers
import os
from uuid import uuid4
from django.db import models
from django.db.models.query import QuerySet
from django.utils.translation import ugettext_lazy as _
from django.core.exceptions import ValidationError


__author__ = 'abdulaziz'

logger = logging.getLogger(__name__)


def path_and_rename(path):
    def wrapper(instance, filename):
        fpath =  time.strftime(path)
        ext = filename.split('.')[-1]
        # set filename as random string
        filename = '{}.{}'.format(uuid4().hex, ext)
        # return the whole path to the file
        return os.path.join(fpath, filename)
    return wrapper


def check_username(username):
    if username in settings.SECRET_RESERVED_USERNAMES:
        raise exceptions.ValidationError(_("This username is already taken"))

    for token in settings.NOT_ALLOWED_TOKENS:
        if token in username:
            raise exceptions.ValidationError(_("These words are not allowed in a username: %(banned)s") %
                                             {'banned': ' '.join(settings.NOT_ALLOWED_TOKENS)})


class SoftDeletionQuerySet(QuerySet):
    def delete(self):
        # Bulk delete bypasses individual objects' delete methods.
        return super(SoftDeletionQuerySet, self).update(alive=False)

    def hard_delete(self):
        return super(SoftDeletionQuerySet, self).delete()

    def alive(self):
        return self.filter(alive=True)

    def dead(self):
        return self.exclude(alive=True)


class SoftDeletionManager(models.Manager):
    def __init__(self, *args, **kwargs):
        self.alive_only = kwargs.pop('alive_only', True)
        super(SoftDeletionManager, self).__init__(*args, **kwargs)

    def get_queryset(self):
        if self.alive_only:
            return SoftDeletionQuerySet(self.model).filter(alive=True)
        return SoftDeletionQuerySet(self.model)

    def hard_delete(self):
        return self.get_queryset().hard_delete()


class SoftDeletionModel(models.Model):
    alive = models.BooleanField(default=True)

    objects = SoftDeletionManager()
    all_objects = SoftDeletionManager(alive_only=False)

    class Meta:
        abstract = True

    def delete(self, using=None):
        self.alive = False
        self.save(using=using)

    def hard_delete(self, using=None):
        super(SoftDeletionModel, self).delete(using=using)


class LiveField(models.Field):
    '''Similar to a BooleanField, but stores False as NULL.

    '''
    description = 'Soft-deletion status'
    __metaclass__ = models.SubfieldBase

    def __init__(self):
        super(LiveField, self).__init__(default=True, null=True)

    def get_internal_type(self):
        # Create DB column as though for a NullBooleanField.
        return 'NullBooleanField'

    def get_prep_value(self, value):
        # Convert in-Python value to value we'll store in DB
        if value:
            return 1
        return None

    def to_python(self, value):
        # Misleading name, since type coercion also occurs when
        # assigning a value to the field in Python.
        return bool(value)

    def get_prep_lookup(self, lookup_type, value):
        # Filters with .alive=False won't work, so
        # raise a helpful exception instead.
        if lookup_type == 'exact' and not value:
            msg = ("%(model)s doesn't support filters with "
                "%(field)s=False. Use a filter with "
                "%(field)s=None or an exclude with "
                "%(field)s=True instead.")
            raise TypeError(msg % {
                'model': self.model.__name__,
                'field': self.name})

        return super(LiveField, self).get_prep_lookup(lookup_type, value)


class HyperlinkedImageField(serializers.ImageField):

    def __init__(self, *args, **kwargs):
        self.geometry = kwargs.pop('geometry', '100x100')
        super(HyperlinkedImageField, self).__init__(*args, **kwargs)

    def to_native(self, value):
        if value:
            request = self.context.get('request', None)
            from sorl.thumbnail import get_thumbnail
            try:
                im = get_thumbnail(value, self.geometry, crop='center', format="PNG")
                return request.build_absolute_uri(im.url)
            except:
                logger.exception('unable to create thumbnail')
                return None


class ImageUrlField(serializers.ImageField):

    def to_native(self, value):
        if value:
            request = self.context.get('request', None)
            return request.build_absolute_uri(value.url)


class ImageRelativeUrlField(serializers.ImageField):
    read_only = True

    def to_native(self, value):
        if value:
            return value.name


import math

class SolrPaginator:
    """
    Create a Django-like Paginator for a solr response object. Can be handy
    when you want to hand off a Paginator and/or Page to a template to
    display results, and provide links to next page, etc.

    For more details see the Django Paginator documentation and solrpy
    unittests.

      http://docs.djangoproject.com/en/dev/topics/pagination/

    """

    def __init__(self, response, default_page_size=None, allow_empty_first_page=None):
        self.response = response
        self.documents = response.documents
        self.page_size = default_page_size

        if default_page_size:
            try:
                self.page_size = int(default_page_size)
            except ValueError:
                raise ValueError('default_page_size must be an integer')

        else:
            self.page_size = len(self.documents)

    @property
    def count(self):
        return int(self.response.total_results)

    @property
    def num_pages(self):
        if self.count == 0:
            return 0
        return int(math.ceil(float(self.count) / float(self.page_size)))

    @property
    def page_range(self):
        """List the index numbers of the available result pages."""
        if self.count == 0:
            return []
        # Add one because range is right-side exclusive
        return range(1, self.num_pages + 1)

    def page(self, page_num=1):
        """Return the requested Page object"""
        try:
            page_num = int(page_num)
        except:
            raise PageNotAnInteger

        if page_num not in self.page_range:
            raise EmptyPage, 'That page does not exist.'

        # Page 1 starts at 0; take one off before calculating
        return SolrPage(self.documents, page_num, self,
                highlighting=getattr(self.response.highlighting, 'highlighting', None),)

    def validate_number(self, number):
        """
        Validates the given 1-based page number.
        """
        try:
            number = int(number)
        except (TypeError, ValueError):
            raise PageNotAnInteger('That page number is not an integer')
        if number < 1:
            raise EmptyPage('That page number is less than 1')
        if number > self.num_pages:
            if number == 1:
                pass
            else:
                raise EmptyPage('That page contains no results')
        return number


    @classmethod
    def start(self, page_num=1, page_size=10):
        """Return the requested Page object"""
        try:
            page_num = int(page_num)
        except:
            raise PageNotAnInteger

        # Page 1 starts at 0; take one off before calculating
        start = (page_num - 1) * int(page_size)
        return start


class SolrPage:
    """A single Paginator-style page."""

    def __init__(self, result, page_num, paginator, highlighting):
        self.result = result
        self.number = page_num
        self.paginator = paginator
        self.highlighting = highlighting

    @property
    def object_list(self):
        return self.result

    def has_next(self):
        if self.number < self.paginator.num_pages:
            return True
        return False

    def has_previous(self):
        if self.number > 1:
            return True
        return False

    def has_other_pages(self):
        if self.paginator.num_pages > 1:
            return True
        return False

    def start_index(self):
        # off by one because self.number is 1-based w/django,
        # but start is 0-based in solr
        return (self.number - 1) * self.paginator.page_size

    def end_index(self):
        # off by one because we want the last one in this set,
        # not the next after that, to match django paginator
        return self.start_index() + len(self.result) - 1

    def next_page_number(self):
        return self.number + 1

    def previous_page_number(self):
        return self.number - 1






import collections

class OrderedSet(collections.MutableSet):

    def __init__(self, iterable=None):
        self.end = end = []
        end += [None, end, end]         # sentinel node for doubly linked list
        self.map = {}                   # key --> [key, prev, next]
        if iterable is not None:
            self |= iterable

    def __len__(self):
        return len(self.map)

    def __contains__(self, key):
        return key in self.map

    def add(self, key):
        if key not in self.map:
            end = self.end
            curr = end[1]
            curr[2] = end[1] = self.map[key] = [key, curr, end]

    def discard(self, key):
        if key in self.map:
            key, prev, next = self.map.pop(key)
            prev[2] = next
            next[1] = prev

    def __iter__(self):
        end = self.end
        curr = end[2]
        while curr is not end:
            yield curr[0]
            curr = curr[2]

    def __reversed__(self):
        end = self.end
        curr = end[1]
        while curr is not end:
            yield curr[0]
            curr = curr[1]

    def pop(self, last=True):
        if not self:
            raise KeyError('set is empty')
        key = self.end[1][0] if last else self.end[2][0]
        self.discard(key)
        return key

    def __repr__(self):
        if not self:
            return '%s()' % (self.__class__.__name__,)
        return '%s(%r)' % (self.__class__.__name__, list(self))

    def __eq__(self, other):
        if isinstance(other, OrderedSet):
            return len(self) == len(other) and list(self) == list(other)
        return set(self) == set(other)


def feed_validator(value):
    try:
        f = feedparser.parse(value)
        if not f.version:
            raise ValidationError(_("This URL doesn't point to a valid xml feed resource"))
    except:
        raise ValidationError(_("This URL doesn't point to a valid xml feed resource"))