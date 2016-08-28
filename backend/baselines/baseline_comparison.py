import baselines.flickr_reccommended as fr
import baselines.tag_cooccurrence as tc
import sql_extract
from general_functions import binary_search
import numpy as np
import location
import random
from copy import copy


# Preprocess the dataset so it does not need to be built each time the system is run
# This method can be performed in chunks by altering the db lower and upper limits
def build_database(directory="", db_limit_lower=0, db_limit_upper=0):

    # Create database records pertaining to the inputted image folder
    # This will return an array of photos with data such as number of faces
    # It will also return an array of tags relating to the aforementioned photos
    photo_array, photos_tags = sql_extract.create_data(directory, db_limit_lower, db_limit_upper)

    # Open a connection to the sql database
    location.open_connection()

    # Loop through all photos in array and create database records relating to their location (places ID)
    for photo_index, photo in enumerate(photo_array):
        if photo['places_id'] is not 0:
            # These are put into a separate list as they contain data from outwith the dataset
            # And therefore should not be returned for use in training / testing
        #    location.save_to_area(photo['places_id'], photos_tags[photo_index])
            pass
        if photo['postingTime'] is not None:
            location.save_to_area(photo['postingTime'], photos_tags[photo_index])

    # Close the connection to the sql database
    location.close_connection()

    return photo_array, photos_tags


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
    execute_test(test_photos, test_tags, write_results)


def set_up(limit, training_amount, load_from_file=False):

    photo_array = sql_extract.get_photo_data(limit)
    photos_tags = [sql_extract.get_photo_tags(photo['id']) for photo in photo_array]
    tag_array = sql_extract.get_tags()

    # Assign all data found before the cut off point (test_amount) to the training set
    training_array = photo_array[:training_amount]
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
        tc.create(training_array, training_tags, tag_array)

    return test_photos, test_tags


def execute_test(test_photos, test_tags, write_results=False):

    # Set up dictionaries that will contain results of test
    flickr_recommended = {'name': 'Flickr Recommended', 'total_pa1': 0, 'total_pa5': 0, 'total_sa5': 0, 'total_mrr': 0}
    tag_cooccurrence = {'name': 'Tag Co-occurrence', 'total_pa1': 0, 'total_pa5': 0, 'total_sa5': 0, 'total_mrr': 0}
    phillip_cooccurrence = {'name': 'Phillip\'s Baseline', 'total_pa1': 0, 'total_pa5': 0, 'total_sa5': 0,
                            'total_mrr': 0}
    new_sys = {'name': 'New co-occurrence system', 'total_pa1': 0, 'total_pa5': 0, 'total_sa5': 0, 'total_mrr': 0}
    loc_only = {'name': 'Location', 'total_pa1': 0, 'total_pa5': 0, 'total_sa5': 0, 'total_mrr': 0}
    time_only = {'name': 'Time', 'total_pa1': 0, 'total_pa5': 0, 'total_sa5': 0, 'total_mrr': 0}

    # Run through each tag in the test tags set
    for test_index, photo_tags in enumerate(test_tags):

        # Skip any photos that do not have a sufficient amount of tags
        if len(photo_tags) < 6:
            continue

        tags = copy(photo_tags)

        # A random tag from the photo tag list will be submitted to each baseline
        tag = random.choice(tags)

        # All others will be compared against the baseline's recommendations
        tags.remove(tag)

        # Get the recommended tags from each system
        # TODO: Remember to re-enable this and put it back in sys list
        # flickr_recommended['recommended_tags'] = fr.get_recommended(tag, 5)
        tag_cooccurrence['recommended_tags'] = tc.get_overall_recommended(tag, 5)
        phillip_cooccurrence['recommended_tags'] = tc.get_phillip_recommended(test_photos[test_index], tag, 5)
        new_sys['recommended_tags'] = tc.novel_sys_recommendations(test_photos[test_index], tag, 5, False, photo_tags)
        loc_only['recommended_tags'] = tc.location_recommendation(test_photos[test_index], tag, 5, False, photo_tags)
        time_only['recommended_tags'] = tc.time_recommendation(test_photos[test_index], tag, 5, False, photo_tags)

        systems = [tag_cooccurrence, phillip_cooccurrence, new_sys, loc_only, time_only]

        # Save the current tag and the recommended tag of each system to spreadsheet
        if write_results:
            print "Original tags, " + tag + ", " + str(tags) + "\n"
            for sys in systems:
                print sys['name'], sys['recommended_tags']

        # Loop through each tag recommendation system and gather results for precision at one etc.
        for sys in systems:
            # TODO: MRR is being calculated wrong and needs to be fixed
            new_pa1, new_mrr = precision_at_one(tags, sys['recommended_tags'])
            new_sa5, new_pa5 = precision_success_at_five(tags, sys['recommended_tags'])
            sys['total_pa1'] += new_pa1
            sys['total_sa5'] += new_sa5
            sys['total_pa5'] += new_pa5
            sys['total_mrr'] += new_mrr

    # Print the test results on screen
    for sys in systems:
        print "LENGTH: " + str(len(test_tags))
        print_results(sys, test_tags)


# Get the precision at one and Mean Reciprocal Rank (MRR) of given tag
# Precision at one is the percentage of runs where top tag recommended is relevant
# MRR is "computed as 1/r where r is the rank of the first relevant tag returned,
# averaged over all runs" (McParlane, 2014)
def precision_at_one(other_tags, recommended_tags):

    # If there are 1 or more
    if recommended_tags is not None and other_tags is not None and len(recommended_tags) > 0 and len(other_tags) > 0:
        if recommended_tags[0] in other_tags:
            return 1, 1 / binary_search(np.array(other_tags), recommended_tags[0])

    return 0, 0


# Gets the Precision at five and success at five of give tag
# Precision at five is the percentage of relevant tags amongst the five recommended ones
# Success at five is the percentage of runs where at least one relevant tag is found amongst the recommended ones
def precision_success_at_five(other_tags, recommended_tags):

    success = 0
    precision = 0

    if recommended_tags is not None and other_tags is not None:

        for index, rec_tag in enumerate(recommended_tags):
            if rec_tag in other_tags:
                success = 1
                precision += 1

    return success, precision


def print_results(sys, test_tags):

    if len(test_tags) > 0:
        print sys['name']

        print "Precision at 1 - " + str(sys['total_pa1']) + " out of " + str(len(test_tags))
        sys['total_pa1'] = float(sys['total_pa1']) / float(len(test_tags)) * 100
        print str(sys['total_pa1']) + '%'

        print "Precision at 5 - " + str(sys['total_pa5']) + " out of " + str(len(test_tags) * 5)
        sys['total_pa5'] = float(sys['total_pa5']) / float(len(test_tags) * 5) * 100
        print str(sys['total_pa5']) + '%'

        print "Success at 5 - " + str(sys['total_sa5']) + " out of " + str(len(test_tags))
        sys['total_sa5'] = float(sys['total_sa5']) / float(len(test_tags)) * 100
        print str(sys['total_sa5']) + '%'

        print "MRR - " + str(sys['total_mrr']) + " out of " + str(len(test_tags))
        sys['total_mrr'] = float(sys['total_mrr']) / float(len(test_tags)) * 100
        print str(sys['total_mrr']) + '%'

        print "\n"
