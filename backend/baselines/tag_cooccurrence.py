import numpy as np
from backend.general_functions import binary_search
from scipy import sparse, io
from backend import location
import backend.flickr_data.flickr_api as fa

saved_tag_array = []
saved_occurrences = []

# Can add and remove features from here when they are needed / not needed
# features = ['overall', 'flash', 'device_type', 'num_faces', 'dominant_colour', 'image_orientation']
features = (('overall', 1), ('flash', 3), ('num_faces', 4), ('dominant_colour', 5),
            ('image_orientation', 3), ('continent', 8), ('time_of_day', 6), ('day_of_week', 3), ('season', 6), )
# The number of distinct values that could be held in a feature
# e.g. 'flash' has 3 values- 0 is off, 1 is on and 2 is unknown
max_values = [1, 3, 3, 4, 5, 3]


# Add one to the occurrence count where two tags co-occur
def add_count(tag, other_tag, tag_array, photo, occurrence_matrices):

    # Search for the index of each tag
    tag_index = binary_search(tag_array, tag)
    other_tag_index = binary_search(tag_array, other_tag)

    # Ensure that both tags were found and add one to the occurrence count
    if tag_index is not -1 and other_tag_index is not -1:
        occurrence_matrices[0][0][tag_index, other_tag_index] += 1

        # Remove normal tag occurrence temporarily
        f = features[1:]

        for index, feature_array in enumerate(occurrence_matrices[1:]):
            feature_value = int(photo[f[index][0]])

            try:
                feature_array[feature_value][tag_index, other_tag_index] += 1
            except IndexError:
                print features[index], feature_value


# Perform IDF operation on each occurrence
def calculate_idf(tag_array_len, occurrence_array):

    total_occurrences = np.log(tag_array_len / occurrence_array.sum(0))
    return occurrence_array.multiply(sparse.lil_matrix(total_occurrences))


# Count all co-occurrences of given tags
# photo_array is an array of photos that contain details such as device_type and num_faces
# photos_tags is an array of tags associated with each image
def count_cooccurrences(photos_tags, tag_array, photo_array, occurrence_matrices):

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
                    add_count(tag, other_tag, tag_array, photo_array[photo_index], occurrence_matrices)


# Create tag co-occurrence matrices with the given photos and tags
def create(photo_array, photos_tags, tag_array):

    occurrence_matrices = []
    ta_len = len(tag_array)

    for index, feature in enumerate(features):
        sparse_matrices = []
        for mv in range(feature[1]):
            sparse_matrices.append(sparse.lil_matrix((ta_len, ta_len), dtype=np.float16))

        occurrence_matrices.append(sparse_matrices)

    count_cooccurrences(photos_tags, tag_array, photo_array, occurrence_matrices)

    # Calculate IDF values
    tag_array_len = len(tag_array)
    occurrence_matrices[0][0] = calculate_idf(tag_array_len, occurrence_matrices[0][0])
    print occurrence_matrices[0][0].max()

    for feature, f in enumerate(features):
        for value in range(f[1]):
            occurrence_matrices[feature][value] = calculate_idf(tag_array_len, occurrence_matrices[feature][value])

    save_arrays(occurrence_matrices, tag_array)
    save_as_file(occurrence_matrices)

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


def load_from_file():

    new_matrices = []

    for feat_index, feature in enumerate(features):
        m = []

        for feat_val in range(feature[1]):
            m.append(io.mmread("arrays/" + feature[0] + str(feat_val) + ".mtx").tolil())

        new_matrices.append(m)

    return new_matrices


# Load the arrays from global variables if available or their corresponding npy files
def load_arrays():
    global saved_tag_array
    global saved_occurrences

    # TODO: Re-implement retrieving from file if global variables are empty
    return saved_tag_array, saved_occurrences


# Return the top x amount of recommended tags given a tag
def get_overall_recommended(tag, amount_results, show_result=False):
    # Load the arrays from the global variables or from files
    tag_array, occurrence_array = load_arrays()

    # Look for the tag in the array
    tag_index = binary_search(tag_array, tag)
    tag_row = occurrence_array[0][0].getrow(tag_index).toarray()

    # matrix_to_spreadsheet(tag_array, occurrence_array[feature_index][feature_value], "results/ssheet_overall.csv")

    ranked_results = rank_results(amount_results, tag_row, len(tag_array))

    if show_result:
        # Return the tags and their respective occurrence values
        ranked_list = [[i[0], tag_array[int(i[1])]] for i in ranked_results]
    else:
        # Return just the tags
        ranked_list = [tag_array[int(i[1])] for i in ranked_results]

    return ranked_list


def rank_results(amount_results, row_array, amount_tags):

    # Create an array filled with negative 1s (lower than lowest possible value in occurrence array)
    # index 0 is the value, index 1 is the tag array index
    chosen_values = np.negative(np.ones([amount_results, 2]))

    # Loop through all tags to search for highest occurring ones
    for other_tag_index in range(amount_tags):

        # Check if the current tag value is higher than the lowest value found in the current highest vals list
        if row_array[0, other_tag_index] > chosen_values[amount_results - 1][0]:
            # If it is then replace the lowest value and then sort the new highest list by values
            # This is done to ensure that the lowest value in this list is always at the end of it
            chosen_values[amount_results - 1] = [int(row_array[0, other_tag_index]),
                                                 int(other_tag_index)]
            chosen_values[::-1].sort(0)

    return chosen_values


def novel_sys_recommendations(photo, tag, amount_results, show_result=False, tags=""):

    recommended = get_combined_recommended(photo, tag, amount_results, features, True, True, tags)

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
def get_combined_recommended(photo, tag, amount_results, feature_list, show_result=False, count_location_time=False, tags=""):

    # Load the arrays from the global variables or from files
    tag_array, occurrence_array = load_arrays()

    # Look for the tag in the array
    tag_index = binary_search(tag_array, tag)

    totals = 0
    counter = 0

    # Set overall value to 0 as this is what the feature value will always be
    photo['overall'] = 0

    for feat_index, feature in enumerate(features):

        if feature in feature_list:
            feat_val = int(photo[feature[0]])
            row = occurrence_array[feat_index][feat_val].getrow(tag_index).toarray()
            totals = np.add(totals, row)
            counter += 1

    if count_location_time:
        location_matrix = location.request_area_matrix(photo['places_id'], tag_array, tags)
        loc_row = location_matrix.getrow(tag_index).toarray()

        totals = np.add(totals, loc_row)
        counter += 1

        if photo['postingTime'] is not None:
            time_matrix = location.request_area_matrix(photo['postingTime'], tag_array, tags)
            time_row = time_matrix.getrow(tag_index).toarray()

            totals = np.add(totals, time_row)
            counter += 1

    average = totals / counter

    ranked_results = rank_results(amount_results, average, len(tag_array))

    return results(show_result, tag_array, ranked_results)


def location_recommendation(photo, tag, amount_results, show_result=False, tags=""):
    return location_time_recommendation(photo['places_id'], tag, amount_results, show_result, tags)


def time_recommendation(photo, tag, amount_results, show_result=False, tags=""):
    return location_time_recommendation(photo['postingTime'], tag, amount_results, show_result, tags)


def location_time_recommendation(place_or_time, tag, amount_results, show_result=False, tags=""):

    # Load the arrays from the global variables or from files
    tag_array, occurrence_array = load_arrays()

    # Look for the tag in the array
    tag_index = binary_search(tag_array, tag)

    location_matrix = location.request_area_matrix(place_or_time, tag_array, tags)
    loc_row = location_matrix.getrow(tag_index).toarray()

    ranked_results = rank_results(amount_results, loc_row, len(tag_array))
    return results(show_result, tag_array, ranked_results)


def results(show_result, tag_array, ranked_results):

    if show_result:
        # Return the tags and their respective occurrence values
        loc_values = [[i[0], tag_array[int(i[1])]] for i in ranked_results]
    else:
        # Return just the tags
        loc_values = [tag_array[int(i[1])] for i in ranked_results]

    return loc_values


# Adds a new tag to the tag array and increases all matrices in size
def add_new_tag(tag):

    tag_array, occurrence_matrices = load_arrays()

    # If the tag is already in the tag array then nothing needs to be done
    if tag not in tag_array:

        # Add tag to tag array
        tag_array.append(tag)

        # Get the shape of an established co-occurrence matrix (they're all the same size)
        shape = occurrence_matrices[0][0].shape

        # Loop through each co-occurrence matrix and increase the size to allow for the new tag (add 1 row 1 column)
        for feature in occurrence_matrices:
            for i, matrix in enumerate(feature):

                new_row = sparse.lil_matrix((shape[0], 1))
                new_matrix = sparse.hstack([matrix, new_row])

                new_col = sparse.lil_matrix((1, shape[0] + 1))
                feature[i] = sparse.vstack([new_matrix, new_col])

    save_arrays(occurrence_matrices, tag_array)
