from django.contrib import admin
from .models import Idea, Post, UserContactProfile

@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'status', 'created_on')
    prepopulated_fields = {'slug': ('title',)}
    list_filter = ('status', 'created_on')
    search_fields = ('title', 'content')


@admin.register(Idea)
class IdeaAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'owner', 'title', 'reviewed', 'created_on')
    list_filter = ('reviewed', 'created_on', 'owner')
    search_fields = ('name', 'email', 'title', 'idea', 'owner__username')


@admin.register(UserContactProfile)
class UserContactProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'telephone', 'updated_on')
    search_fields = ('user__username', 'user__email', 'telephone')



