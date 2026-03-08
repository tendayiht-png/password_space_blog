from django.views.generic import DetailView, ListView, TemplateView
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


class HowToPageView(TemplateView):
    template_name = 'how_to_page.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'How to Set Up Two-Factor Authentication (2FA)'
        context['description'] = 'Step-by-step guide to enable 2FA on your accounts and protect them from unauthorized access.'
        context['time_estimate'] = 'Estimated Time: 5-8 min'
        context['difficulty'] = 'Difficulty: Beginner'
        context['outcome'] = 'Outcome: Account protected'
        return context


class ChecklistPageView(TemplateView):
    template_name = 'checklist_page.html'
