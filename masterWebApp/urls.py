from masterWebApp import views
from django.conf.urls import url, patterns
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.conf.urls import include

urlpatterns = patterns('',
                       url(r'^admin/', admin.site.urls),
                       url(r'^$', views.main_page, name='index'),
                       url(r'^evaluation/', include('evaluation.urls')),
                       ) + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)