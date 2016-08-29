import flickrapi
import json
from math import floor
import numpy as np
from datetime import datetime
from backend import countries

api_key = u'267fe530e588c482dfdad60a0ea85955'
api_secret = u'05307043c90701cf'
flickr = flickrapi.FlickrAPI(api_key, api_secret, format='json')

# camera_brands = np.load("flickr_data/camera_brands.npy")
# camera_models = np.load("flickr_data/camera_models.npy")


# Get the exif data (camera name, flash etc) and return relevant data
def get_exif(photo_id):

    # Get and parse exif data retrieved from Flickr
    exif = flickr.photos.getExif(photo_id=photo_id)
    exif = json.loads(exif.decode('utf-8'))

    # If there was no exif data returned then inform calling method that flash and device name is unknown
    if 'photo' not in exif:
        return 2, 2

    exif = exif['photo']['exif']

    # For flash 0 is off, 1 is on and 2 is unknown
    flash = 2

    # For device type 0 is camera, 1 is mobile phone and 2 is unknown
    device = 2

    # Loop through all exif data and look for flash and camera type
    for row in exif:

        # NOTE: Is this line needed?
        if "label" in row:
            if row['label'] == "Flash":
                if "off" in row['raw']['_content'].lower():
                    flash = 0
                else:
                    flash = 1

    return flash, device


# Get the amount of comments and views on a photo and return whether the amount is low, medium or high
# 0 is low, 1 is average, 2 is high and 3 is unknown
# TODO: Change bins so they hold relatively equal amount each
def get_comments_views(photo_id):

    # Determine the thresholds to use for comments/views (i.e. to split them into low, medium and high)
    def determine_threshold(number, lower, upper):

        # Check which thresholds the number of comments / views lies within and place in respective bin
        if number <= lower:
            return 0
        elif lower < number < upper:
            return 1
        else:
            return 2

    # Thresholds were determined by running set_thresholds on the first 1000 photos in dataset
    views_lower = 1804
    views_upper = 9157
    comments_lower = 37
    comments_upper = 100

    # Retrieve and parse the number of comments / views from Flickr
    info = flickr.photos.getInfo(photo_id=photo_id)
    info = json.loads(info.decode('utf-8'))

    # Check that data was correctly received from Flickr
    if 'photo' in info:
        info = info['photo']
        comments = int(info['comments']['_content'])
        views = int(info['views'])

        # Determine whether number of comments is low, medium or high compared to other Flickr comments
        comments = determine_threshold(comments, comments_lower, comments_upper)
        # Determine whether number of views is low, medium or high compared to other Flickr views
        views = determine_threshold(views, views_lower, views_upper)

        return comments, views

    # If the data cannot be accessed inform the calling method of this
    print "Cannot access photo info"
    return 3, 3


# This only needs to be executed once
# When given a sample number of images the method determines thresholds for high/medium/low amount of comments/views
# The output will then be hardcoded as variables in the amount_comments_views method
def set_thresholds(photo_array):

    # Get the number of comments and views for a given photo
    def amount_comments_views(photo_id):

        # Get the number of comments and views from Flickr
        info = flickr.photos.getInfo(photo_id=photo_id)
        info = json.loads(info.decode('utf-8'))

        # Check the correct data was returned
        if 'photo' in info:
            info = info['photo']

            # Retrieve and return comments and views
            amount_comments = int(info['comments']['_content'])
            amount_views = int(info['views'])
            return amount_comments, amount_views
        print "Cannot access photo info"
        return 0, 0

    comments_list = []
    views_list = []

    # Loop through each photo in the given array
    for photo in photo_array:

        # Get the amount of comments and views
        comments, views = amount_comments_views(photo['id'])

        # Add the comments and views to respective arrays
        if comments > 0:
            comments_list.append(comments)
        if views > 0:
            views_list.append(views)

    # Sort the comments and views in numerical order
    comments_list.sort()
    views_list.sort()

    # Split up array into thirds to retrieved lower threshold (last item in first third)
    # and upper (first item in last third) anything under lower threshold is deemed low etc.
    length = len(photo_array)
    comments_upper = comments_list[int(floor(length * 0.66))]
    comments_lower = comments_list[int(floor(length * 0.33))]

    views_upper = views_list[int(floor(length * 0.66))]
    views_lower = views_list[int(floor(length * 0.33))]

    # Print the thresholds so they can be hardcoded into get_comments_views method
    print "views_lower = " + str(views_lower)
    print "views_upper = " + str(views_upper)

    print "comments_lower = " + str(comments_lower)
    print "comments_upper = " + str(comments_upper)


# Test the thresholds by getting amount of low/medium/high comments/views
# Should print similar numbers for low/medium/high bin
def test_thresholds(photo_array):

    low_comments = 0
    average_comments = 0
    high_comments = 0

    low_views = 0
    average_views = 0
    high_views = 0

    # Loop through all photos in array and determine which bin the commments/views go in
    for photo in photo_array:
        comments, views = get_comments_views(photo['id'])

        if comments == 0:
            low_comments += 1
        elif comments == 1:
            average_comments += 1
        else:
            high_comments += 1

        if views == 0:
            low_views += 1
        elif views == 1:
            average_views += 1
        else:
            high_views += 1

    # Print the results - all bins should be relatively equal in size
    print low_comments, average_comments, high_comments
    print low_views, average_views, high_views


def get_place(lat, lng, get_country_continent=False):

    # Get the place ID
    data = flickr.places.findByLatLon(lat=lat, lon=lng, accuracy=11)
    data = json.loads(data.decode('utf-8'))

    # Get the place ID of the city in which this place resides
    try:
        place = data['places']['place'][0]['place_id']

        if get_country_continent:

            data = flickr.places.getinfo(place_id=place)
            country = countries.get_country_index(json.loads(data.decode('utf-8'))['place']['country']['_content'])
            continent = countries.find_continent(country)

            return place, country, continent

    except IndexError:
        return '0'


# TODO: Remove if not needed
def get_city(lat, lng):

    data = get_place(lat, lng)
    city = flickr.places.getInfo(place_id=data)
    city = json.loads(city.decode('utf-8'))
    return city['place']['locality']['place_id']


# Loop through all dates in past three years and retrieve photos from Flickr
def get_tags_date(date):

    epoch_day = 86400

    photo_tags = []
    max_date = date + (epoch_day * 4)

    # Search the Flickr database for real photos (not screenshots - content_type covers this) for this date
    photos = flickr.photos.search(min_taken_date=date, max_taken_date=max_date, sort='date-taken-asc',
                                  content_type=1, media='photos', extras=['tags'], page=1, per_page=50)

    try:
        photos = json.loads(photos.decode('utf-8'))['photos']['photo']
    except KeyError:
        return []

    for photo in photos:

        tags = photo['tags'].split(' ')

        # As we are creating a co-occurrence matrix we have no need for photos with just one tag
        if len(tags) > 1:
            photo_tags.append(tags)

    return photo_tags


# Retrieves a list of photos taken near the given location
def nearby_tags(places_id):

    photo_tags = []

    # Search the Flickr database for real photos (not screenshots - content_type covers this) in this neighbourhood
    photos = flickr.photos.search(place_id=places_id, sort='interestingness-desc', content_type=1, media='photos',
                                  extras=['tags'], page=1, per_page=25)

    # Only look at top x results so tag array doesn't get exponentially large
    try:
        photos = json.loads(photos.decode('utf-8'))['photos']['photo']
    except KeyError:
        return

    for photo in photos:

        tags = photo['tags'].split(' ')

        # As we are creating a co-occurrence matrix we have no need for photos with just one tag
        if len(tags) > 1:
            photo_tags.append(tags)

    return photo_tags


def missing_flickr_info(photo_id):

    info = flickr.photos.getInfo(photo_id=photo_id)
    try:
        info = json.loads(info.decode('utf-8'))['photo']

        photo_info = {'id': photo_id}
        photo_info['owner_id'] = info['owner']['nsid']
        photo_info['postingTime'] = datetime.strptime(info['dates']['taken'], '%Y-%m-%d %H:%M:%S')
        photo_info['postingTime'] = info['dates']['taken']
        photo_info['lat'] = info['location']['latitude']
        photo_info['lon'] = info['location']['longitude']
        photo_info['country'] = info['location']['country']['_content']

        # This field is not needed for our purposes
        # photo_info['test'] = 0

    except KeyError:
        return False

    return photo_info


def get_tags(photo_id):

    tags = []
    tag_data = flickr.tags.getListPhoto(photo_id=photo_id)
    tag_data = json.loads(tag_data.decode('utf-8'))['photo']['tags']['tag']

    for tag in tag_data:
        tags.append(tag['_content'])

    return tags


def get_relevant_location(places_id, amount_results):

    tag_data = flickr.places.tagsForPlace(place_id=places_id)
    try:
        tag_data = json.loads(tag_data.decode('utf-8'))['tags']['tag'][:amount_results]
    except KeyError:
        return []

    array = []

    for tag in tag_data:
        array.append(tag["_content"])

    return array


def get_posting_time(photo_id):

    info = flickr.photos.getInfo(photo_id=photo_id)
    try:
        info = json.loads(info.decode('utf-8'))['photo']['dates']['taken']
        return to_date(info)
    except KeyError:
        return None


def to_date(date):

    # If a string has been passed in then convert it to datetime
    if isinstance(date, basestring):
        date = datetime.strptime(date, '%Y-%m-%d %H:%M:%S')

    return date
