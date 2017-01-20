import json
import logging
from urlparse import urlparse
import datetime
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import  reverse_lazy, resolve
from django.http.response import Http404, HttpResponseNotAllowed, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST, require_GET
from django.views.generic.detail import DetailView
from django.views.generic.edit import UpdateView, CreateView
from django.views.generic.list import ListView
from mysolr.mysolr import Solr
from pytz import UTC
import requests
from api.models import Blog, BlogClaim, Post, Image
from auth.models import DwwenUser
from dwwen_web.forms import BlogForm, BlogUpdateForm, BlogSearchForm, CreateDwwenBlogForm, PostForm, UpdatePostForm, ImageUploadForm
from django.utils.translation import ugettext as _
from dwwen_web.utils import markdown2text, summary

logger = logging.getLogger(__name__)

@login_required
def add_blog(request):
    # if this is a POST request we need to process the form data
    if request.method == 'POST':
        # create a form instance and populate it with data from the request:
        form = BlogForm(request.POST, request.FILES)
        # check whether it's valid:
        if form.is_valid():
            blog = form.save(commit=False)
            blog.user = request.user
            blog.type = Blog.FEED
            blog.save()
            form.save_m2m()
            return redirect('web-blog-list')

    # if a GET (or any other method) we'll create a blank form
    else:
        form = BlogForm()

    return render(request, 'blog/blog-add.html', {'form': form})


class BlogList(ListView):
    template_name = 'blog/blog_list.html'
    paginate_by = 50

    def get_queryset(self):
        return self.request.user.blogs.filter(type=Blog.FEED)


class BlogDetailView(DetailView):
    template_name = 'blog/blog_detail.html'

    def get_queryset(self):
        return Blog.objects.filter(type=Blog.FEED)


class BlogUpdate(UpdateView):
    form_class = BlogUpdateForm
    template_name = 'blog/blog_update.html'

    def get_queryset(self):
        return self.request.user.blogs.all()

    def get_success_url(self):
        blog = self.get_object()
        messages.success(self.request, _('Blog was updated successfully'))
        if blog.type == Blog.FEED:
            return reverse_lazy('web-blog-detail', kwargs={'pk': self.get_object().id})
        elif blog.type == Blog.DWWEN:
            return reverse_lazy('web-blog', kwargs={'username': self.request.user.username})


@login_required
def search_blog(request):
    # if this is a POST request we need to process the form data
    q = None
    if request.method == 'POST':
        # create a form instance and populate it with data from the request:
        form = BlogSearchForm(request.POST)
        # check whether it's valid:
        if form.is_valid():
            d = form.cleaned_data
            if d['name']:
                solr = Solr(settings.BLOGS_SOLR_URL)
                response = solr.search(q=u'{}'.format(d['name']), qf='name_ar name_en', rows=50, start=0)
                q = Blog.objects.filter(pk__in=[doc['pk'] for doc in response.documents])
            else:
                q = Blog.objects.filter(blog_url__icontains=d['url'])

    # if a GET (or any other method) we'll create a blank form
    else:
        form = BlogSearchForm()

    return render(request, 'blog/blog-search.html', {'form': form, 'blogs': q})


@login_required
def claim_blog(request):
    if request.method == 'POST':
        blog_id = request.POST.get('id', None)
        if not blog_id:
            raise Http404('missing blog id')
        resp = requests.post('https://api.dwwen.com/v1/blogclaims/',
                             data={'blog': 'https://api.dwwen.com/v1/blogs/{}/'.format(request.POST['id']),
                                   'csrfmiddlewaretoken': request.COOKIES['csrftoken']},
                             cookies=request.COOKIES, headers={'referer': 'https://api.dwwen.com/v1/'})
        if resp.status_code == requests.codes.ok or resp.status_code == requests.codes.created:
            messages.success(request, _('You claim was created successfully'))
        else:
            error = _('Could not create your claim, please try again later')
            try:
                errors = json.loads(resp.text)
                if errors.get('detail', None):
                    error = errors.get('detail')
                else:
                    for k, v in errors.iteritems():
                        for e in v:
                            messages.error(request, e)
            except:
                logger.exception('could not json parse response')
            messages.error(request, error)
    resp = requests.get('https://api.dwwen.com/v1/blogclaims/', cookies=request.COOKIES,  headers={'referer': 'https://api.dwwen.com/v1/'})
    if resp.status_code == requests.codes.ok:
        result = json.loads(resp.text)
        for blog_claim in result['results']:
            blog_id = int(resolve(urlparse(blog_claim['blog_obj']['url']).path).kwargs['pk'])
            blog_claim['blog_obj']['id'] = blog_id
            claim_id = int(resolve(urlparse(blog_claim['url']).path).kwargs['pk'])
            blog_claim['id'] = claim_id
        return render(request, 'blog/blog-claim-list.html', {'claims': result['results']})
    else:
        error = _('Could not load your claims, please try again later.')
        try:
            errors = json.load(resp.text)
            if errors.get('detail', None):
                error = errors.get('detail')
            else:
                for k, v in errors.iteritems():
                    messages.error(request, v)
        except:
            pass
        messages.error(request, error)
    return render(request, 'blog/blog-claim-list.html')



@login_required
def verify_blog(request, pk=None):
    if request.method == 'POST':
        claim = get_object_or_404(BlogClaim, pk=pk)
        resp = requests.post('https://api.dwwen.com/v1/blogclaims/{}/verify/'.format(claim.id),
                             data={'csrfmiddlewaretoken': request.COOKIES['csrftoken']},
                             cookies=request.COOKIES,  headers={'referer': 'https://api.dwwen.com/v1/'})
        if resp.status_code == requests.codes.ok:
            messages.success(request, _('Blog ownership was verified successfully.'))
        else:
            error = _('Error verifying blog')
            try:
                errors = json.loads(resp.text)
                if errors.get('detail', None):
                    error = errors.get('detail')
                else:
                    for k, v in errors.iteritems():
                        messages.error(request, v)
            except:
                pass
            messages.error(request, error)
        return redirect('web-blog-claim')

    else:
        return HttpResponseNotAllowed(['POST'])


@login_required
def create_dwwen_blog(request, pk=None):

    if Blog.objects.filter(user=request.user, type=Blog.DWWEN).count() > 1:
        messages.error(request, _('You can create only one blog.'))
        return redirect('web-blog', username=request.user.username)

    if request.method == 'POST':
        # create a form instance and populate it with data from the request:
        form = CreateDwwenBlogForm(request.POST, request.FILES)
        # check whether it's valid:
        if form.is_valid():
            blog = form.save(commit=False)
            blog.user = request.user
            blog.type = Blog.DWWEN
            blog.save()
            form.save_m2m()
            messages.success(request, _('Blog was created successfully.'))
            return redirect('web-blog', username=request.user.username)

    # if a GET (or any other method) we'll create a blank form
    else:
        form = CreateDwwenBlogForm()

    return render(request, 'blog/blog-create.html', {'form': form})


@login_required
def my_blog(request, pk=None):
    return redirect('web-blog', request.user.username)


@require_GET
def view_blog(request, username=None):

    try:
        user = DwwenUser.objects.get_by_username(username)
    except DwwenUser.DoesNotExist:
        raise Http404()
    blogs = Blog.objects.filter(user=user, type=Blog.DWWEN)

    if user != request.user and not blogs.exists():
        raise Http404

    context = dict()

    if blogs.exists():
        blog = blogs.first()
        posts = blog.posts.all().order_by('-published_date')
        if blog.user != request.user:
            posts = posts.filter(status=Post.PUBLISHED)
        context['is_owner'] = blog.user == request.user
        context['posts'] = posts
        context['blog'] = blog

    return render(request, 'blog/blog.html', context)



@login_required
def create_post(request, pk=None):
    blog = get_object_or_404(Blog, pk=pk, user=request.user)

    if request.method == 'POST':
        # create a form instance and populate it with data from the request:
        form = PostForm(request.POST, request.FILES, initial={'blog': blog})
        # check whether it's valid:
        if form.is_valid():
            if form.cleaned_data['blog'] != blog:
                raise Http404()
            post = form.save(commit=False)
            post.status = Post.DRAFT
            post.published_date = datetime.datetime.now(tz=UTC)
            try:
                post.full_content = markdown2text(post.markdown)
                post.summary = summary(post.full_content)
            except:
                pass
            post.save()
            messages.success(request, _('Post was created successfully.'))
            return redirect('web-post', pk=post.id)

    # if a GET (or any other method) we'll create a blank form
    else:
        form = PostForm(initial={'blog': blog})

    return render(request, 'blog/post-create.html', {'form': form, 'blog': blog})


@login_required
def update_post(request, pk=None):
    post = get_object_or_404(Post, pk=pk, blog__user=request.user)

    if request.method == 'POST':
        # create a form instance and populate it with data from the request:
        form = UpdatePostForm(request.POST, request.FILES, instance=post)
        # check whether it's valid:
        if form.is_valid():
            post = form.save(commit=False)
            try:
                post.full_content = markdown2text(post.markdown)
                post.summary = summary(post.full_content)
            except:
                pass
            post.save()
            messages.success(request, _('Post was updated successfully.'))
            return redirect('web-post', pk=post.id)

    # if a GET (or any other method) we'll create a blank form
    else:
        form = UpdatePostForm(instance=post)

    return render(request, 'blog/post-update.html', {'form': form, 'post': post})


@login_required
@require_POST
def delete_post(request, pk=None):
    post = get_object_or_404(Post, pk=pk, blog__user=request.user)
    post.delete()
    messages.success(request, _('Post was deleted successfully.'))

    return redirect('web-blog', pk=post.blog.id)


@login_required
@require_POST
def publish_post(request, pk=None):
    post = get_object_or_404(Post, pk=pk, blog__user=request.user)
    post.status = Post.PUBLISHED
    post.published_date = datetime.datetime.now(tz=UTC)
    post.save()
    messages.success(request, _('Post was published successfully.'))
    return redirect('web-post', pk=post.id)


class BlogPosts(ListView):
    template_name = 'blog/blog.html'
    paginate_by = 5
    context_object_name = "posts"

    def get_queryset(self):
        blog = Blog.objects.get(pk=self.kwargs['pk'], type=Blog.DWWEN)
        qs = blog.posts.all().order_by('-published_date')
        if blog.user != self.request.user:
            qs = qs.filter(status=Post.PUBLISHED)
        return qs

    def get_context_data(self, **kwargs):
        context = super(BlogPosts, self).get_context_data(**kwargs)
        blog = Blog.objects.get(pk=self.kwargs['pk'])
        context['blog'] = blog
        context['is_owner'] = blog.user == self.request.user
        return context


class PostDetailView(DetailView):
    template_name = 'blog/post.html'
    context_object_name = 'post'

    def get_object(self, queryset=None):
        post = Post.objects.get(pk=self.kwargs['pk'], blog__type=Blog.DWWEN)
        if post.status != Post.PUBLISHED and post.blog.user != self.request.user:
            return None
        return post

    def get_context_data(self, **kwargs):
        context = super(PostDetailView, self).get_context_data(**kwargs)
        post = self.get_object()
        context['is_owner'] = post.blog.user == self.request.user
        return context


class ImageUploadView(CreateView):
    template_name = 'gallery/image_upload_form.html'
    form_class = ImageUploadForm

    def form_valid(self, form):
        image = form.save(commit=False)
        image.user = self.request.user
        image.save()
        self.object = image
        url = self.request.build_absolute_uri(self.object.image.url)
        data = json.dumps({'url': url, 'title': form.cleaned_data.get('title')})
        return HttpResponse(data, mimetype='application/json')


class ImageDetailView(DetailView):
    template_name = 'gallery/image-details.html'
    context_object_name = 'image'

    def get_queryset(self):
        return Image.objects.filter(user=self.request.user)


class GalleryView(DetailView):
    template_name = 'gallery/gallery.html'
    context_object_name = 'image'

    def get_queryset(self):
        return Image.objects.filter(user=self.request.user)
