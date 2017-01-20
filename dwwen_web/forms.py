from django import forms
from django.core.exceptions import ValidationError
from api.models import Blog, Post, Image
from django.utils.translation import ugettext as _

__author__ = 'abdulaziz'

labels = {
            "name": _("Name"),
            "blog_url": _("Blog URL"),
            "rss_url": _("RSS URL"),
            "description": _("Description"),
            "country": _("Country"),
            "image": _("Image"),
            "categories": _("Categories"),
            "title": _("Title"),
            "summary": _("summary"),
            "markdown": _("Post"),
        }


class BlogForm(forms.ModelForm):

    class Meta:
        model = Blog
        widgets = {
            'description': forms.Textarea(attrs={'cols': 80, 'rows': 10}),
        }
        fields = ('name', 'blog_url', 'rss_url', 'description', 'country', 'image', 'categories')
        labels = labels


class BlogUpdateForm(forms.ModelForm):

    class Meta:
        model = Blog

        widgets = {
            'description': forms.Textarea(attrs={'cols': 80, 'rows': 10}),
        }
        fields = ('name', 'description', 'country', 'image', 'categories')
        labels = labels


class BlogSearchForm(forms.Form):
    name = forms.CharField(max_length=60, required=False, label=_('Name'),
                           help_text=_('Blog name as currently registered in Dwwen'))
    url = forms.URLField(max_length=2048, required=False, label=_('URL'),
                         help_text=_('You can enter search by part of the url, like domain'))

    def clean(self):
        sf = self.cleaned_data['name'] or self.cleaned_data['url']
        if not sf:
            raise ValidationError(_('At least one search criteria must be provided'))
        return self.cleaned_data


class CreateDwwenBlogForm(forms.ModelForm):

    class Meta:
        model = Blog
        widgets = {
            'description': forms.Textarea(attrs={'cols': 80, 'rows': 10}),
        }
        fields = ('name', 'description', 'country', 'image', 'categories')
        labels = labels
        
        
class PostForm(forms.ModelForm):

    class Meta:
        model = Post
        widgets = {
            'markdown': forms.Textarea(attrs={'cols': 80, 'rows': 25, }),
            'blog': forms.HiddenInput(),
        }
        fields = ('title', 'markdown', 'image', 'blog')
        labels = labels


class UpdatePostForm(forms.ModelForm):

    class Meta:
        model = Post
        widgets = {
            'markdown': forms.Textarea(attrs={'cols': 80, 'rows': 25, }),
        }
        fields = ('title', 'markdown', 'image')
        labels = labels
        

class ImageUploadForm(forms.ModelForm):
    class Meta:
        model = Image
        fields = ('title', 'image', )
        labels = {
            'title': _('Title'),
            'image': _('Image')
        }