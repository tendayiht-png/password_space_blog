from django.contrib import admin
from .models import Comment, Post

@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'status', 'created_on')
    prepopulated_fields = {'slug': ('title',)}
    list_filter = ('status', 'created_on')
    search_fields = ('title', 'content')


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('post', 'author', 'approved', 'created_on')
    list_filter = ('approved', 'created_on')
    search_fields = ('body',)



