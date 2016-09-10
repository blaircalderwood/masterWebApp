from __future__ import division
import random
from copy import copy
import numpy as np
from backend.context_retrieval import sql_extract
import backend.baselines.tag_cooccurrence as tc
from backend.context_retrieval import location
from backend.context_retrieval.spreadsheetIO import save_results
import backend.baselines.flickr_reccommended as fr
from multiprocessing import Pool, cpu_count
from functools import partial

# Set up dictionaries that will contain results of test
flickr_recommended = {'name': 'Flickr Recommended'}
tag_cooccurrence = {'name': 'Tag Co-occurrence'}
phillip_cooccurrence = {'name': 'Phillip\'s Baseline'}
new_sys = {'name': 'New co-occurrence system'}
loc_only = {'name': 'Location'}
time_only = {'name': 'Time'}

systems = [flickr_recommended, tag_cooccurrence, phillip_cooccurrence, new_sys, loc_only, time_only]


# Preprocess the dataset so it does not need to be built each time the system is run
# This method can be performed in chunks by altering the db lower and upper limits
def build_database(directory="", db_limit_lower=0, db_limit_upper=0):

    # Create database records pertaining to the inputted image folder
    # This will return an array of photos with data such as number of faces
    # It will also return an array of tags relating to the aforementioned photos
    photo_array, photos_tags = sql_extract.create_data(directory, db_limit_lower, db_limit_upper)

    photo_array = photo_array[db_limit_lower:]
    photos_tags = photos_tags[db_limit_lower:]

    # Open a connection to the sql database
    location.open_connection()

    # Loop through all photos in array and create database records relating to their location (places ID)
    for photo_index, photo in enumerate(photo_array):
        if photo['places_id'] is not 0:
            # These are put into a separate list as they contain data from outwith the dataset
            # And therefore should not be returned for use in training / testing
            location.save_to_area(photo['places_id'], photos_tags[photo_index])

        if photo['postingTime'] is not None:
            location.save_to_area(photo['postingTime'], photos_tags[photo_index])

    # Close the connection to the sql database
    location.close_connection()

    return photo_array, photos_tags


# Extract all unique tags from the given array and append them to the given tag array
def append_tags(tag_array, array):

    for photo in array:
        for tag in photo:
            if tag not in tag_array:
                tag_array.append(tag)

    return tag_array


# Run the offline test by passing in a preprocessed dataset
def offline_test(limit, training_amount, write_results=False, load_from_file=False):

    # These are split into two methods to save time in testing
    test_photos, test_tags = set_up(limit, training_amount, load_from_file)
    print "Co-Occurrences Created"
    execute_test(test_photos, test_tags, write_results)


# Create occurrence matrices
def set_up(limit, test_amount, load_from_file=False):

    training_amount = limit - test_amount

    # Get the data for the photos (dominant colour etc.) from the MySQL database
    photo_array = sql_extract.get_photo_data(limit)
    photos_tags = [sql_extract.get_photo_tags(photo['id']) for photo in photo_array]
    tag_array = sql_extract.get_tags()

    # Assign all data found before the cut off point (test_amount) to the training set
    training_photos = photo_array[:training_amount]
    training_tags = photos_tags[:training_amount]

    # Assign all data found after the cut off point to the test set
    test_photos = photo_array[training_amount:]
    test_tags = photos_tags[training_amount:]

    # Create an overall co-occurrence matrix and one for each of the features
    # One feature may be used in more than one system and so creating all at the start increases efficiency
    if load_from_file:
        oa = tc.load_from_file()
        tc.save_arrays(oa, tag_array)
    else:
        tc.create(training_photos, training_tags, tag_array)

    # Return Numpy (efficient) arrays
    return np.array(test_photos), np.array(test_tags)


# Run the offline test for the given limit and testing amount (testing amount is the number of photos to run tests on)
def execute_test(limit, test_amount):

    training_amount = limit - test_amount

    # Get the required data from the database
    test_photos = sql_extract.get_photo_data(limit, training_amount)

    # Get the tags for all images retrieved from the database
    test_tags = [sql_extract.get_photo_tags(photo['id']) for photo in test_photos]

    tt_len = len(test_tags)

    # Create empty arrays to hold the test results
    for sys in systems:
        sys['results'] = np.zeros((len(test_photos), 5))

    # Run through each tag in the test tags set by creating several cpu processes to run on separate cores
    # This will split the test photos up into n cores and then assemble the results into one array
    pool = Pool(cpu_count())
    partial_func = partial(get_result, test_photos, test_tags)
    results = pool.map(partial_func, test_tags)

    # Loop through each result retrieved from multiprocessing pool above and add to appropriate system results array
    for result_index, result in enumerate(results):
        for index, sys in enumerate(systems):
            sys['results'][result_index] = result[index]

    # Print the test results on screen
    for index, sys in enumerate(systems):

        # Save the results to a spreadsheet
        save_results(sys['results'], 'results/systemResults/' + sys['name'] + '.csv')

        # Precision at one is the percentage of runs where top tag recommended is relevant (McParlane, 2014)
        pa1 = np.sum(sys['results'], axis=0)[0]

        sa5 = 0
        rows = np.sum(sys['results'], axis=1)

        # Precision at five is the percentage of relevant tags amongst the five recommended ones
        pa5 = (np.sum(rows) / 5)

        for row in rows:

            # Success at five is the percentage of runs where at least one relevant tag is found
            # amongst the recommended ones
            if row > 0:
                sa5 += 1

        # Print the results on screen
        print_results(sys, test_tags, pa1, pa5, sa5)


# Get recommended tags for the given photo and check if they match against the ground truth
def get_result(test_photos, test_tags, photo_tags):

    # Skip any photos that do not have a sufficient amount of tags
    if len(photo_tags) < 6:
        return

    # Get the index of this photo in the array
    test_index = test_tags.index(photo_tags)

    # Copy the tags as the original will need to be retained
    tags = copy(photo_tags)

    # A random tag from the photo tag list will be submitted to each baseline
    tag = random.choice(tags)

    # All others will be compared against the baseline's recommendations
    tags.remove(tag)

    # Get the recommended tags from each baseline
    fr_rec = fr.get_recommended(tag, 5)
    tc_rec = tc.get_overall_recommended(tag, 5)
    pc_rec = tc.get_phillip_recommended(test_photos[test_index], tag, 5)

    # Get recommendations from the two novel features
    lc_rec = tc.location_recommendation(test_photos[test_index], tag, 5, False, photo_tags)
    t_rec = tc.time_recommendation(test_photos[test_index], tag, 5, False, photo_tags)
    ns_rec = tc.novel_sys_recommendations(test_photos[test_index], tag, 5, False, photo_tags)

    # Create an array of all systems and their recommendations
    rec_tags = [fr_rec, tc_rec, pc_rec, lc_rec, t_rec, ns_rec]
    res = []

    # Loop through each tag recommendation system and gather results for precision at one etc.
    for sys, recommended_tags in zip(systems, rec_tags):

        results = np.zeros(5)

        # Loop through each of the five recommended tags
        for recommended_tag_index in range(4):

            # If the tag is in the ground truth then save it as 1
            try:
                if recommended_tags[recommended_tag_index] in tags:
                    results[recommended_tag_index] = 1
                else:
                    results[recommended_tag_index] = 0
            except IndexError:
                pass

        res.append(results)

    # Return an array of the collected results
    return res


def print_results(sys, test_tags, pa1, pa5, sa5):

    if len(test_tags) > 0:
        print sys['name']

        tt_len = len(test_tags)

        # Precision at one is the percentage of runs where top tag recommended is relevant (McParlane, 2014)
        print "Precision at 1 - " + str(pa1) + " out of " + str(tt_len)
        pa1 = (pa1 / tt_len) * 100
        print pa1, '%'

        # Precision at five is the percentage of relevant tags amongst the five recommended ones
        print "Precision at 5 - " + str(pa5) + " out of " + str(tt_len * 5)
        pa5 = (pa5 / tt_len) * 100
        print pa5, '%'

        # Success at five is the percentage of runs where at least one relevant tag is found
        # amongst the recommended ones
        print "Success at 5 - " + str(sa5) + " out of " + str(tt_len)
        sa5 = (sa5 / tt_len) * 100
        print sa5, '%'

        print "\n"

