from django import forms
from django.utils.text import slugify

from .models import Post
from .sanitizers import sanitize_post_html


class PostEditorForm(forms.ModelForm):
    slug = forms.SlugField(required=False, max_length=200)

    class Meta:
        model = Post
        fields = ['title', 'slug', 'excerpt', 'content', 'status']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Post title'}),
            'slug': forms.TextInput(
                attrs={'class': 'form-control', 'placeholder': 'auto-generated-from-title'}
            ),
            'excerpt': forms.Textarea(
                attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Optional short summary'}
            ),
            'content': forms.Textarea(attrs={'class': 'form-control', 'rows': 14}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }

    def clean_slug(self):
        slug = (self.cleaned_data.get('slug') or '').strip()
        title = (self.cleaned_data.get('title') or '').strip()

        if not slug:
            slug = slugify(title)

        if not slug:
            raise forms.ValidationError('Please add a title so a URL slug can be created.')

        conflict_qs = Post.objects.filter(slug=slug)
        if self.instance.pk:
            conflict_qs = conflict_qs.exclude(pk=self.instance.pk)

        if conflict_qs.exists():
            raise forms.ValidationError('This slug is already in use. Please choose a different one.')

        return slug

    def clean_content(self):
        raw_content = self.cleaned_data.get('content', '')
        cleaned_content = sanitize_post_html(raw_content)
        if not cleaned_content:
            raise forms.ValidationError('Content cannot be empty after sanitization.')
        return cleaned_content
