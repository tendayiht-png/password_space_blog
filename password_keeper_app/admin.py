from django.contrib import admin

# Register your models here.
from .models import Post, Comment
from django_summernote.admin import SummernoteModelAdmin

# Register your models here.
@admin.register()
class PostAdmin(SummernoteModelAdmin):

    list_display = ('title', 'slug', 'status')
    search_fields = ['title']
    list_filter = ('status',)
    prepopulated_fields = {'slug': ('title',)}
    summernote_fields = ('content',)

