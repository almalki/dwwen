from django.conf.urls import patterns, url
from django.contrib.auth.decorators import login_required
from django.views.generic.base import TemplateView
from dwwen_web.views import BlogList, BlogDetailView, BlogUpdate, BlogPosts, PostDetailView, ImageUploadView, \
    ImageDetailView, GalleryView

__author__ = 'abdulaziz'


urlpatterns = patterns('dwwen_web.views',

    url(r'^$', TemplateView.as_view(template_name='home.html'), name='home'),
    url(r'^contact/$', TemplateView.as_view(template_name='contact.html'), name='contact'),
    url(r'^blogs/add/$', 'add_blog', name='web-blog-add'),
    url(r'^blogs/create/$', 'create_dwwen_blog', name='web-blog-create'),
    url(r'^blogs/$', login_required(BlogList.as_view()), name='web-blog-list'),
    url(r'^blogs/(?P<pk>[0-9]+)/update/$', login_required(BlogUpdate.as_view()), name='web-blog-update'),
    url(r'^blogs/(?P<pk>[0-9]+)/$', login_required(BlogDetailView.as_view()), name='web-blog-detail'),
    url(r'^blogs/search/$', 'search_blog', name='web-blog-search'),
    url(r'^blogs/claims/$', 'claim_blog', name='web-blog-claim'),
    url(r'^blogs/claims/(?P<pk>[0-9]+)/verify/$', 'verify_blog', name='web-blog-claim-verify'),

    url(r'^blogs/(?P<pk>[0-9]+)/posts/$', 'create_post', name='web-post-create'),
    url(r'^posts/(?P<pk>[0-9]+)/update$', 'update_post', name='web-post-update'),
    url(r'^posts/(?P<pk>[0-9]+)/delete$', 'delete_post', name='web-post-delete'),
    url(r'^posts/(?P<pk>[0-9]+)/publish$', 'publish_post', name='web-post-publish'),
    url(r'^posts/(?P<pk>[0-9]+)/$', PostDetailView.as_view(), name='web-post'),

    url(r'^gallery/upload/$', login_required(ImageUploadView.as_view()), name='web-upload-image'),
    url(r'^gallery/(?P<pk>[0-9]+)/$', login_required(ImageDetailView.as_view()), name='web-image-details'),
    url(r'^gallery/$', login_required(GalleryView.as_view()), name='web-gallery'),

    url(r'^blog/(?P<username>[a-zA-Z0-9_]+)/', 'view_blog', name='web-blog'),
    url(r'^blog/my-blog/', 'my_blog', name='my-blog'),


)