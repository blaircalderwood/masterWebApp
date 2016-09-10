from __future__ import division
from evaluation.models import UserImage
import exifread
import backend.context_retrieval.image_processing as ip
import os
import backend.context_retrieval.datetime_functions as dtf
from random import choice
from PIL import Image
from PIL.ExifTags import TAGS
from backend.flickr_data import flickr_api
from datetime import datetime
import backend.baselines.tag_cooccurrence as tc
from backend.baselines import flickr_reccommended
from backend.context_retrieval.spreadsheetIO import save_results
from evaluation.forms import RatingForm, ImageForm
from evaluation.models import Rating

imgs = []
image_names = []
systems = ['flickr_recommended', 'tag_cooccurrence', 'phillip_system', 'new_sys']


def get_recommendations(system, tag, photo_id=""):

    photo_id = 'media/user_images/' + photo_id
    image_data = ''

    for image in imgs:
        if image['id'] == photo_id:
            image_data = image

    if image_data is not '':

        if system is 'flickr_recommended':
            return flickr_reccommended.get_recommended(tag, 5)
        elif system is 'new_sys':
            return tc.novel_sys_recommendations(image_data, tag, 5)
        elif system is 'tag_cooccurrence':
            return tc.get_overall_recommended(tag, 5)
        elif system is 'phillip_system':
            return tc.get_phillip_recommended(image_data, tag, 5)

    return []


def create_image_data():

    global imgs, image_names
    imgs = []
    image_names = []

    for directory, _, files in os.walk('media/user_images'):
        for img_file in files:

            # Skip all images that don't have correct metadata
            try:
                image = os.path.join(directory, img_file)
                image = ip.read_image(image)

                # OS join isn't working for this line
                img_name = 'media/user_images/' + img_file
                image_names.append(img_name)

                # image_names.append(img_name)
                imgs.append(get_exif(img_name, image))

            except AttributeError or KeyError:
                image = UserImage.objects.filter(img_name=img_file)
                image.delete()


def next_img():

    image, img_name, tag = get_next_image()

    if image is None:
        # All images have been tagged
        return None, None, None, None

    system_choice = choice(systems)
    choice_list = get_recommendations(system_choice, tag, img_name)

    form = RatingForm(choice_list=choice_list)
    form.fields["system_choice"].initial = system_choice

    return form, image, img_name, tag


def get_next_image():

    try:

        image = UserImage.objects.all()[0]

        img = image.img
        img_name = image.img_name
        tag = image.tag
        image.delete()

        return img, img_name, tag

    except IndexError:
        # All images have been tagged so delete them and inform the calling function
        delete_images()
        return None, None, None


def delete_images():

    # Delete all images in media folder (needs to be done so no user info is held)
    for directory, _, files in os.walk('media'):
        for img_file in files:
            os.remove(os.path.join(directory, img_file))


def get_exif(photo_filename, photo_file):

    # These are the numbers that indicate flash has been fired
    # according to http://www.sno.phy.queensu.ca/~phil/exiftool/TagNames/EXIF.html
    flash_on_values = [1, 2, 5, 7, 9, 'd', 'f', 19, '1d', '1f', 41, 45, 47, 49, '4d', '4f', 50, 59, '5d', '5f']

    # From http://www.blog.pythonlibrary.org/2010/03/28/getting-photo-metadata-exif-using-python/
    def get_exif_details(fn):
        ret = {}
        i = Image.open(fn)
        info = i._getexif()

        for tag, value in info.items():
            decoded = TAGS.get(tag, tag)
            ret[decoded] = value

        return ret

    f = get_exif_details(photo_filename)

    photo = {}
    photo['id'] = photo_filename

    photo['num_faces'] = ip.get_faces(photo_file)
    photo['dominant_colour'] = ip.get_dominant_colour(photo_file)
    photo['image_orientation'] = ip.get_image_orientation(photo_file)

    photo['lat'], photo['lon'] = convert_to_degress(f)
    photo['places_id'], photo['country'], photo['continent'] = flickr_api.get_place(photo['lat'], photo['lon'], True)

    d = None

    try:
        photo['postingTime'] = datetime.strptime(f['DateTimeDigitized'], '%Y:%m:%d %H:%S:%f')

        d = photo['postingTime']
    except KeyError:
        pass

    if d is not None:
        photo['time_of_day'] = dtf.time_of_day(d)
        photo['season'] = dtf.time_of_year(d)
        photo['day_of_week'] = dtf.day_of_week(d)

    try:

        # 0 is off, 1 is on
        if f['Flash'] in flash_on_values:
            photo['flash'] = 1
        else:
            photo['flash'] = 0

    except KeyError:
        photo['flash'] = 2

    try:
        # Check if image is vertical and set to 1 if it is
        if f['Orientation'] is 4:
            photo['image_orientation'] = 1
        else:
            photo['image_orientation'] = 0

    except KeyError:
        photo['image_orientation'] = 2

    # Return Exif tags
    return photo


# From http://stackoverflow.com/questions/6460381/translate-exif-dms-to-dd-geolocation-with-python
def convert_to_degress(photo):

    try:
        d = photo['GPSInfo']

        lat = d[2][0][0]/d[2][0][1] + (d[2][1][0] / d[2][1][1])/60 + (d[2][2][0] / d[2][2][1])/3600
        lon = d[4][0][0]/d[2][0][1] + (d[4][1][0] / d[4][1][1])/60 + (d[4][2][0] / d[4][2][1])/3600

        if d[1] == 'S':
            lat *= -1

        if d[3] == 'W':
            lon *= -1

        return lat, lon

    except KeyError:
        # No Lat / Long available
        return 0, 0


def save_ratings():

    ratings = Rating.objects.all()
    fr = {'name': 'flickr_recommended', 'results': []}
    tc = {'name': 'tag_cooccurrence', 'results': []}
    ns = {'name': 'new_sys', 'results': []}
    pr = {'name': 'phillip_system', 'results': []}
    result_systems = [fr, tc, ns, pr]

    for rating in ratings:

        score = [rating.selected_1, rating.selected_2, rating.selected_3, rating.selected_4, rating.selected_5]

        for sys in result_systems:
            if rating.system_choice == sys['name']:
                sys['results'].append(score)

    for sys in result_systems:
        save_results(sys['results'], 'online_results/' + sys['name'] + '.csv')