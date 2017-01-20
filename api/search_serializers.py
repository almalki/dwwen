from rest_framework import fields, relations, pagination, serializers
from api.models import Blog, UserBlog, Post, PostTag
from api.serializers import BlogSerializer, PostSerializer, BlogBriefSerializer
from api.utils import HyperlinkedImageField, ImageRelativeUrlField

__author__ = 'abdulaziz'


class SolrBlogSerializer(BlogSerializer):
    pk = fields.IntegerField()
    user = relations.PrimaryKeyRelatedField()
    image = ImageRelativeUrlField()
    categories = relations.PrimaryKeyRelatedField(many=True)

    class Meta:
        model = Blog
        fields = ('pk', 'name', 'blog_url', 'rss_url', 'description', 'country_name',
                  'created_date', 'last_update_date', 'image', 'categories', 'type')


class SolrBlogResponseSerializer(BlogSerializer):
    url = relations.HyperlinkedIdentityField(view_name='blog-detail')
    user = fields.IntegerField()
    categories = relations.HyperlinkedRelatedField(view_name="blogcategory-detail", many=True)
    image = HyperlinkedImageField(geometry='200x200')
    is_followed = serializers.SerializerMethodField('_is_followed')

    class Meta:
        model = Blog
        fields = ('url', 'name', 'blog_url', 'rss_url', 'description', 'country_name', 'type'
                  'created_date', 'last_update_date', 'image', 'categories', 'is_followed')

    def _is_followed(self, obj):
        user = self.context['request'].user
        qs = self.context['queryset']
        ublog = filter(lambda x: x.id == obj.pk, qs)
        return bool(ublog)


class Struct:
    country_name = None
    country = None
    url = None
    name = None
    blog_url = None
    rss_url = None
    description = None
    created_date = None
    last_update_date = None
    image = None
    categories = None
    is_followed = None
    title = None
    published_date= None
    blog = None
    link = None
    summary = None

    def __init__(self, **entries):
        self.__dict__.update(entries)
        if entries.get('blog', None):
            self.blog = Struct(pk=entries.get('blog'))
        if entries.get('categories', None):
            self.categories = [Struct(pk=pk) for pk in entries.get('categories')]


class SolrBlogPaginationSerializer(pagination.PaginationSerializer):

    def __init__(self, *args, **kwargs):
        super(SolrBlogPaginationSerializer, self).__init__(*args, **kwargs)
        self.context = kwargs.get('context')
        user = self.context['request'].user
        qs  = UserBlog.objects.filter(blog_id__in=[doc.pk for doc in self.context.get('documents')],
                                      user_id=user.id)
        self.context['queryset'] = qs

    class Meta:
        object_serializer_class = SolrBlogResponseSerializer


####################################################################3
############### Post stuff    #####################################
###################################################################

class SolrPostSerializer(PostSerializer):
    pk = fields.IntegerField()
    blog = relations.PrimaryKeyRelatedField()
    image = ImageRelativeUrlField()
    tags = relations.RelatedField(many=True)
    content = fields.CharField(source='full_content')
    link = fields.URLField()

    class Meta:
        model = Post
        fields = ('pk', 'title', 'published_date', 'blog', 'image', 'tags',
                  'link', 'summary', 'content', 'created_date', 'last_update_date',)

    def get_fields(self, *args, **kwargs):
        return super(PostSerializer, self).get_fields(*args, **kwargs)


class SolrPostResponseSerializer(PostSerializer):
    url = relations.HyperlinkedIdentityField(view_name='post-detail')
    image = HyperlinkedImageField(geometry='640x300')
    blog_obj = serializers.SerializerMethodField('_get_related_blog')
    link = relations.HyperlinkedIdentityField(view_name='post-visit')

    class Meta:
        model = Post
        fields = ('url', 'title', 'published_date', 'image', 'blog_obj',
                  'link', 'summary', 'created_date', 'last_update_date',)

    def _get_related_blog(self, obj):
        blogs = self.context['blogs']
        blog = filter(lambda x: x.id == obj.blog.pk, blogs)
        if len(blog) > 0:
            return BlogBriefSerializer(instance=blog[0], context=self.context).data
        return None

    def get_fields(self, *args, **kwargs):
        return super(PostSerializer, self).get_fields(*args, **kwargs)


class SolrPostPaginationSerializer(pagination.PaginationSerializer):

    def __init__(self, *args, **kwargs):
        super(SolrPostPaginationSerializer, self).__init__(*args, **kwargs)
        self.context = kwargs.get('context')
        qs = Blog.objects.filter(pk__in=[post.blog.pk for post in self.context.get('posts')])
        self.context['blogs'] = qs

    class Meta:
        object_serializer_class = SolrPostResponseSerializer

