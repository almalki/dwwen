from django.conf.urls import patterns, url, include
from api.views import BlogViewSet, UserViewSet, FollowedBlogsView, TimelineViewSet, PostViewSet, FavoriteView, CountryViewSet, BlogCategoryViewSet, \
    BlogClaimViewSet, ImageGalleryViewSet

__author__ = 'abdulaziz'


from rest_framework import routers

router = routers.SimpleRouter()
router.register(r'blogs', BlogViewSet, base_name='blog')
router.register(r'users', UserViewSet, base_name='user')
router.register(r'timeline', TimelineViewSet, base_name='timeline')
router.register(r'posts', PostViewSet, base_name='post')
router.register(r'countries', CountryViewSet)
router.register(r'categories', BlogCategoryViewSet)
router.register(r'blogclaims', BlogClaimViewSet, base_name='blogclaim')
router.register(r'gallery', ImageGalleryViewSet, base_name='image')


urlpatterns = patterns('',
    url(r'^$', 'api.views.dwwen_api', name='v1-api-root'),
    url(r'^tag-cloud/$', 'api.views.tag_cloud', name='tag-cloud'),
    url(r'^', include(router.urls)),
    url(r'^following/$', FollowedBlogsView.as_view(), name='following-list'),

    url(r'^favorites/$', FavoriteView.as_view(), name='favorite-list'),

    url(r'^api-auth/', include('rest_framework.urls', namespace='rest_framework')),
    url(r'^docs/', include('rest_framework_swagger.urls')),
)