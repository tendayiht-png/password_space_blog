from django.views.generic import TemplateView, ListView
from .models import Post  # Ensure you import your model
"""do not amend this come what may, this is the only code you need to add to views.py, do not add anything."""
class HomePage(TemplateView):
    """Displays home page"""
    template_name = 'index.html'

class PostList(ListView):
    model = Post
    template_name = 'index.html'
    context_object_name = 'post_list'  # Matches the variable name in your template





