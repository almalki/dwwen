from datetime import date, timedelta, time, datetime
from StringIO import StringIO
import logging
from bs4 import BeautifulSoup
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core.paginator import InvalidPage
from django.db import transaction
from django.db.models.aggregates import Count
from django.http.response import Http404
from django.template import loader
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from mysolr.mysolr import Solr
from django.utils.translation import ugettext_lazy as _
from pytz import UTC
import requests
from rest_framework import mixins, viewsets
from rest_framework.decorators import api_view, detail_route, list_route
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.reverse import reverse
from api import search_serializers
from api.models import PostLike, FavoritePost, BlogCategory, Blog, UserBlog, Country, BlogClaim, Post, Image, UserPostView
from api.permissions import IsResourceOwnerOrReadOnly, IsAuthenticatedNonPost, IsAuthenticatedAndSameUser, \
    IsDwwenBlogOwner
from api.search_serializers import Struct
from rest_framework import status
from api.serializers import CategorySerializer, BlogUpdateSerializer, BlogSerializer, UserBlogSerializer, PostSerializer, \
    PostDetailSerializer, FavoritePostSerializer, CountrySerializer, UserSerializer, UserUpdateSerializer, \
    ChangePasswordSerializer, ResetPasswordSerializer, BlogClaimSerializer, BlogBriefSerializer, ImageSerializer
from api.task_queues import record_post_view
from api.throttles import EmailSendThrottle, BlogClaimVerifyThrottle
from api.utils import SolrPaginator
from django.conf import settings

logger = logging.getLogger(__name__)


class BlogCategoryViewSet(mixins.ListModelMixin,
                          mixins.RetrieveModelMixin,
                          viewsets.GenericViewSet):

    authentication_classes = (IsAuthenticated, )
    queryset = BlogCategory.objects.all()
    serializer_class = CategorySerializer
    paginate_by = None


class BlogViewSet(mixins.CreateModelMixin,
                  mixins.ListModelMixin,
                  mixins.RetrieveModelMixin,
                  mixins.UpdateModelMixin,
                  viewsets.GenericViewSet):
    '''
    Create, list, retrieve, search and update blogs.
    You can search for blogs with q parameter
    Use category param to filter blogs in specific category
    You can use orderBy param to order blogs by different criteria
    orderBy = popular | recent

    This endpoint supports pagination. See pagination documentation for more details.

    To follow a blog, send a post request to this URL:
    /blogs/{id}/follow
    To unfollow, send a delete request to the same URL.
    '''

    permission_classes = (IsAuthenticated, IsResourceOwnerOrReadOnly)

    def get_queryset(self):

        queryset = Blog.objects.annotate(followers_count=Count('followers'))\
            .select_related('country').prefetch_related('categories')

        category = self.request.GET.get('category', None)
        if category:
            try:
                cat = int(category)
                queryset = queryset.filter(categories=int(cat))
            except TypeError:
                pass

        orderBy = self.request.GET.get('orderBy', None)
        if orderBy:
            if orderBy == 'popular':
                queryset = queryset.order_by('-followers_count')

            elif orderBy == 'recent':
                queryset = queryset.order_by('-created_date')

        return queryset

    def list(self, request, *args, **kwargs):
        q = self.request.GET.get('q', None)
        if q:
            solr = Solr(settings.BLOGS_SOLR_URL)
            page_kwarg = self.kwargs.get(self.page_kwarg)
            page_query_param = self.request.QUERY_PARAMS.get(self.page_kwarg)
            page_num = page_kwarg or page_query_param or 1
            page_size = self.get_paginate_by()
            try:
                start = SolrPaginator.start(page_num, page_size)
            except InvalidPage as e:
                raise Http404(_('Invalid page (%(page_number)s): %(message)s') % {
                    'page_number': page_num,
                    'message': str(e)
                })
            response = solr.search(q=q, rows=page_size, start=start)
            docs = []
            if response.documents:
                for doc in response.documents:
                    docs.append(Struct(**doc))
                response.documents = docs
            self.paginator_class = SolrPaginator
            blogs_page = super(BlogViewSet, self).paginate_queryset(response)
            context=self.get_serializer_context()
            context['documents'] = docs
            serializer = search_serializers.SolrBlogPaginationSerializer(instance=blogs_page, context=context)

            return Response(serializer.data)
        return super(BlogViewSet, self).list(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.DATA, files=request.FILES)

        if serializer.is_valid():
            self.pre_save(serializer.object)
            self.object = serializer.save(force_insert=True)
            self.post_save(self.object, created=True)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED,
                            headers=headers)

        elif serializer.errors.get('existing_blog', None):
            id = serializer.errors['existing_blog']
            blog = Blog.objects.get(pk=int(id))
            serializer.errors["existing_blog"] = BlogBriefSerializer(blog, context={'request': request}).data
            return Response(serializer.errors, status=status.HTTP_409_CONFLICT)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def paginate_queryset(self, queryset, page_size=None):
        page = super(BlogViewSet, self).paginate_queryset(queryset=queryset, page_size=page_size)
        blogs = {blog.id: blog for blog in page}
        user_blogs = UserBlog.objects.filter(user=self.request.user, blog__in=[blog.id for blog in page])
        for user_blog in user_blogs:
            blogs[user_blog.blog_id].followed = True
        return page

    def get_object(self, queryset=None):
        blog = super(BlogViewSet, self).get_object(queryset=queryset)
        blog.followed = UserBlog.objects.filter(user=self.request.user, blog=blog).exists()
        return blog

    def pre_save(self, obj):
        obj.user = self.request.user

    def get_serializer_class(self):
        if self.request.method == 'PUT':
            return BlogUpdateSerializer
        return BlogSerializer

    @detail_route(methods=['post', 'delete'], permission_classes=(IsAuthenticated,))
    def follow(self, request, pk=None):
        blog = self.get_object()
        following = UserBlog.objects.filter(user=request.user, blog=blog)
        if request.method == 'DELETE':
            if following.exists():
                following.delete()
                return Response({'status': 'unfollowed'})
            else:
                return Response({},
                                status=status.HTTP_404_NOT_FOUND)
        else:
            if following.exists():
                return Response({'status': 'already followed'}, status=status.HTTP_400_BAD_REQUEST)
            UserBlog.objects.create(blog=blog, user=request.user)
            return Response({'status': 'followed'}, status=status.HTTP_201_CREATED)


class FollowedBlogsView(ListAPIView):
    '''
    List all blogs followed by current user ordered by date and time it was followed.
    This endpoint supports pagination. See pagination documentation for more details.
    '''

    permission_classes = (IsAuthenticated,)
    serializer_class = UserBlogSerializer

    def get_queryset(self):
        user = self.request.user
        return UserBlog.objects.filter(user=user).order_by('-created_date').select_related('blog')


class TimelineViewSet(mixins.ListModelMixin,
                      viewsets.GenericViewSet):
    '''
    Timeline of all posts from followed blogs.
    This endpoint supports pagination. See pagination documentation for more details.
    '''

    serializer_class = PostSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        user = self.request.user
        return Post.objects.filter(blog__followers=user,
                                   status=Post.PUBLISHED).order_by('-published_date').select_related('blog')

    def paginate_queryset(self, queryset, page_size=None):
        page = super(TimelineViewSet, self).paginate_queryset(queryset=queryset, page_size=page_size)
        posts = {post.id: post for post in page}

        # i am doing these bad things because of this https://code.djangoproject.com/ticket/19259
        # where orm generates a group by on all table fields
        # postgres struggles with generated query so i am getting rid of the whole join
        likes_count = PostLike.objects.values('post').filter(
            post_id__in=[post.id for post in page]).annotate(like_count=Count('user'))

        for like in likes_count:
            posts[like['post']].like_count = like['like_count']
        for post in page:
            if not post.like_count:
                post.like_count = 0

        favs = FavoritePost.objects.filter(user=self.request.user, post__in=[post.id for post in page])
        likes = PostLike.objects.filter(user=self.request.user, post__in=[post.id for post in page])
        for fav in favs:
            posts[fav.post_id].favorited = True
        for like in likes:
            posts[like.post_id].liked = True
        return page


class PostViewSet(mixins.ListModelMixin,
                  mixins.CreateModelMixin,
                  mixins.RetrieveModelMixin,
                  mixins.UpdateModelMixin,
                  mixins.DestroyModelMixin,
                  viewsets.GenericViewSet):
    '''
    List, search and retrieve blog posts.
    List all posts in descending order by published_date
    You can search for posts with q parameter
    You can use popular param to get most liked posts over specific time span
    popular=lastWeek|today

    This endpoint supports pagination. See pagination documentation for more details.

    To like a post, send a HTTP POST request to this URL:
    /posts/{id}/like/
    To unlike, send a delete request to the same URL.

    To favorite a post, send a HTTP POST request to this URL:
    /posts/{id}/favorite/
    To remove from favorites, send a delete request to the same URL.

    '''

    serializer_class = PostSerializer
    permission_classes = (IsAuthenticated, IsDwwenBlogOwner)

    def get_queryset(self):

        queryset = Post.objects.annotate(like_count=Count('liked_by')).select_related('blog')

        if self.action in ['update', 'publish', 'destroy']:
            return queryset.filter(blog__user=self.request.user, blog__type=Blog.DWWEN)

        queryset = queryset.filter(status=Post.PUBLISHED)

        blog = self.request.GET.get('blog', None)
        if blog:
            try:
                queryset = queryset.filter(blog_id=int(blog))
            except TypeError:
                pass

        orderBy = self.request.GET.get('popular', None)
        if orderBy:
            if orderBy == 'lastWeek':
                last_week = date.today()-timedelta(days=7)
                queryset = queryset.filter(published_date__range=(last_week, date.today())).order_by('-like_count')

            elif orderBy == 'today':
                today_min = datetime.combine(date.today(), time.min)
                today_max = datetime.combine(date.today(), time.max)
                queryset = queryset.filter(published_date__range=(today_min, today_max)).order_by('-like_count')

        else:
            queryset = queryset.order_by('-published_date')

        return queryset

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return PostDetailSerializer
        return PostSerializer

    def retrieve(self, request, *args, **kwargs):
        post = self.get_object()
        try:
            record_post_view.delay(post.id, request.user.id, UserPostView.VIEW)
        except:
            logger.exception('could not schedule user post view event persistence'
                             ' post_id: {}, user: {}, type: {}'.format(post.id, request.user.id, UserPostView.VIEW))
        return super(PostViewSet, self).retrieve(request, *args, **kwargs)

    def list(self, request, *args, **kwargs):
        q = self.request.GET.get('q', None)
        if q:
            solr = Solr(settings.POSTS_SOLR_URL)
            page_kwarg = self.kwargs.get(self.page_kwarg)
            page_query_param = self.request.QUERY_PARAMS.get(self.page_kwarg)
            page_num = page_kwarg or page_query_param or 1
            page_size = self.get_paginate_by()
            try:
                start = SolrPaginator.start(page_num, page_size)
            except InvalidPage as e:
                raise Http404(_('Invalid page (%(page_number)s): %(message)s') % {
                                    'page_number': page_num,
                                    'message': str(e)
                })
            response = solr.search(q=q, rows=page_size, start=start)
            docs = []
            if response.documents:
                for doc in response.documents:
                    docs.append(Struct(**doc))
                response.documents = docs
            self.paginator_class = SolrPaginator
            posts_page = super(PostViewSet, self).paginate_queryset(response)
            context=self.get_serializer_context()
            context['posts'] = docs
            serializer = search_serializers. SolrPostPaginationSerializer(instance=posts_page, context=context)
            return Response(serializer.data)

        return super(PostViewSet, self).list(request, *args, **kwargs)

    def paginate_queryset(self, queryset, page_size=None):
        page = super(PostViewSet, self).paginate_queryset(queryset=queryset, page_size=page_size)
        posts = {post.id: post for post in page}
        favs = FavoritePost.objects.filter(user=self.request.user, post__in=[post.id for post in page])
        likes = PostLike.objects.filter(user=self.request.user, post__in=[post.id for post in page])
        for fav in favs:
            posts[fav.post_id].favorited = True
        for like in likes:
            posts[like.post_id].liked = True
        return page

    def get_object(self, queryset=None):
        post = super(PostViewSet, self).get_object(queryset=queryset)
        post.favorited = FavoritePost.objects.filter(user=self.request.user, post=post).exists()
        post.liked = PostLike.objects.filter(user=self.request.user, post=post).exists()
        return post

    def pre_save(self, obj):
        obj.link = None
        obj.published_date = datetime.now(tz=UTC)
        obj.status = Post.DRAFT
        if not obj.summary:
            obj.summary = obj.content[:200]

    @detail_route(methods=['post', 'delete'])
    def publish(self, request, pk=None):
        post = self.get_object()
        if request.method == 'DELETE':
            if post.status == Post.PUBLISHED:
                post.status = Post.DRAFT
                post.save()
                return Response({'status': 'unpublished'}, status=status.HTTP_200_OK)
            else:
                return Response({'status': 'not published'}, status=status.HTTP_400_BAD_REQUEST)
        else:
            if post.status == Post.DRAFT:
                post.status = Post.PUBLISHED
                post.save()
                return Response({'status': 'published'}, status=status.HTTP_200_OK)
            else:
                return Response({'status': 'already published'}, status=status.HTTP_400_BAD_REQUEST)

    @detail_route(methods=['post', 'delete'])
    def like(self, request, pk=None):

        post = self.get_object()
        like = PostLike.objects.filter(user=request.user, post=post)
        if request.method == 'DELETE':
            if like.exists():
                like.delete()
                return Response({'status': 'like removed'})
            else:
                return Response({'detail': _('There is no like to remove')},
                                status=status.HTTP_404_NOT_FOUND)

        else:
            if like.exists():
                return Response({'status': 'already liked'}, status=status.HTTP_400_BAD_REQUEST)
            PostLike.objects.create(post=post, user=request.user)
            return Response({'status': 'liked'}, status=status.HTTP_201_CREATED)

    @detail_route(methods=['post', 'delete'])
    def favorite(self, request, pk=None):
        post = self.get_object()
        fav = FavoritePost.objects.filter(user=request.user, post=post)
        if request.method == 'DELETE':
            if fav.exists():
                fav.delete()
                return Response({'status': 'favorite removed'})
            else:
                return Response({'detail': _('There is no favorite to remove')},
                                status=status.HTTP_404_NOT_FOUND)

        else:
            if fav.exists():
                return Response({'status': 'already favorited'}, status=status.HTTP_400_BAD_REQUEST)
            FavoritePost.objects.create(post=post, user=request.user)
            return Response({'status': 'favorited'}, status=status.HTTP_201_CREATED)

    @detail_route(methods=['get', ])
    def mlt(self, request, pk=None):
        solr = Solr(settings.POSTS_SOLR_URL)
        post = self.get_object()
        context = self.get_serializer_context()
        mlt_result = solr.more_like_this(q='pk:{}'.format(post.id), rows=5, **{'mlt.fl': 'content_ar,content_en'})

        ## this is AAKKK and should be fixed
        qs = Blog.objects.filter(pk__in=[post['blog'] for post in mlt_result.documents])
        context['blogs'] = qs
        docs = []
        if mlt_result.documents:
            for doc in mlt_result.documents:
                docs.append(Struct(**doc))
        serializer = search_serializers.SolrPostResponseSerializer(instance=docs, context=context, many=True)
        return Response(serializer.data)

    @detail_route(methods=['get', ])
    def visit(self, request, pk=None):
        post = self.get_object()
        try:
            record_post_view.delay(post.id, request.user.id, UserPostView.VISIT)
        except:
            logger.exception('could not schedule user post view event persistence'
                             ' post_id: {}, user: {}, type: {}'.format(post.id, request.user.id, UserPostView.VISIT))

        return Response({}, status=status.HTTP_302_FOUND, headers={u'Location': post.link})


class FavoriteView(ListAPIView):
    '''
    List all favorited posts ordered by date and time it was favorited.
    favorited_date is the timestamp when the post was favorited
    This endpoint supports pagination. See pagination documentation for more details.
    '''

    permission_classes = (IsAuthenticated,)
    serializer_class = FavoritePostSerializer

    def get_queryset(self):
        user = self.request.user
        return user.favorited_posts.order_by('-created_date').select_related('blog')

    def paginate_queryset(self, queryset, page_size=None):
        page = super(FavoriteView, self).paginate_queryset(queryset=queryset, page_size=page_size)
        posts = {post.id: post for post in page}

        # i am doing these bad things because of this https://code.djangoproject.com/ticket/19259
        # postgres struggles with generated query so i am getting rid of the whole join
        likes_count = PostLike.objects.values('post').filter(
            post_id__in=[post.id for post in page]).annotate(like_count=Count('user'))

        for like in likes_count:
            posts[like['post']].like_count = like['like_count']
        for post in page:
            if not post.like_count:
                post.like_count = 0

        favs = FavoritePost.objects.filter(user=self.request.user, post__in=[post.id for post in page])
        likes = PostLike.objects.filter(user=self.request.user, post__in=[post.id for post in page])
        for fav in favs:
            posts[fav.post_id].favorited_date = fav.created_date
        page.object_list.sort(key=lambda r: r.favorited_date, reverse=True)
        for like in likes:
            posts[like.post_id].liked = True
        return page


class CountryViewSet(mixins.ListModelMixin,
                     mixins.RetrieveModelMixin,
                     viewsets.GenericViewSet):
    '''
    List and retrieve countries.
    '''

    serializer_class = CountrySerializer
    queryset = Country.objects.all()
    permission_classes = (IsAuthenticated,)
    paginate_by = None


class UserViewSet(mixins.CreateModelMixin,
                  mixins.RetrieveModelMixin,
                  mixins.UpdateModelMixin,
                  viewsets.GenericViewSet):
    '''
    Registration and user management.
    For registration, the request MUST NOT be authenticated(must be anonymous user).

    To change password, send HTTP post request with the new password to this URL:
    /users/change_password/

    To reset password, send POST request with email to this URL:
    /users/reset_password/

    '''

    lookup_field = 'username'
    lookup_url_kwarg = 'username'
    permission_classes = (IsAuthenticatedNonPost, IsAuthenticatedAndSameUser)
    queryset = get_user_model().objects.all()

    def create(self, request, *args, **kwargs):
        serialized = self.get_serializer(data=request.DATA, files=request.FILES)

        if serialized.is_valid():
            obj = serialized.object
            user = get_user_model().objects.create_user(
                obj.username, email=obj.email, password=obj.password,
                first_name=obj.first_name, last_name=obj.last_name
            )
            return Response(UserSerializer(instance=user, context={'request': request}).data,
                            status=status.HTTP_201_CREATED)
        else:
            return Response(serialized.errors, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        self.object = self.get_object_or_none()

        serializer = self.get_serializer(self.object, data=request.DATA,
                                         files=request.FILES, partial=partial)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        if self.object is None:
            return Response({}, status=status.HTTP_404_NOT_FOUND)

        self.object = serializer.save(force_update=True)
        return Response(UserSerializer(instance=get_user_model().objects.get(pk=request.user.id),
                                       context={'request': request}).data,
                        status=status.HTTP_200_OK)

    def get_serializer_class(self):
        if self.request.method == 'PUT':
            return UserUpdateSerializer
        if self.request.method == "POST" and 'change_password' in self.request.path:
            return ChangePasswordSerializer
        if self.request.method == "POST" and 'reset_password' in self.request.path:
            return ResetPasswordSerializer
        return UserSerializer

    @list_route(methods=['POST'], permission_classes=(IsAuthenticated,))
    def change_password(self, request):
        '''
        Change current authenticated user password
        '''
        user = request.user

        serialized = ChangePasswordSerializer(data=request.DATA)
        if serialized.is_valid():
            old_password = serialized.object['old_password']
            new_password = serialized.object['new_password']

            if old_password == new_password:
                return Response({'detail': _('new_password is the same as old_password')}, status=status.HTTP_400_BAD_REQUEST)

            if user.check_password(old_password):
                user.set_password(new_password)
                user.save()
                return Response({'detail': _('Password changed successfully')}, status=status.HTTP_200_OK)

            else:
                return Response({'detail': _('Incorrect old password')}, status=status.HTTP_400_BAD_REQUEST)

        else:
            return Response(serialized.errors, status=status.HTTP_400_BAD_REQUEST)

    @list_route(methods=['POST'], permission_classes=(AllowAny,), throttle_classes = (EmailSendThrottle,))
    def reset_password(self, request):
        '''
        Reset user password using email
        '''
        serialized = ResetPasswordSerializer(data=request.DATA)
        if serialized.is_valid():
            email = serialized.object['email']

            token_generator = default_token_generator
            email_template_name = 'accounts/password_reset_email.html'
            subject_template_name = 'accounts/password_reset_subject.txt'

            from django.core.mail import send_mail
            UserModel = get_user_model()
            active_user = UserModel._default_manager.filter(email__iexact=email, is_active=True)
            count = active_user.count()
            if count > 1:
                return Response({'detail': _('Unknown Error')}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            if count == 1:
                user = active_user.get()
                # Make sure that no email is sent to a user that actually has
                # a password marked as unusable
                if not user.has_usable_password():
                    return Response({'detail': _('You are not allowed to reset password')}, status=status.HTTP_403_FORBIDDEN)
                else:
                    domain = 'dwwen.com'
                c = {
                    'email': user.email,
                    'domain': domain,
                    'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                    'user': user,
                    'token': token_generator.make_token(user),
                    'protocol': 'https',
                }
                subject = loader.render_to_string(subject_template_name, c)
                # Email subject *must not* contain newlines
                subject = ''.join(subject.splitlines())
                email = loader.render_to_string(email_template_name, c)
                send_mail(subject, email, u'{} <{}>'.format(_('Dwwen'), settings.FROM_DWWEN_EMAIL), [user.email])
            return Response({'detail': _('An email with password reset instructions has been sent.')},
                            status=status.HTTP_200_OK)

        else:
            return Response(serialized.errors, status=status.HTTP_400_BAD_REQUEST)


class BlogClaimViewSet(mixins.CreateModelMixin,
                       mixins.ListModelMixin,
                       mixins.RetrieveModelMixin,
                       viewsets.GenericViewSet):
    '''
    Blog claims.
    A user can claim his blog and ownership will be transferred to him if he proves it regardless of previous owner.

    To verify the claim, a meta tag must be put on the blog HTML HEAD tag:
    &ltmeta name="dwwen_verification_key" content="key"&gt

    where key is unique for every claim. Claims expire in 7 days

    Once that verification meta tag is in place, a verification request can be place by HTTP POST to this URL:
    /blogclaims/{claim_id}/verify/
    '''

    serializer_class = BlogClaimSerializer
    permission_classes = (IsAuthenticated, )

    def get_queryset(self):
        user = self.request.user
        return BlogClaim.objects.filter(user=user, expire_at__gt=datetime.now(tz=UTC))

    def pre_save(self, obj):
        user = self.request.user
        obj.user = user

    @detail_route(methods=['POST'], permission_classes=(IsAuthenticated,), throttle_classes = (BlogClaimVerifyThrottle,))
    def verify(self, request, pk=None):
        '''
        Verify page has the correct key
        '''
        claim = self.get_object()
        if claim.is_verified:
            return Response({'detail': _('This claim request was already verified, create a new one')},
                            status=status.HTTP_400_BAD_REQUEST)
        blog = claim.blog
        if blog.user == request.user:
            return Response({'detail': _('This blog already belongs to you.')},
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            response = requests.get(claim.blog.blog_url, timeout=10)
            size = 0
            ctt = StringIO()
            maxsize = 1024000

            for chunk in response.iter_content(2048):
                size += len(chunk)
                ctt.write(chunk)
                if size > maxsize:
                    response.close()
                    return Response({'detail': _('Page size is too large')},
                                    status=status.HTTP_503_SERVICE_UNAVAILABLE)
            content = ctt.getvalue()
        except:
            return Response({'detail': _('Blog homepage is unreachable')},
                            status=status.HTTP_400_BAD_REQUEST)
        if response.status_code == requests.codes.ok:
            soup = BeautifulSoup(content)
            meta = (soup.find('meta', property='dwwen_verification_key') or
                        soup.find('meta', attrs={'name': 'dwwen_verification_key'}))
            if meta and meta.get('content', None):
                meta_key = meta['content']
                if claim.verification_key == meta_key:
                    with transaction.atomic():
                        claim.is_verified = True
                        blog.user = claim.user
                        blog.is_ownership_verified = True
                        claim.save()
                        blog.save()
                    return Response({'detail': _('Blog ownership verified, it is now all yours')}, status=status.HTTP_200_OK)
                else:
                    return Response({'detail': _('Key found, but invalid')}, status=status.HTTP_400_BAD_REQUEST)

            else:
                return Response({'detail': _('Missing key, please check the homepage has a meta tag with the key')},
                                status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({'detail': _('Blog homepage is unreachable')},
                            status=status.HTTP_400_BAD_REQUEST)


class ImageGalleryViewSet(mixins.CreateModelMixin,
                          mixins.ListModelMixin,
                          mixins.RetrieveModelMixin,
                          mixins.DestroyModelMixin,
                          viewsets.GenericViewSet):

    serializer_class = ImageSerializer
    permission_classes = (IsAuthenticated, )

    def get_queryset(self):
        return Image.objects.filter(user=self.request.user)

    def pre_save(self, obj):
        user = self.request.user
        obj.user = user


@api_view(('GET',))
def tag_cloud(request, format=None):
    '''
        Use this endpoint to retrieve tag cloud.
    '''
    solr = Solr(settings.POSTS_SOLR_URL)
    kargs = {'facet':'true', 'facet.field':'tags'}
    response = solr.search(q='*:*', rows=0, start=0, **kargs)
    facet_fields = response.facets.get('facet_fields', None)
    if facet_fields:
        tags = facet_fields.get('tags', None)
        if tags:
            return Response(tags)
    return Response({})


@api_view(('GET',))
def dwwen_api(request, format=None):
    endpoints = {
        'blogs': reverse('blog-list', request=request, format=format),
        'following': reverse('following-list', request=request, format=format),
        'timeline': reverse('timeline-list', request=request, format=format),
        'posts': reverse('post-list', request=request, format=format),
        'favorites': reverse('favorite-list', request=request, format=format),
        'countries': reverse('country-list', request=request, format=format),
        'categories': reverse('blogcategory-list', request=request, format=format),
        'tag-cloud': reverse('tag-cloud', request=request, format=format),
        'users': reverse('user-list', request=request, format=format),
        'change-password': reverse('user-change-password', request=request, format=format),
        'reset-password': reverse('user-reset-password', request=request, format=format),
        'blogclaims': reverse('blogclaim-list', request=request, format=format),
        'gallery': reverse('image-list', request=request, format=format),
    }

    if request.user.is_authenticated():
        endpoints['me'] = reverse('user-detail', kwargs={'username': request.user.username}, request=request,
                                  format=format)

    return Response(endpoints)
