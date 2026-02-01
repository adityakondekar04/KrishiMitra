"""
URL configuration for myproject project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from agrimitra import views as app_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', app_views.home, name='home'),
    path('login/', app_views.login_view, name='login'),
    path('signup/', app_views.signup_view, name='signup'),
    path('dashboard/', app_views.dashboard, name='dashboard'),
    path('logout/', app_views.logout_view, name='logout'),
    path('api/profile/update/', app_views.update_profile_api, name='api_profile_update'),
    path('forum/', app_views.forum, name='forum'),
    path('api/forum/vote/', app_views.forum_vote, name='forum_vote'),
    path('api/forum/comment/', app_views.forum_comment, name='forum_comment'),
    path('api/forum/comment/like/', app_views.forum_comment_like, name='forum_comment_like'),
    path('chatbot/', app_views.chatbot, name='chatbot'),
    path('api/chatbot/ask/', app_views.chatbot_api, name='chatbot_api'),
    path('learning/', app_views.learning, name='learning'),
        path('weather/', app_views.weather_updates, name='weather_updates'),
    path('schemes/', app_views.schemes, name='schemes'),
    path('profile/', app_views.profile_page, name='profile_page'),
    path('settings/', app_views.settings_page, name='settings_page'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
