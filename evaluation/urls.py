from django.conf.urls import url, patterns
from django.conf import settings
from django.conf.urls.static import static
from evaluation import views

urlpatterns = patterns('',
                       url(r'^$', views.rating_form, name='evaluation'),
                       url(r'^upload_image/$', views.upload_image, name='upload_image'),
                       url(r'^rate_image/$', views.rating_form, name='rate_image')) + \
              static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)