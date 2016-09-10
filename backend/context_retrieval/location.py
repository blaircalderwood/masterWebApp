from scipy import sparse
import numpy as np
from backend.flickr_data import flickr_api as fa
from general_functions import binary_search
import pymysql
import json
import sys
from datetime import datetime
reload(sys)
sys.setdefaultencoding('utf-8')

# An array of sparse matrices - each matrix pertains to a unique real world area
areas = []
db = 'flickrptr'

conn = None
cur = None

current_matrix = []


def open_connection():

    global conn
    global cur

    if conn is None:
        # Connect to the server
        conn = pymysql.connect(host='localhost', port=3306, user='root', passwd='password', db=db)
        conn.query('SET GLOBAL connect_timeout=28800')
        cur = conn.cursor()


def close_connection():

    global conn
    global cur

    cur.close()
    conn.close()
    cur = None
    conn = None


# Save a given location or date to the database
def save_place(place_or_date, photos_tags):

    open_connection()

    if photos_tags is None:
        return

    # Save the list of tags for each photo into json format so it can be saved into the database
    photos_tags = json.dumps(photos_tags)

    # If a date was given save the tags into the date database
    if isinstance(place_or_date, datetime):
        doy = place_or_date.timetuple().tm_yday

        cur.execute("REPLACE INTO dates (day_of_year, photos_tags) VALUES(%s, %s)", (doy, photos_tags))

    else:
        # If it is a location save it into the areas database
        cur.execute("REPLACE INTO areas (places_id, photos_tags) VALUES(%s, %s)", (place_or_date, photos_tags))

    # Save the new row
    conn.commit()


# Get every area or date in the database
def get_all_areas(area=True):

    open_connection()

    # If the calling function has requested areas return all locations
    if area:
        cur.execute("SELECT places_id FROM areas")

    # Otherwise return all dates
    else:
        cur.execute("SELECT day_of_year FROM dates")

    area_array = []

    for area in cur:
        area_array.append(area[0])

    return area_array


# Save each new tag read in from the Flickr API into the tags database
def save_tags(photos):

    open_connection()

    if photos is None:
        return

    # Loop through each tag in each photo
    for photo in photos:
        for tag in photo:

            # Escape any characters such as '
            tag = tag.encode('unicode-escape')

            # Only save tags that are under length 100
            if tag is not "" and 1 < len(tag) < 100:

                # Save the tags
                cur.execute("REPLACE INTO tags(tag) VALUES(%s)", tag)
                conn.commit()


# Save the given photo's tags into the given location or day of year
def save_to_area(place_or_date, photo_tags):

    area_index = -1
    doy = None

    # Check if the given value is a date
    if isinstance(place_or_date, datetime):
        if len(dates_array) > 0:
            # If it is a date get the day of year and search for this date in the array of all dates
            doy = place_or_date.timetuple().tm_yday
            area_index = binary_search(dates_array, str(doy))

    else:
        # Otherwise it is a location so find it in the locations array
        if len(areas_array) > 0:
            area_index = binary_search(areas_array, place_or_date)

    # If there is no data in the place or date then get some 'starter' data from Flickr
    if area_index is -1 and doy is None:
        record = fa.nearby_tags(place_or_date)
    else:
        # Otherwise decode this data so it can be readily manipulated
        record = json.loads(get_record(place_or_date).decode('utf-8'))


    # Append the new tags to the given photo and tags
    if record is not None:
        record.append(photo_tags)
    else:
        record = photo_tags

    # Save the new tags
    save_place(place_or_date, record)
    save_tags(record)

    # Append the new area or date to its corresponding array
    if doy is None:
        areas_array.append(place_or_date)
    else:
        dates_array.append(doy)

    conn.commit()

    try:
        # Return the new tag array
        return np.array(record)
    except ValueError:
        return


# Given a location or date return either a dynamically created matrix or one row of a dynamically created matrix
def request_area_matrix(places_id, tag_array, photo_tags="", tag=''):

    global current_matrix

    # Check if the matrix in question is the last one to the generated as this is still in memory
    if len(current_matrix) > 0 and places_id == current_matrix[0]:

        # Skip the rest of this method and return this generated matrix
        return current_matrix[1]

    tag_array_len = len(tag_array)

    # If a tag was given then only create a one row sparse matrix
    if tag is not '':
        matrix = sparse.lil_matrix((1, tag_array_len), dtype=np.int8)

    # Otherwise create a full sparse matrix
    else:
        matrix = sparse.lil_matrix((tag_array_len, tag_array_len), dtype=np.int8)

    # Return an empty matrix if the given place or time could not be found
    # this could happen if a picture was taken at sea as no places IDs exist there
    if places_id is None:
        return matrix

    # Get the photos and tags for this location or date from the database
    try:
        record = json.loads(get_record(places_id).decode('utf-8'))
    except AttributeError:
        return matrix

    # If record cannot be found then inform calling function
    if record is False:
        return False

    # Remove any record that matches exactly with the given one
    # This is used as the testing photo may have had data saved to here in the past and so removing it removes bias
    if photo_tags is not "" and photo_tags in record:
        for r in record:
            if r == photo_tags:
                record.remove(r)
                break

    # Remove all photos that don't contain the tag
    # This leads to a partially constructed co-occurrence matrix which increases efficiency
    if tag is not '':
        for r in record:
            if tag not in r:
                record.remove(r)

        # Create a partial matrix of one row
        matrix = add_tags_partial(matrix, record, tag_array, tag)

    else:
        if len(record) > 0:
            # Create a full sparse matrix
            matrix = add_tags(matrix, record, tag_array)

    # Assign this matrix to be the current matrix
    # If the next places ID is the same as this one then this matrix is used therefore increasing efficiency
    current_matrix = [places_id, matrix]

    return matrix


# Get the record of a given place or date from the database
def get_record(place_or_date):

    if place_or_date is None:
        return None

    open_connection()

    # If the given data is a date get the record from the dates database
    if isinstance(place_or_date, datetime):
        doy = place_or_date.timetuple().tm_yday

        cur.execute("SELECT photos_tags FROM dates WHERE day_of_year = %s LIMIT 1", doy)

    # Otherwise get the record from the areas database
    else:
        cur.execute("SELECT photos_tags FROM areas WHERE places_id = '" + place_or_date + "' LIMIT 1")

    row = False

    # Decode the record and place it into an array
    if cur is not None:
        for new_row in cur:
            row = new_row[0].decode('utf-8')

    close_connection()

    return row


# Given a matrix and photos create a full co-occurrence matrix
def add_tags(matrix, photo_tags, tag_array):

    # Loop through all photos in the array
    for photo in photo_tags:

        # Loop through all tags in the photo
        for tag in photo:

            # Get the index of the tag in the tag array
            tag_index = binary_search(tag_array, tag)

            # Loop through all tags in the photo again
            for other_tag in photo:

                # Check the two tags in question are not the same
                if tag is not other_tag:
                    # Get the other tag's index
                    other_tag_index = binary_search(tag_array, other_tag)

                    # Add one to the co-occurrence value in the given matrix
                    matrix[tag_index, other_tag_index] += 1

    return matrix


# Populate a one row matrix with co-occurrences
def add_tags_partial(matrix, photo_tags, tag_array, tag):

    # Loop through all given photos
    for photo in photo_tags:

        # Loop through all other tags
        for other_tag in photo:

            # Check the tag is not the one given by the calling method
            if tag is not other_tag:

                # Get the index of the other tag
                other_tag_index = binary_search(tag_array, other_tag)

                # Add one to the co-occurrence value in the given matrix
                matrix[0, other_tag_index] += 1

    return matrix


# Get the top tags for any place or location (this is not used by the program
# It is used for producing some data seen in thesis
def get_top_tags(place_or_date, tag_array):

    # Remove all values that contain '~~~api~~~' (this is a bug)
    api_col = 369973

    # Get the whole area matrix for this location
    matrix = request_area_matrix(place_or_date, tag_array)

    # Remove the '~~~api~~~' column and row
    matrix[api_col, :] = 0
    matrix[:, api_col] = 0

    # Convert the LIL matrix to COO format in order to find the maximum overall values
    matrix = matrix.tocoo()

    try:

        # Get the maximum value of any cell in the matrix
        mx = matrix.data.argmax()

        # Get the row and column index of this maximum
        top_col = matrix.col[mx]
        top_row = matrix.row[mx]

        # Return the corresponding two tags
        return tag_array[top_col], tag_array[top_row]

    except ValueError:
        return "No tags found"


open_connection()
areas_array = get_all_areas()
dates_array = get_all_areas(False)