import numpy as np

# Goes through a series of checks to remove noisey tags
# TODO: Could also check for words spelled similar to another word in the tag by using edit distance


camera_brands = []
camera_models = []


def remove_noise(tags):

    def is_camera(tag):

        global camera_brands, camera_models
        return not (tag.lower() in camera_brands or tag.lower() in camera_models)

    def is_location(tag):
        return True

    def is_time(tag):
        return True

    def is_group(tag):
        return True

    def is_achievement(tag):
        return True

    def is_nonsense(tag):
        return True

    def is_synonym(tag, tags):
        return True

    def is_translation(tag, tags):
        return True

    # Perform all checks to determine if tag is noise
    def perform_checks(tag):

        # Put all checks into array
        checks = [is_camera, is_location, is_time, is_nonsense]

        # Perform checks
        for check in checks:
            # False if check fails
            if check(tag) is False:
                return False

        return True

    new_tags = []

    for current_tag in tags:

        # True if all checks pass
        if perform_checks(current_tag):
            # Put the tag into array to return as it is not noise
            new_tags.append(current_tag)

    # Return all tags that are not noise
    return new_tags


def load_files():
    global camera_brands, camera_models
    camera_brands = np.load("flickr_data/camera_brands.npy")
    camera_models = np.load("flickr_data/camera_models.npy")


load_files()
