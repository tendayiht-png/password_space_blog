from django.contrib import admin
from django.conf import settings
# Import models to connect
# Register your models here.
from .models import Post, Comment
from django.contrib.auth.models import User

# Register your models here.
admin.site.register(Post)
admin.site.register(Comment)

class PostAdmin(admin.ModelAdmin):
    list_display = ('title', 'slug', 'status')
    search_fields = ['title']
    list_filter = ('status',)
    prepopulated_fields = {'slug': ('title',)}
# Use it like this:
if settings.DEBUG:
    # do something specific for development
    pass
# Get 'MY_CUSTOM_SETTING' from settings.py, or use 'default_value' if it's missing
my_setting = getattr(settings, 'MY_CUSTOM_SETTING', 'default_value')



