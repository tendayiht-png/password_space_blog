from django.urls import path

from . import views

urlpatterns = [
    path('', views.PostList.as_view(), name='home'),
    path('post/<slug:slug>/', views.PostDetail.as_view(), name='post_detail'),
    path('ideas/', views.ideas_page, name='ideas_page'),
    path('ideas/<int:pk>/', views.IdeaDetail.as_view(), name='idea_detail'),
    path('ideas/my/', views.my_ideas_page, name='my_ideas_page'),
    path('ideas/unallocated/', views.unallocated_ideas_page, name='unallocated_ideas_page'),
    path('ideas/<int:idea_id>/edit/', views.edit_idea_page, name='edit_idea_page'),
    path('ideas/<int:idea_id>/delete/', views.delete_idea, name='delete_idea'),
    path('about/', views.AboutPageView.as_view(), name='about_page'),
    path('how-to-2fa/', views.HowToPageView.as_view(), name='how_to_page'),
    path('login/', views.LoginPageView.as_view(), name='login_page'),
    path('register/', views.RegisterPageView.as_view(), name='register_page'),
    path('settings/', views.SettingsPageView.as_view(), name='settings_page'),
    path('forgot-password/', views.ForgotPasswordView.as_view(), name='forgot_password_page'),
    path('reset-password/<uidb64>/<token>/', views.ResetPasswordView.as_view(), name='reset_password_page'),
    path('API/login', views.login_api, name='login_api'),
    path('API/register', views.register_api, name='register_api'),
    path('API/delete-account', views.delete_account_api, name='delete_account_api'),
    path('API/password-reset-request', views.password_reset_request_api, name='password_reset_request_api'),
    path('API/password-reset-confirm', views.password_reset_confirm_api, name='password_reset_confirm_api'),
    path('API/token/refresh', views.refresh_token_api, name='refresh_token_api'),
    path('API/logout', views.logout_api, name='logout_api'),
]
