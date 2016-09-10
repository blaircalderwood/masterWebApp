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


def save_place(place_or_date, photos_tags):

    open_connection()

    if photos_tags is None:
        return

    photos_tags = json.dumps(photos_tags)

    if isinstance(place_or_date, datetime):
        doy = place_or_date.timetuple().tm_yday

        cur.execute("REPLACE INTO dates (day_of_year, photos_tags) VALUES(%s, %s)", (doy, photos_tags))

    else:
        cur.execute("REPLACE INTO areas (places_id, photos_tags) VALUES(%s, %s)", (place_or_date, photos_tags))

    # Save the new row
    conn.commit()


def get_all_areas(area=True):

    open_connection()

    if area:
        cur.execute("SELECT places_id FROM areas")
    else:
        cur.execute("SELECT day_of_year FROM dates")

    area_array = []

    for area in cur:
        area_array.append(area[0])

    return area_array


def save_tags(photos):

    open_connection()

    if photos is None:
        return

    for photo in photos:

        for tag in photo:

            tag = tag.encode('unicode-escape')

            # Only save tags that are under length 100
            if tag is not "" and 1 < len(tag) < 100:
                cur.execute("REPLACE INTO tags(tag) VALUES(%s)", tag)
                conn.commit()


def save_to_area(place_or_date, photo_tags):

    area_index = -1
    doy = None

    if isinstance(place_or_date, datetime):
        if len(dates_array) > 0:
            doy = place_or_date.timetuple().tm_yday
            area_index = binary_search(dates_array, str(doy))

    else:
        if len(areas_array) > 0:
            area_index = binary_search(areas_array, place_or_date)

    if area_index is -1 and doy is None:
        record = fa.nearby_tags(place_or_date)
        print place_or_date
    else:
        record = json.loads(get_record(place_or_date).decode('utf-8'))

    if record is not None:
        record.append(photo_tags)
    else:
        record = photo_tags

    save_place(place_or_date, record)
    save_tags(record)
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


def request_area_matrix(places_id, tag_array, photo_tags="", tag=''):

    global current_matrix

    if len(current_matrix) > 0 and places_id == current_matrix[0]:
        return current_matrix[1]

    tag_array_len = len(tag_array)

    if tag is not '':
        matrix = sparse.lil_matrix((1, tag_array_len), dtype=np.int8)
    else:
        matrix = sparse.lil_matrix((tag_array_len, tag_array_len), dtype=np.int8)

    if places_id is None:
        return matrix

    try:
        record = json.loads(get_record(places_id).decode('utf-8'))
    except AttributeError:
        return matrix

    # If record cannot be found then inform calling function
    if record is False:
        return False

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

        matrix = add_tags_partial(matrix, record, tag_array, tag)

    else:
        if len(record) > 0:
            matrix = add_tags(matrix, record, tag_array)

    # Assign this matrix to be the current matrix
    # If the next places ID is the same as this one then this matrix is used therefore increasing efficiency
    current_matrix = [places_id, matrix]

    return matrix


def get_record(place_or_date):

    if place_or_date is None:
        return None

    open_connection()

    if isinstance(place_or_date, datetime):
        doy = place_or_date.timetuple().tm_yday

        cur.execute("SELECT photos_tags FROM dates WHERE day_of_year = %s LIMIT 1", doy)

    else:
        cur.execute("SELECT photos_tags FROM areas WHERE places_id = '" + place_or_date + "' LIMIT 1")

    row = False

    if cur is not None:
        for new_row in cur:
            row = new_row[0].decode('utf-8')

    close_connection()

    return row


def save_record(place_or_date, photo_tags):

    open_connection()

    if isinstance(place_or_date, datetime):
        doy = place_or_date.timetuple().tm_yday
        sql = "REPLACE INTO areas(day_of_year, photos_tags) VALUES (%s, %s)" % doy, photo_tags

    else:
        sql = "REPLACE INTO areas(places_id, photos_tags) VALUES (%s, %s)" % place_or_date, photo_tags

    cur.execute(sql)
    conn.commit()
    close_connection()


def add_tags(matrix, photo_tags, tag_array):

    for photo in photo_tags:

        for tag in photo:

            tag_index = binary_search(tag_array, tag)

            for other_tag in photo:

                if tag is not other_tag:
                    other_tag_index = binary_search(tag_array, other_tag)
                    matrix[tag_index, other_tag_index] += 1

    return matrix


def add_tags_partial(matrix, photo_tags, tag_array, tag):

    for photo in photo_tags:

        for other_tag in photo:

            if tag is not other_tag:
                other_tag_index = binary_search(tag_array, other_tag)
                matrix[0, other_tag_index] += 1

    return matrix

open_connection()
areas_array = get_all_areas()
dates_array = get_all_areas(False)


def get_top_tags(place_or_date, tag_array):

    # Remove all values that contain '~~~api~~~' (this is a bug)
    api_col = 369973

    matrix = request_area_matrix(place_or_date, tag_array)
    matrix[api_col, :] = 0
    matrix[:, api_col] = 0

    matrix = matrix.tocoo()

    try:
        mx = matrix.data.argmax()

        top_col = matrix.col[mx]
        top_row = matrix.row[mx]

        return tag_array[top_col], tag_array[top_row]

    except ValueError:
        return "No tags found"