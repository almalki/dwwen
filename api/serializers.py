from datetime import datetime
from cities_light.models import Country
from django.core import validators
from django.core.exceptions import ValidationError
from pytz import UTC
from rest_framework import serializers, fields
from rest_framework.fields import CharField
from rest_framework.pagination import NextPageField, PreviousPageField, BasePaginationSerializer
from rest_framework.relations import HyperlinkedIdentityField
from rest_framework.reverse import reverse_lazy
from rest_framework.serializers import HyperlinkedModelSerializer, ModelSerializer, Serializer
from api.models import Blog, UserBlog, Post, BlogCategory, BlogClaim, Image
from api.utils import HyperlinkedImageField, check_username, ImageUrlField
from django.utils.translation import ugettext_lazy as _
import re
from auth.models import DwwenUser


__author__ = 'abdulaziz'


class CategorySerializer(HyperlinkedModelSerializer):
    class Meta:
        model = BlogCategory


class CountrySerializer(HyperlinkedModelSerializer):
    class Meta:
        model = Country


class BlogSerializer(HyperlinkedModelSerializer):
    image = HyperlinkedImageField(geometry='200x200', required=False)
    is_followed = serializers.SerializerMethodField('_is_followed')
    country_name = CharField(source='country.name', read_only=True)
    followers_count = fields.IntegerField(read_only=True)

    class Meta:
        model = Blog
        fields = ('url', 'type', 'name', 'blog_url', 'rss_url', 'description', 'country', 'country_name',
                  'created_date', 'last_update_date', 'image', 'is_followed', 'categories', 'followers_count')
        write_only_fields = ('country',)

    def _is_followed(self, obj):
        return bool(obj.followed)


class BlogUpdateSerializer(HyperlinkedModelSerializer):

    class Meta:
        model = Blog
        fields = ('name', 'description', 'country', 'image', 'categories')


class BlogBriefSerializer(BlogSerializer):
    class Meta:
        model = Blog
        fields = ('url', 'name', 'blog_url', 'rss_url', 'description',
                  'created_date', 'last_update_date', 'image')


class UserSerializer(ModelSerializer):
    url = HyperlinkedIdentityField(lookup_field='username', view_name='user-detail')
    password = fields.CharField(required=True, max_length=128, min_length=8, write_only=True)
    username = fields.CharField(required=True, max_length=15, min_length=3,
                                help_text=_('Required. 15 characters or fewer. Letters, numbers and underscore.'),
                                error_messages={'invalid_format': _('Username must consists of letters, numbers and underscore only')},
                                validators=[
                                    validators.RegexValidator(regex=re.compile('^[a-zA-Z0-9_]+$'),
                                                              message=_('Enter a valid username.'), code='invalid_format')])
    email = fields.EmailField(required=True, min_length=1)

    def validate_username(self, attrs, source):
        username = attrs[source].lower().strip().strip(' \t\n\r')
        check_username(username)
        user_exists = DwwenUser.objects.filter(email__iexact=username).exists()
        if user_exists:
            raise serializers.ValidationError(_("This username is already taken"))
        attrs[source] = username
        return attrs

    def validate_email(self, attrs, source):
        value = attrs[source].lower().strip().strip(' \t\n\r')
        email_exists = DwwenUser.objects.filter(email__iexact=value).exists()
        if email_exists:
            raise serializers.ValidationError(_("This email is already registered with another user"))
        attrs[source] = value
        return attrs

    class Meta:
        model = DwwenUser
        fields = ('url', 'username', 'email', 'password', 'first_name', 'last_name',
                  'is_active', 'last_login', 'date_joined')
        read_only_fields = ('is_active', 'last_login', 'date_joined')


class UserUpdateSerializer(UserSerializer):

    def validate_username(self, attrs, source):
        user = self.context['request'].user
        username = attrs[source].lower().strip().strip(' \t\n\r')
        check_username(username)
        user_exists = DwwenUser.objects.filter(email__iexact=username).exclude(pk=user.id).exists()
        if user_exists:
            raise serializers.ValidationError(_("This username is already taken"))
        attrs[source] = username
        return attrs

    def validate_email(self, attrs, source):
        user = self.context['request'].user
        value = attrs[source].lower().strip().strip(' \t\n\r')
        email_exists = DwwenUser.objects.filter(email__iexact=value).exclude(pk=user.id).exists()
        if email_exists:
            raise serializers.ValidationError(_("This email is already registered with another user"))
        attrs[source] = value
        return attrs

    class Meta:
        model = DwwenUser
        fields = ('username', 'email', 'first_name', 'last_name')


class ChangePasswordSerializer(Serializer):
    old_password = fields.CharField(required=True, max_length=512, min_length=8)
    new_password = fields.CharField(required=True, max_length=512, min_length=8)


class ResetPasswordSerializer(Serializer):
    email = fields.EmailField(required=True, label=_("Email"), max_length=254)


class UserBlogSerializer(ModelSerializer):
    blog = BlogBriefSerializer()

    class Meta:
        model = UserBlog
        fields = ('blog', 'created_date',)


class PostSerializer(HyperlinkedModelSerializer):
    image = HyperlinkedImageField(geometry='640x300', required=False, blank=True)
    favorited = serializers.SerializerMethodField('_is_favorated')
    liked = serializers.SerializerMethodField('_is_liked')
    like_count = serializers.IntegerField(read_only=True)
    blog_obj = BlogBriefSerializer(read_only=True, source='blog')
    text = serializers.CharField(required=False, source='content', write_only=True)
    link = serializers.HyperlinkedIdentityField(view_name='post-visit', source='*')

    class Meta:
        model = Post
        fields = ('url', 'title', 'summary', 'published_date', 'image', 'like_count',
                  'link', 'created_date', 'last_update_date', 'favorited', 'liked',
                  'blog_obj', 'blog', 'text')
        write_only_fields = ('blog',)
        read_only_fields = ('published_date',)

    def _is_favorated(self, obj):
        return bool(obj.favorited)

    def _is_liked(self, obj):
        return bool(obj.liked)

    def get_fields(self, *args, **kwargs):
        fields = super(PostSerializer, self).get_fields(*args, **kwargs)
        user = self.context['view'].request.user
        fields['blog'].queryset = Blog.objects.filter(type=Blog.DWWEN, user=user)
        return fields


class PostDetailSerializer(PostSerializer):
    content = fields.SerializerMethodField('_get_content')
    more_like_ths = fields.SerializerMethodField('_mlt_url')

    class Meta:
        model = Post
        fields = ('url', 'title', 'summary', 'published_date', 'image', 'like_count',
                  'link', 'content', 'created_date', 'last_update_date',
                  'favorited', 'liked', 'blog_obj', 'blog', 'more_like_ths')
        write_only_fields = ('blog',)

    def _get_content(self, obj):
        if obj.markdown:
            return obj.markdown
        if obj.full_content:
            return obj.full_content
        if len(obj.content) > len(obj.summary):
            return obj.content
        return obj.summary

    def _mlt_url(self, obj):
        return reverse_lazy('post-mlt', kwargs={'pk':obj.id}, request=self.context['request'])


class FavoritePostSerializer(PostSerializer):
    favorited_date = fields.DateTimeField(read_only=True)

    def _is_favorated(self, obj):
        return True

    class Meta:
        model = Post
        write_only_fields = ('blog',)
        fields = ('url', 'title','published_date', 'image', 'like_count',
                  'link', 'summary', 'created_date', 'last_update_date',
                  'favorited', 'liked', 'blog_obj', 'blog', 'favorited_date')


class BlogClaimSerializer(serializers.HyperlinkedModelSerializer):
    blog_obj = BlogBriefSerializer(read_only=True, source='blog')

    class Meta:
        model = BlogClaim
        fields = ('url', 'blog', 'blog_obj', 'is_verified', 'verification_key', 'expire_at')
        read_only_fields = ('user', 'is_verified', 'verification_key', 'expire_at')
        write_only_fields = ('blog',)

    def validate_blog(self, attrs, source):
        if self.context['request'].user == attrs['blog'].user:
            raise ValidationError(_('This blog already belongs to you.'))
        q = BlogClaim.objects.filter(blog=attrs['blog'], user=self.context['request'].user,
                                     is_verified=False, expire_at__gt=datetime.now(tz=UTC))
        if q.exists():
            raise ValidationError(_('An active claim request is already there.'))

        return attrs


class DwwenPaginationSerializer(BasePaginationSerializer):
    """
    Dwwen implementation of a pagination serializer.
    """
    next = NextPageField(source='*')
    previous = PreviousPageField(source='*')


class ImageSerializer(HyperlinkedModelSerializer):
    image = ImageUrlField()

    class Meta:
        model = Image
        fields = ('url', 'title', 'image',)