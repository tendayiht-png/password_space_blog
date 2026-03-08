from django.urls import path

from . import views

urlpatterns = [
    path('', views.PostList.as_view(), name='home'),
    path('post/<slug:slug>/', views.PostDetail.as_view(), name='post_detail'),
    path('how-to-2fa/', views.HowToPageView.as_view(), name='how_to_page'),
    path('breach-checklist/', views.ChecklistPageView.as_view(), name='checklist_page'),
]
