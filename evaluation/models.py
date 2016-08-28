from __future__ import unicode_literals

from django.db import models


class Rating(models.Model):

    system_choice = models.CharField(max_length=20, unique=False)

    selected_1 = models.IntegerField(max_length=1, default=0)
    selected_2 = models.IntegerField(max_length=1, default=0)
    selected_3 = models.IntegerField(max_length=1, default=0)
    selected_4 = models.IntegerField(max_length=1, default=0)
    selected_5 = models.IntegerField(max_length=1, default=0)

    def save(self, *args, **kwargs):
        super(Rating, self).save(*args, **kwargs)

    def __unicode__(self):
        return self.system_choice


class UserImage(models.Model):

    img = models.ImageField(upload_to='user_images')

    def save(self, *args, **kwargs):
        super(UserImage, self).save(*args, **kwargs)

    def __unicode__(self):
        return self.img.name
