from django.db.models.aggregates import Count
from api.models import Blog, Post, BlogCategory, PostTag, UserBlog, FavoritePost, PostLike, BlogClaim, UserPostView
from django.core import management
from scraper.collector import fetch_post_content
from django.contrib import admin
from django.utils.translation import ugettext_lazy as _


class PostsByBlogListFilter(admin.SimpleListFilter):
    title = _('by blog')
    # Parameter for the filter that will be used in the URL query.
    parameter_name = 'blog'

    def lookups(self, request, model_admin):
        return ((d['blog_id'], d['blog__name']) for d in
                model_admin.get_queryset(request).values('blog_id', 'blog__name').annotate(c=Count('id')))

    def queryset(self, request, queryset):
        if self.value():
            return Post.all_objects.filter(blog_id=self.value())


def hard_delete(modeladmin, request, queryset):
    queryset.hard_delete()
hard_delete.short_description = "Hard Delete"


def refetch_post(modeladmin, request, queryset):
    for post in queryset:
        fetch_post_content.delay(post.id)
refetch_post.short_description = "Re-fetch post"


class BlogModelAdmin(admin.ModelAdmin):
    actions = [hard_delete, 'fetch_all_blogs']

    def get_queryset(self, request):
        return Blog.all_objects.all()

    def fetch_all_blogs(self, request, queryset):
        management.call_command('scheduleallblogs', verbosity=0, interactive=False)
    fetch_all_blogs.short_description = "Fetch RSS for all blogs"


class PostModelAdmin(admin.ModelAdmin):
    actions = [hard_delete, refetch_post]
    list_filter = (PostsByBlogListFilter,)

    def get_queryset(self, request):
        return Post.all_objects.all()



admin.site.register(Blog, BlogModelAdmin)
admin.site.register(Post, PostModelAdmin)
admin.site.register(BlogCategory)
admin.site.register(PostTag)
admin.site.register(UserBlog)
admin.site.register(FavoritePost)
admin.site.register(PostLike)
admin.site.register(BlogClaim)
admin.site.register(UserPostView)