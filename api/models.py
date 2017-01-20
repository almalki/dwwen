import uuid
from caching.base import CachingMixin, CachingManager
from datetime import timedelta, datetime
from cities_light.models import Country as CCountry
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.manager import Manager
from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch.dispatcher import receiver
from django.utils.translation import gettext_lazy as _
from pytz import UTC
import urlnorm
from api.utils import path_and_rename, SoftDeletionModel, feed_validator

### TODO
###########################################################################
### add this to enforce db case insensitive username
#####   CREATE UNIQUE INDEX test_upper_idx ON auth_user (upper(username));
#####   CREATE UNIQUE INDEX test_upper_idx ON auth_user (upper(email));
###########################################################################


class Country(CCountry, CachingMixin):
    objects = CachingManager()

    class Meta:
        proxy = True


class Blog(SoftDeletionModel):

    ACTIVE = 0
    GONE = 1
    STATUS_CHOICES = (
        (ACTIVE, _('Active')),
        (GONE, _('Gone')),
    )

    FEED = 1
    DWWEN = 2
    TYPE_CHOICES = (
        (FEED, _('Feed')),
        (DWWEN, _('Dwwen')),
    )

    name = models.CharField(max_length=60)
    blog_url = models.URLField(unique=True, max_length=2048, blank=True, null=True,
                               verbose_name=_('Blog URL'))
    rss_url = models.URLField(unique=True, max_length=2048, blank=True, null=True,
                              verbose_name=_('RSS URL'), validators=[feed_validator, ])
    type = models.SmallIntegerField(choices=TYPE_CHOICES)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, blank=True, related_name='blogs')
    description = models.CharField(max_length=500)
    country = models.ForeignKey(Country, blank=True, null=True)
    status = models.IntegerField(choices=STATUS_CHOICES, default=ACTIVE)
    created_date = models.DateTimeField(auto_now_add=True)
    last_update_date = models.DateTimeField(auto_now=True)
    http_last_modified = models.CharField(max_length=100, blank=True)
    http_etag = models.CharField(max_length=200, blank=True)
    image = models.ImageField(upload_to=path_and_rename('blogs_images/%Y/%m/%d'), blank=True)
    categories = models.ManyToManyField('BlogCategory')
    followers = models.ManyToManyField(settings.AUTH_USER_MODEL, through='UserBlog', related_name='following')
    is_ownership_verified = models.BooleanField(default=False)
    followed = None
    followers_count = None

    # On Python 3: def __str__(self):
    def __unicode__(self):
        return self.name

    def delete(self, using=None):
        super(Blog, self).delete(using=using)
        UserBlog.objects.filter(blog=self).delete()
        FavoritePost.objects.filter(post__blog=self).delete()
        Post.objects.filter(blog=self).delete()

    def clean(self):
        if self.type == Blog.FEED:
            if not self.blog_url:
                raise ValidationError({'blog_url': [_("This field is required."), ]})

            if not self.rss_url:
                raise ValidationError({'rss_url': [_("This field is required."), ]})

            self.rss_url = urlnorm.norm(self.rss_url)
            self.blog_url = urlnorm.norm(self.blog_url)
            rss_url = self.rss_url.partition("?")[0]
            qs = Blog.objects.filter(rss_url__istartswith=rss_url).exclude(pk=self.id)
            if qs.exists():
                raise ValidationError({'rss_url': [_("URL already exists."), ], 'existing_blog': str(qs.first().id)})

            blog_url = self.blog_url.partition("?")[0]
            qs = Blog.objects.filter(blog_url__istartswith=blog_url).exclude(pk=self.id)
            if qs.exists():
                raise ValidationError({'blog_url': [_("URL already exists."), ], 'existing_blog': str(qs.first().id)})

        elif self.type == Blog.DWWEN:
            self.rss_url = None
            self.blog_url = None

    def full_clean(self, exclude=None, validate_unique=True):
        excludes = []
        excludes.extend(exclude)
        valid_unique = validate_unique
        if self.type == Blog.DWWEN:
            excludes.extend(['rss_url', 'blog_url'])
            valid_unique = False
        super(Blog, self).full_clean(exclude=excludes, validate_unique=valid_unique)


class BlogCategory(CachingMixin, models.Model):
    name = models.CharField(max_length=50)

    # On Python 3: def __str__(self):
    def __unicode__(self):
        return self.name

    objects = CachingManager()


class Post(SoftDeletionModel):

    DRAFT = 1
    PUBLISHED = 2
    STATUS_CHOICES = (
        (DRAFT, _('Draft')),
        (PUBLISHED, _('Published')),
    )

    title = models.CharField(max_length=255)
    published_date = models.DateTimeField()
    status = models.SmallIntegerField(choices=STATUS_CHOICES, default=PUBLISHED)
    blog = models.ForeignKey('Blog', related_name='posts')
    link = models.URLField(unique=True, max_length=2048, blank=True, null=True)
    summary = models.TextField(blank=True)
    content = models.TextField(blank=True)
    full_content = models.TextField(blank=True)
    content_html = models.TextField(blank=True)
    markdown = models.TextField(blank=True)
    created_date = models.DateTimeField(auto_now_add=True)
    last_update_date = models.DateTimeField(auto_now=True)
    image = models.ImageField(upload_to=path_and_rename('posts_images/%Y/%m/%d'), blank=True)
    favorited_by = models.ManyToManyField(settings.AUTH_USER_MODEL, through='FavoritePost',
                                          related_name='favorited_posts')
    liked_by = models.ManyToManyField(settings.AUTH_USER_MODEL, through='PostLike', related_name='liked_posts')
    favorited = None
    liked = None
    like_count = None

    # On Python 3: def __str__(self):
    def __unicode__(self):
        return self.title

    def delete(self, using=None):
        super(Post, self).delete(using=using)
        FavoritePost.objects.filter(post=self).delete()

    def clean(self):
        if self.blog.type == Blog.DWWEN:
            self.link = None

    def full_clean(self, exclude=None, validate_unique=True):
        excludes = []
        excludes.extend(exclude)
        valid_unique = validate_unique
        if self.blog.type == Blog.DWWEN:
            excludes.extend(['link'])
            valid_unique = False
        super(Post, self).full_clean(exclude=excludes, validate_unique=valid_unique)


class PostTag(CachingMixin, models.Model):
    tag = models.CharField(max_length=100)
    post = models.ForeignKey('Post', related_name='tags')

    def __unicode__(self):
        return self.tag

    cached = CachingManager()
    objects = Manager()


class UserBlog(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL)
    blog = models.ForeignKey('Blog')
    created_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'blog')


class FavoritePost(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='favorites')
    post = models.ForeignKey('Post', related_name='favorites')
    created_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'post')


class PostLike(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL)
    post = models.ForeignKey('Post', related_name='like')
    created_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'post')


class BlogClaim(models.Model):

    blog = models.ForeignKey('Blog')
    user = models.ForeignKey(settings.AUTH_USER_MODEL)
    is_verified = models.BooleanField(default=False) # if true blog should have been moved to this user
    verification_key = models.CharField(max_length=300)
    expire_at = models.DateTimeField()


class UserPostView(models.Model):

    VIEW = 1
    VISIT = 2
    TYPE_CHOICES = (
        (VIEW, _('View')),
        (VISIT, _('Visit website')),
    )

    post = models.ForeignKey('Post')
    user = models.ForeignKey(settings.AUTH_USER_MODEL)
    timestamp = models.DateTimeField(auto_now_add=True)
    type = models.SmallIntegerField(choices=TYPE_CHOICES)


class Image(models.Model):
    title = models.CharField(max_length=140, blank=True)
    date_created = models.DateTimeField(auto_now_add=True)
    date_modified = models.DateTimeField(auto_now=True)
    image = models.ImageField(upload_to=path_and_rename('gallery_images/%Y/%m/%d'))
    user = models.ForeignKey(settings.AUTH_USER_MODEL)


##################################################################################
################### SIGNALS ######################################################
##################################################################################


if not settings.DEBUG:
    from mysolr import Solr
    import search_serializers

    @receiver(pre_save, sender=BlogClaim)
    def initialize_blog_claim(sender, instance, raw, **kwargs):
        if not instance.id:
            instance.verification_key = str(uuid.uuid4())
            instance.expire_at = datetime.now(tz=UTC) + timedelta(days=5)

    @receiver(post_save, sender=Blog)
    def update_solr_blog(sender, instance, created, **kwargs):
        solr = Solr(settings.BLOGS_SOLR_URL)

        # Create documents
        serializer = search_serializers.SolrBlogSerializer(instance=instance)
        blog = serializer.data
        blog['created_date'] = blog['created_date'].strftime('%Y-%m-%dT%H:%M:%SZ')
        blog['last_update_date'] = blog['last_update_date'].strftime('%Y-%m-%dT%H:%M:%SZ')
        documents = [
            blog
        ]
        # Index using json is faster!
        solr.update(documents, 'json', commit=False)

        # Manual commit
        solr.commit()

    @receiver(post_delete, sender=Blog)
    def delete_blog_from_solr(sender, instance, **kwargs):
        solr = Solr(settings.BLOGS_SOLR_URL)
        solr.delete_by_key(instance.id, commit=False)
        solr.delete_by_query('blog:{}'.format(instance.id), commit=False)
        solr.commit()

    @receiver(post_save, sender=Post)
    def update_solr_post(sender, instance, created, **kwargs):
        if instance.status != Post.PUBLISHED:
            return
        solr = Solr(settings.POSTS_SOLR_URL)

        # Create documents
        serializer = search_serializers.SolrPostSerializer(instance=instance)
        post = serializer.data
        post['published_date'] = post['published_date'].strftime('%Y-%m-%dT%H:%M:%SZ')
        post['created_date'] = post['created_date'].strftime('%Y-%m-%dT%H:%M:%SZ')
        post['last_update_date'] = post['last_update_date'].strftime('%Y-%m-%dT%H:%M:%SZ')
        documents = [
            post
        ]
        # Index using json is faster!
        solr.update(documents, 'json', commit=False)

        # Manual commit
        solr.commit()

    @receiver(post_delete, sender=Post)
    def delete_post_from_solr(sender, instance, **kwargs):
        solr = Solr(settings.POSTS_SOLR_URL)
        solr.delete_by_key(instance.id, commit=False)
        solr.commit()