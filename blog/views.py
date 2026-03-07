from django.views.generic import DetailView, TemplateView, ListView
from .models import Post  # Ensure you import your model
"""do not amend this come what may, this is the only code you need to add to views.py, do not add anything."""

from django.http import HttpResponse
from django.shortcuts import render

def hello_view(request):
    return HttpResponse("Hello, world!")

def template_view(request):
    return render(request, "hello.html", {"name": "Tenda"})
class HomePage(TemplateView):
    """Displays home page"""
    template_name = 'index.html'

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


