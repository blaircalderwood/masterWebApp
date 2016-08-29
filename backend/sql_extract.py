import math
import sys

import numpy as np
import pymysql

import countries
import datetime_functions as dtf
import location
from context_retrieval import image_processing as ip
from flickr_data import flickr_api
from noise import remove_noise

reload(sys)
sys.setdefaultencoding('utf-8')

db = location.db

# Connect to the mysql server
conn = pymysql.connect(host='localhost', port=3306, user='root', passwd='password', db=db)

# Set the connection timeout to be very high as the database may need to be open for a long time
conn.query('SET GLOBAL connect_timeout=28800')
cur = conn.cursor()


def open_connection():

    global conn
    global cur

    # Connect to the mysql server
    conn = pymysql.connect(host='localhost', port=3306, user='root', passwd='password', db=db)

    # Set the connection timeout to be very high as the database may need to be open for a long time
    conn.query('SET GLOBAL connect_timeout=28800')
    cur = conn.cursor()


def close_connection():

    global conn
    global cur
    cur.close()
    cur = None
    conn.close()
    conn = None


# Get all information for the given photo from the mysql database
def get_photo_info(img):

    # Retrieve all information for given photo
    cur.execute("SELECT id, owner_id, postingTime, lat, lon, country FROM flickraia_photos WHERE id = " +
                img[1] + " LIMIT 1")

    # Set titles to be the header for each column (e.g. id, number_faces etc.)
    titles = cur.description

    # Will only iterate once - this is a check to see if the photo has been found
    # Len does not work will data retrieved in this way which is why a for loop has been used
    for photo in cur:
        new_photo = photo_object(titles, photo)
        return add_context(new_photo, img[0])

    # TODO: may need to close connection
    # If photo not found tell the calling method
    return False


def save_dates(photo):
    photo['postingTime'] = flickr_api.get_posting_time(photo['id'])
    if photo['postingTime'] is not None:
        save_photo(photo, 'flickrptr_photos_info')


# Collect and collate all data corresponding to features e.g. num_faces, device_type
def add_context(new_photo, img):

    # Set all fields to data returned from various functions
    d = new_photo['postingTime']

    if d is not None:
        new_photo['time_of_day'] = dtf.time_of_day(d)
        new_photo['season'] = dtf.time_of_year(d)
        new_photo['day_of_week'] = dtf.day_of_week(d)

    new_photo['num_faces'] = ip.get_faces(img)
    new_photo['dominant_colour'] = ip.get_dominant_colour(img)
    new_photo['image_orientation'] = ip.get_image_orientation(img)

    new_photo['country'] = countries.get_country_index(new_photo['country'])
    new_photo['continent'] = countries.find_continent(new_photo['country'])
    new_photo['places_id'] = flickr_api.get_place(new_photo['lat'], new_photo['lon'])

    # Not needed
    # del new_photo['city']

    new_photo['amount_comments'], new_photo['amount_views'] = flickr_api.get_comments_views(new_photo['id'])
    new_photo['flash'], new_photo['device_type'] = flickr_api.get_exif(new_photo['id'])

    # Return the object with the collected features included
    return new_photo


# Get tags from photo
def get_photo_tags(photo_id):

    tags = []

    # Get all tags for given photo ID
    cur.execute("SELECT tag FROM flickrptr_photos_tags WHERE photoID = " + str(photo_id))

    # Append each tag to a tag array
    for tag in cur:
        tags.append(tag[0].encode('string-escape'))

    if tags is []:
        tags = flickr_api.get_tags(photo_id)
        print "Tags retrieved"
        save_photo(tags, "flickrptr_photos_tags")

    # Remove noisey tags
    # TODO: adding tags to array simply to remove them again seems redundant - fix?
    tags = remove_noise(tags)

    # Return a numpy array of tags
    return tags


# Save the given photo object (including data on features) in a new mysql database
def save_photo(obj, table):

    if obj is not False:

        keys = ""
        values = ""

        # Collect all keys (e.g. "num_faces") and values (e.g. 2) from photo object and append to corresponding strings
        for item in obj:
            keys += item + ", "

            values += "'" + str(obj[item]).encode('string-escape') + "', "

        # Remove the trailing comma from each string
        keys = keys[:-2]
        values = values[:-2]

        sql = "REPLACE INTO %s (%s) VALUES(%s)"

        sql = sql % (table, keys, values)
        # Place the new data into the database using the two aforementioned strings
        cur.execute(sql)

        # Save the new row
        conn.commit()


def switch_continent():
    open_connection()

    photos = get_photo_data()
    continents = ['Europe', 'Africa', 'South America', 'North America', 'Asia', 'Oceania', 'Antarctica']

    for photo in photos:
        photo['continent'] = countries.find_continent(photo['country'])
        cur.execute("UPDATE flickrptr_photos_info SET continent = %s WHERE id = %s", (photo['continent'], photo['id']))

    conn.commit()


# Create a new dataset based on images from a given directory
def create_data(directory, lower_limit, upper_limit):

    if conn is None:
        open_connection()

    # Get all previously created data
    photo_array = get_photo_data(upper_limit)
    photos_tags = [get_photo_tags(photo['id']) for photo in photo_array]
    pa_len = len(photo_array)

    # Check if the length of the photo array is bigger than the upper limit
    # If it is then no work needs to be done here as all relevant photos have been processed
    if pa_len < upper_limit:

        # Only need to process data that is found between lower and upper limits and has not already been processed
        lower_limit = max(lower_limit, pa_len)

        # Retrieve Open CV ready images from the directory taking account of given file limit and offset
        # This runs through files even if they are already in the database
        photo_info_array = ip.images_from_directory(directory, lower_limit, upper_limit)

        photos_tags = []

        # Loop through each photo in the aforementioned array
        # Only loop through data that has not yet been created

        for image in photo_info_array[:pa_len]:

            # Get the information related to this photo and its features
            new_photo = get_photo_info(image)

            # Ensure that data was properly retrieved for photo
            if new_photo is False:

                # Many of the images in the provided folder did not relate to any rows in the database
                # (only 14 in first 40 images were found before this code was written to fix this)
                info = flickr_api.missing_flickr_info(image[1])

                if info is False:
                    # Skip this loop iteration as the Flickr photo cannot be found (may have been deleted by the user)
                    continue

                print info

                # Get the information related to this photo and its features
                new_photo = add_context(info, image[0])

                # Save the new photo - processing (i.e. obtaining features) of an image only has to take place once
                save_photo(new_photo, "flickrptr_photos_info")

            # Append the information on the photo and its tags to the corresponding arrays
            photo_array.append(new_photo)
            tags = get_photo_tags(image[1])
            photos_tags.append(tags)

            # Add any new tags to the tag array
            for tag in tags:
                if len(tag) < 50:
                    cur.execute("REPLACE INTO tags(tag) VALUES(%s)", tag)

            conn.commit()

    close_connection()

    # Return the collected photos and their corresponding tags
    return np.array(photo_array), np.array(photos_tags)


def get_photo_data(limit=0):

    open_connection()

    if limit is not 0:
        cur.execute("SELECT * FROM flickrptr_photos_info LIMIT %s", limit)
    else:
        cur.execute("SELECT * FROM flickrptr_photos_info")

    desc = cur.description
    objs = []

    for row in cur:
        obj = photo_object(desc, row)
        objs.append(obj)

    return objs


def get_tags():

    cur.execute("SELECT * FROM tags")

    tag_array = []

    for tag in cur:
        tag_array.append(tag[0])

    return tag_array


# Create a dict object based on a given photo and data retrieved from database (e.g. id will become photo['id'])
def photo_object(titles, photo):

    new_photo = {}

    # Loop through all columns in database row and add to dict
    for index, item in enumerate(photo):
        new_photo[str(titles[index][0])] = item

    return new_photo


# Set directory to an image folder to create new SQL records based on those images
# If no directory is set then method will gather preprocessed data which already contains feature information
def get_data(db_limit=0, percentage_test=0, directory=""):

    # Split data up into training and test sets based on percentage (float between 0 and 1)
    if 0 < percentage_test < 1:

        test_amount = int(math.floor(db_limit * percentage_test))
        training_amount = db_limit - test_amount

        # Get data based on the given image directory and save it in the preprocessed database
        training_photos, training_tags = create_data(directory, training_amount)

        # Get data for testing
        test_photos, test_tags = create_data(directory, test_amount, training_amount)

        # Return data corresponding to both the test set and the training set
        return training_photos, training_tags, test_photos, test_tags

    else:

        # Get data based on the given image directory and save it in the preprocessed database
        training_photos, training_tags = create_data(directory, db_limit)

        # Return data corresponding to both the test set and the training set
        return training_photos, training_tags


# Build an array containing all tags found in given dataset
def build_tag_array(sample):

    # TODO: is using sample_tags necessary? flickrptr_tags never seems to be used
    if sample:
        cur.execute("SELECT tag FROM sample_tags")
    else:
        cur.execute("SELECT tag FROM flickrptr_tags")

    tag_array = []

    # Loop through each tag found in database and append it to new array
    for tag in cur:
        tag_array.append(tag[0])

    print "Co-occurrence created"

    # Return the new tags
    return tag_array


def get_row(table, id_name, id_value):

    cur.execute("SELECT * FROM " + table + " WHERE " + id_name + " = " + id_value + " LIMIT 1")

    # Will only execute once and if the record has been found
    for row in cur:
        new_photo = {}

        # Loop through the column headings and fields and create a new photo object for the current row
        for key, field in zip(cur.description, row):
            new_photo[key[0]] = field

        return new_photo

    # Inform the calling function that the row cannot be found
    return False
