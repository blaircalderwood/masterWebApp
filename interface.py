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


# Return recommendations for a given image and tag
def get_recommendations(system, tag, photo_id=""):

    # Alter the image URL so the image data can be read
    photo_id = 'media/user_images/' + photo_id
    image_data = ''

    # Look for the inputted image in the array of image data
    for image in imgs:
        if image['id'] == photo_id:
            image_data = image

    # If the image data exists
    if image_data is not '':

        # Return the recommendations from the inputted system
        if system is 'flickr_recommended':
            return flickr_reccommended.get_recommended(tag, 5)
        elif system is 'new_sys':
            return tc.novel_sys_recommendations(image_data, tag, 5)
        elif system is 'tag_cooccurrence':
            return tc.get_overall_recommended(tag, 5)
        elif system is 'phillip_system':
            return tc.get_phillip_recommended(image_data, tag, 5)

    return []


# Create image data (such as number of faces, places ID) for each given image
def create_image_data():

    global imgs, image_names
    imgs = []
    image_names = []

    # Loop through all images in the uploaded images folder
    for directory, _, files in os.walk('media/user_images'):
        for img_file in files:

            # Skip all images that don't have correct metadata
            try:

                # Get the full image url
                image = os.path.join(directory, img_file)

                # Read the data from the image and place it into a 2 dimensional array for further processing
                image = ip.read_image(image)

                # OS join isn't working for this line so concatenation is used
                img_name = 'media/user_images/' + img_file
                image_names.append(img_name)

                # Get data for this image such as number of faces
                imgs.append(get_exif(img_name, image))

            # If metadata cannot be found skip this image
            except AttributeError or KeyError:
                image = UserImage.objects.filter(img_name=img_file)
                image.delete()


# Return recommendations for the next image in the list
def next_img():

    # Get the details of the next image
    image, img_name, tag = get_next_image()

    if image is None:
        # All images have been tagged
        return None, None, None, None

    # Choose a random system (one of the three baselines or the novel system) and get recommendations based on this
    system_choice = choice(systems)
    choice_list = get_recommendations(system_choice, tag, img_name)

    # Create a new form and set its hidden data to be the choice of system so it can be saved alongside user input
    form = RatingForm(choice_list=choice_list)
    form.fields["system_choice"].initial = system_choice

    return form, image, img_name, tag


# Attempt to get the next image in the list
def get_next_image():

    try:

        # Get the list of all uploaded images and extract the first instance of an image
        image = UserImage.objects.all()[0]

        # Extract details from this record
        img = image.img
        img_name = image.img_name
        tag = image.tag

        # The record is no longer needed - delete it
        image.delete()

        return img, img_name, tag

    except IndexError:
        # All images have been tagged so delete them and inform the calling function
        delete_images()
        return None, None, None


# Delete all image files from the system
def delete_images():

    # Delete all images in media folder (needs to be done so no user info is held)
    for directory, _, files in os.walk('media'):
        for img_file in files:
            os.remove(os.path.join(directory, img_file))


# Get EXIF data from the image
def get_exif(photo_filename, photo_file):

    # These are the numbers that indicate flash has been fired
    # according to http://www.sno.phy.queensu.ca/~phil/exiftool/TagNames/EXIF.html
    flash_on_values = [1, 2, 5, 7, 9, 'd', 'f', 19, '1d', '1f', 41, 45, 47, 49, '4d', '4f', 50, 59, '5d', '5f']

    # From http://www.blog.pythonlibrary.org/2010/03/28/getting-photo-metadata-exif-using-python/
    def get_exif_details(fn):
        ret = {}

        # Open the image file
        i = Image.open(fn)

        # Get exif data
        info = i._getexif()

        # Add tags to the exif data so each element is labelled (e.g. with 'latitude', 'longitude', 'flash')
        for tag, value in info.items():
            decoded = TAGS.get(tag, tag)
            ret[decoded] = value

        return ret

    f = get_exif_details(photo_filename)

    # Add all appropriate data to the new photo object
    photo = {}
    photo['id'] = photo_filename

    # Get image processing based data
    photo['num_faces'] = ip.get_faces(photo_file)
    photo['dominant_colour'] = ip.get_dominant_colour(photo_file)
    photo['image_orientation'] = ip.get_image_orientation(photo_file)

    # Get location based data
    photo['lat'], photo['lon'] = convert_to_degress(f)
    photo['places_id'], photo['country'], photo['continent'] = flickr_api.get_place(photo['lat'], photo['lon'], True)

    # Set a new variable to None to later check if the date has been correctly loaded
    d = None

    try:
        # Extract the date from the image data
        photo['postingTime'] = datetime.strptime(f['DateTimeDigitized'], '%Y:%m:%d %H:%S:%f')
        d = photo['postingTime']

    except KeyError:
        pass

    # If the date is present (i.e. the exception was not triggered)
    if d is not None:

        # Get the date based details for the image
        photo['time_of_day'] = dtf.time_of_day(d)
        photo['season'] = dtf.time_of_year(d)
        photo['day_of_week'] = dtf.day_of_week(d)

    try:

        # 0 is off, 1 is on
        if f['Flash'] in flash_on_values:
            photo['flash'] = 1
        else:
            photo['flash'] = 0

    # If the flash data cannot be found set it to unknown
    except KeyError:
        photo['flash'] = 2

    # Return Exif tags
    return photo


# Convert GPD coordinates from DMS to DD format
# From http://stackoverflow.com/questions/6460381/translate-exif-dms-to-dd-geolocation-with-python
def convert_to_degress(photo):

    try:
        d = photo['GPSInfo']

        # Read exif data and extract the latitude and longitude
        lat = d[2][0][0]/d[2][0][1] + (d[2][1][0] / d[2][1][1])/60 + (d[2][2][0] / d[2][2][1])/3600
        lon = d[4][0][0]/d[2][0][1] + (d[4][1][0] / d[4][1][1])/60 + (d[4][2][0] / d[4][2][1])/3600

        # If the DMS system indicates it is south invert the latitude
        if d[1] == 'S':
            lat *= -1

        # If the DMS system indicates it is west invert the longitude
        if d[3] == 'W':
            lon *= -1

        return lat, lon

    except KeyError:
        # No Lat / Long available
        return 0, 0


# Save the user ratings to a CSV file for further analysis
def save_ratings():

    # Get all ratings
    ratings = Rating.objects.all()

    # Set up objects to hold each system's ratings
    fr = {'name': 'flickr_recommended', 'results': []}
    tc = {'name': 'tag_cooccurrence', 'results': []}
    ns = {'name': 'new_sys', 'results': []}
    pr = {'name': 'phillip_system', 'results': []}
    result_systems = [fr, tc, ns, pr]

    for rating in ratings:

        # Create an array of the rating of each image (5 recommendations per image)
        score = [rating.selected_1, rating.selected_2, rating.selected_3, rating.selected_4, rating.selected_5]

        # Add this score to the system's object
        for sys in result_systems:
            if rating.system_choice == sys['name']:
                sys['results'].append(score)

    # Save the results to a csv file
    for sys in result_systems:
        save_results(sys['results'], 'online_results/' + sys['name'] + '.csv')