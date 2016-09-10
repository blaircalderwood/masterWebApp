from __future__ import division
import numpy as np
from scipy import sparse, io
import pymysql
import backend.flickr_data.flickr_api as fa
from backend.context_retrieval import location
from backend.context_retrieval.general_functions import binary_search
from multiprocessing import Pool, cpu_count
from functools import partial
from os import listdir
from os.path import isfile, join
from backend.context_retrieval import sql_extract
from pymysql.err import ProgrammingError

saved_tag_array = []
saved_occurrences = []

conn = None
cur = None

# Can add and remove features from here when they are needed / not needed
# features = ['overall', 'flash', 'device_type', 'num_faces', 'dominant_colour', 'image_orientation']
features = (('overall', 1), ('flash', 3), ('num_faces', 4), ('dominant_colour', 5),
            ('image_orientation', 3), ('continent', 8), ('time_of_day', 6), ('day_of_week', 3), ('season', 6), )
# The number of distinct values that could be held in a feature
# e.g. 'flash' has 3 values- 0 is off, 1 is on and 2 is unknown
max_values = [1, 3, 3, 4, 5, 3]


def open_connection():

    global conn
    global cur

    if conn is None:
        # Connect to the server
        conn = pymysql.connect(host='localhost', port=3306, user='root', passwd='password', db=location.db)
        conn.query('SET GLOBAL connect_timeout=28800')
        cur = conn.cursor()


def close_connection():

    global conn
    global cur

    if cur is not None:
        cur.close()
        cur = None

    if conn is not None:
        conn.close()
        conn = None


# Add one to the occurrence count where two tags co-occur
def add_count(tag, other_tag, tag_array, occurrence_matrix):

    # Search for the index of each tag
    tag_index = binary_search(tag_array, tag)
    other_tag_index = binary_search(tag_array, other_tag)

    # Ensure that both tags were found and add one to the occurrence count
    if tag_index is not -1 and other_tag_index is not -1:

            try:
                occurrence_matrix[tag_index, other_tag_index] += 1
            except IndexError as e:
                print e


# Perform IDF operation on each occurrence
def calculate_idf(tag_array_len, occurrence_array):

    total_occurrences = np.log(tag_array_len / occurrence_array.sum(0))
    return occurrence_array.multiply(sparse.lil_matrix(total_occurrences))


# Count all co-occurrences of given tags
# photo_array is an array of photos that contain details such as device_type and num_faces
# photos_tags is an array of tags associated with each image
def count_cooccurrences(photos_tags, tag_array, occurrence_matrix):

    open_connection()

    # Loop through all photos that contain tags
    for photo_index, tag_set in enumerate(photos_tags):

        # Loop through all tags in this photo
        for tag_index, _ in enumerate(tag_set):

            tag = photos_tags[photo_index][tag_index]

            # Loop through all other tags in the same photo
            for other_tag_index, _ in enumerate(tag_set):

                other_tag = photos_tags[photo_index][other_tag_index]

                # Only add co-occurrence if the tags are not the same
                if tag_index != other_tag_index:
                    # Add one to the co-occurrence count of these two tags
                    # Pass in the feature (e.g. 1 for flash if flash was on)
                    add_count(tag, other_tag, tag_array, occurrence_matrix)

    close_connection()


def create_cooccurrences(photo_array, photos_tags, tag_array, feature):

    ta_len = len(tag_array)

    for feature_value in range(feature[1]):

        # A matrix for each feature value is created and then saved separately
        # so not all matrices are kept in memory at once
        matrix = sparse.lil_matrix((ta_len, ta_len), dtype=np.float16)
        feature_tags = []

        # If the feature is overall then take all photos into account
        if feature[0] == 'overall':
            feature_tags = photos_tags

        else:
            for photo, tags in zip(photo_array, photos_tags):
                if photo[feature[0]] == feature_value:
                    feature_tags.append(tags)

        count_cooccurrences(feature_tags, tag_array, matrix)
        calculate_idf(ta_len, matrix)

        io.mmwrite("arrays/" + feature[0] + str(feature_value) + ".mtx", matrix)

        print feature[0], feature_value, "matrix constructed"


# Create tag co-occurrence matrices with the given photos and tags
def create(photo_array, photos_tags, tag_array):

    # Utilise multithreading by dividing features up to be handled by each of the CPU's cores
    pool = Pool(cpu_count())
    partial_func = partial(create_cooccurrences, photo_array, photos_tags, tag_array)
    pool.map(partial_func, features)

    return tag_array


# Save the co-occurrence matrix and tag arrays as global variables
def save_arrays(occurrence_array, tag_array):
    global saved_occurrences
    global saved_tag_array
    saved_occurrences = occurrence_array
    saved_tag_array = tag_array


# Save the co-occurrence matrix and tag arrays to a npy file (faster than saving to CSV)
def save_as_file(occurrence_matrices):
    np.savez_compressed("cooccurrence_matrix", occurrence_matrices)

    for feat_index, feature in enumerate(features):
        for feat_val in range(feature[1]):
            io.mmwrite("arrays/" + feature[0] + str(feat_val) + ".mtx", occurrence_matrices[feat_index][feat_val])


def load_feature(feature):

    m = []

    for feature_value in range(feature[1]):
        m.append(io.mmread("arrays/" + feature[0] + str(feature_value) + ".mtx").tolil())
        print feature[0], feature_value, "matrix loaded"

    return m


def load_from_file():

    pool = Pool(cpu_count())

    new_matrices = pool.map(load_feature, features)
    pool.join()
    pool.close()

    return new_matrices


# Load the arrays from global variables if available or their corresponding npy files
def load_arrays():
    global saved_tag_array

    if len(saved_tag_array) is 0:
        saved_tag_array = sql_extract.get_tags()

    # TODO: Re-implement retrieving from file if global variables are empty
    return saved_tag_array


# This method was created to convert the sparse matrix files into SQL databases to counteract RAM constraints
def files_to_db():

    open_connection()

    file_array = [f for f in listdir('arrays') if isfile(join('arrays', f))]

    for matrix_name in file_array:
        sql = "CREATE TABLE IF NOT EXISTS features_%s(row_val INT(10), col_val INT(10), cell_data INT(10))" % matrix_name[:-4]
        cur.execute(sql)

    pool = Pool(cpu_count())
    pool.map(f2db, file_array)

    close_connection()


def f2db(filename):

    db_conn = pymysql.connect(host='localhost', port=3306, user='root', passwd='password', db=location.db)
    db_conn.query('SET GLOBAL connect_timeout=28800')
    db_cur = db_conn.cursor()

    matrix_name = filename[:-4]

    matrix = io.mmread("arrays/" + filename)

    for row, col, data in zip(matrix.row, matrix.col, matrix.data):
        sql = "INSERT INTO features_%s (row_val, col_val, cell_data) VALUES(%s, %s, %s)" % (matrix_name, row, col, data)
        db_cur.execute(sql)
        db_conn.commit()

    print matrix_name, "saved"

    db_cur.close()
    db_conn.close()


def get_row(feature, feature_value, row_num, tag_array_len=None):

    open_connection()

    table_name = "features_" + feature[0] + str(feature_value)

    # Only get top 500 results (increases efficiency greatly while not having a large affect on recommendations)
    sql = "SELECT col_val, cell_data FROM %s WHERE row_val = %s ORDER BY cell_data DESC LIMIT 500" % (table_name,
                                                                                                      row_num)

    try:
        cur.execute(sql)
    except ProgrammingError:
        print sql
        return sparse.lil_matrix((1, tag_array_len))

    if tag_array_len:
        matrix = sparse.lil_matrix((1, tag_array_len), dtype=np.float16)

        for row in cur:
            # Set the row_val cell of the matrix to be equal to the value retrieved from the database
            matrix[0, row[0]] = row[1]

        return matrix

    return cur.fetchall()


def get_all_rows(feature_list, row_num):

    rows = []
    ta_len = len(load_arrays())

    for feature in feature_list:
        for feature_value in range(feature[1]):
            rows.append(get_row(feature, feature_value, row_num, ta_len))

    return rows


# Return the top x amount of recommended tags given a tag
def get_overall_recommended(tag, amount_results, show_result=False):

    # Load the arrays from the global variables or from files
    tag_array = load_arrays()

    # Look for the tag in the array
    tag_index = binary_search(tag_array, tag)

    ranked_results = get_row(features[0], 0, tag_index)[:amount_results]

    if show_result:
        # Return the tags and their respective occurrence values
        ranked_list = [[i[0], tag_array[int(i[0])]] for i in ranked_results]
    else:
        # Return just the tags
        ranked_list = [tag_array[int(i[0])] for i in ranked_results]

    return ranked_list


def rank_results(amount_results, row_array, amount_tags):

    # Create an array filled with negative 1s (lower than lowest possible value in occurrence array)
    # index 0 is the value, index 1 is the tag array index
    chosen_values = np.negative(np.ones([amount_results, 2]))

    # Loop through all tags to search for highest occurring ones
    for other_tag_index in range(amount_tags):

        # Check if the current tag value is higher than the lowest value found in the current highest vals list
        if row_array[0, other_tag_index] > chosen_values[amount_results - 1][0] and \
                        saved_tag_array[other_tag_index] != '~~~api~~~':

            # If it is then replace the lowest value and then sort the new highest list by values
            # This is done to ensure that the lowest value in this list is always at the end of it
            chosen_values[amount_results - 1] = [int(row_array[0, other_tag_index]),
                                                 int(other_tag_index)]
            chosen_values[::-1].sort(0)

    return chosen_values


def novel_sys_recommendations(photo, tag, amount_results, show_result=False, tags="", loc_matrix=None, time_matrix=None):

    recommended = get_combined_recommended(photo, tag, amount_results, features, True, True, tags, loc_matrix,
                                           time_matrix)

    if recommended[0][0] > 0:

        if show_result:
            # Return the tags and their respective occurrence values
            recommended = [[i[0], i[1]] for i in recommended]
        else:
            # Return just the tags
            recommended = [i[1] for i in recommended]
        return recommended
    else:
        relevant = fa.get_relevant_location(photo['places_id'], amount_results)

        return relevant


def get_phillip_recommended(photo, tag, amount_results, show_result=False):
    phillip_features = (('continent', 8), ('time_of_day', 6), ('day_of_week', 3), ('season', 6))
    return get_combined_recommended(photo, tag, amount_results, phillip_features, show_result)


# Get the novel system's recommendation
def get_combined_recommended(photo, tag, amount_results, feature_list, show_result=False, count_location_time=False,
                             tags="", loc_matrix=None, time_matrix=None):

    def normalise_row(new_row):

        new_row = new_row.tocsr()

        min_row = new_row.min()
        max_row = new_row.max()

        try:
            return (new_row - min_row) / (max_row - min_row)
        except NotImplementedError:
            print "ERROR", min_row, max_row

    # Load the arrays from the global variables or from files
    tag_array = load_arrays()

    # Look for the tag in the array
    tag_index = binary_search(tag_array, tag)

    counter = 0
    ta_len = len(tag_array)

    num_rows = len(feature_list)
    if count_location_time:
        num_rows += 2

    rows_normalised = sparse.csr_matrix((num_rows, ta_len), dtype=np.float32)

    # Set overall value to 0 as this is what the feature value will always be
    photo['overall'] = 0

    for feat_index, feature in enumerate(features):

        if feature in feature_list:
            try:

                feat_val = int(photo[feature[0]])
                try:
                    row = get_row(feature, feat_val, tag_index, ta_len)
                    rows_normalised[counter] = normalise_row(row)

                except IndexError:
                    print "Error", feat_index, feat_val

            except KeyError:
                pass

            counter += 1

    if count_location_time is True:
        loc_matrix = location.request_area_matrix(photo['places_id'], tag_array, tags, tag)
        rows_normalised[counter] = normalise_row(loc_matrix) * 10

        counter += 1

        if photo['postingTime'] is not None:
            time_matrix = location.request_area_matrix(photo['postingTime'], tag_array, tags, tag)
            rows_normalised[counter] = normalise_row(time_matrix) * 10

            counter += 1

    rows_normalised = rows_normalised.sum(axis=0)

    # Average does not need to be taken as division is costly and will not change result
    ranked_results = rank_results(amount_results, rows_normalised, len(tag_array))

    # ranked_results = rank_results(amount_results, rows_normalised, len(tag_array))
    # print "New", ranked_results

    return results(show_result, tag_array, ranked_results)


def location_recommendation(photo, tag, amount_results, show_result=False, tags="", retrieve_matrix=False):
    return location_time_recommendation(photo['places_id'], tag, amount_results, show_result, tags, retrieve_matrix)


def time_recommendation(photo, tag, amount_results, show_result=False, tags="", retrieve_matrix=False):
    return location_time_recommendation(photo['postingTime'], tag, amount_results, show_result, tags, retrieve_matrix)


# This method may return location or time related data but is known as simply 'location' for brevity
def location_time_recommendation(place_or_time, tag, amount_results, show_result=False, tags="", retrieve_matrix=False):

    # Load the arrays from the global variables or from files
    tag_array = load_arrays()

    # Look for the tag in the array
    tag_index = binary_search(tag_array, tag)

    loc_row = location.request_area_matrix(place_or_time, tag_array, tags, tag).toarray()

    ranked_results = rank_results(amount_results, loc_row, len(tag_array))
    if retrieve_matrix is True:
        return results(show_result, tag_array, ranked_results), loc_row
    else:
        return results(show_result, tag_array, ranked_results)


def results(show_result, tag_array, ranked_results):

    if show_result:
        # Return the tags and their respective occurrence values
        loc_values = [[i[0], tag_array[int(i[1])]] for i in ranked_results]
    else:
        # Return just the tags
        loc_values = [tag_array[int(i[1])] for i in ranked_results]

    return loc_values
