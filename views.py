from django.views.generic import DetailView, ListView
from .models import Post


class PostList(ListView):
    model = Post
    template_name = 'index.html'
    context_object_name = 'post_list'
    queryset = Post.objects.all().order_by('-created_on')


class PostDetail(DetailView):
    model = Post
    template_name = 'post_detail.html'
    context_object_name = 'post'
    slug_field = 'slug'
    slug_url_kwarg = 'slug'


