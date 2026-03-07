from django.views.generic import TemplateView, ListView
from .models import Post  # Ensure you import your model
"""do not amend this come what may, this is the only code you need to add to views.py, do not add anything."""
class HomePage(TemplateView):
    """Displays home page"""
    template_name = 'index.html'

class PostList(generic.ListView):
    model = Post
    # Choose your preferred template name
    template_name = 'index.html'  
    # This allows you to use {% for post in post_list %} in your template
    context_object_name = 'post_list'  
    
    # Use queryset if you need to filter or order the posts
    queryset = Post.objects.all().order_by('-created_at') 




