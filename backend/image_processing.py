import numpy as np
import cv2
import os
import matplotlib.pyplot as plt
import math
import exifread

face_cascade = cv2.CascadeClassifier('backend/trainingData/haarcascade_frontalface_default.xml')


# Code created by following tutorial found in iPython Interactive Computing and Visualisation p371
# Uses Viola and Jones' (2001) HAAR cascade method
def get_faces(image):

    try:
        # Convert to greyscale to improve accuracy and efficiency
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Return the number of faces detected using the aforementioned HAAR cascade method
        return min(len(face_cascade.detectMultiScale(gray, 1.3)), 3)

    # Unknown error with a minority (< 0.01%) of images - return 0 faces
    except Exception:
        return 0


# Get the number of faces for each photo in an array
def get_faces_array(image_array):
    return process_array(get_faces, image_array)


# Get the orientation (portrait, landscape or square) given an image
# NOTE: this information is returned through some Flickr API calls and so may be better using that
def get_image_orientation(image):

    # Get the width and height of the image
    height, width = image.shape[:2]

    if width > height:
        # Landscape
        return 0
    elif height > width:
        # Portrait
        return 1
    else:
        # Square
        return 2


# Get the image orientation for each image in an array
def get_image_orientation_array(image_array):
        return process_array(get_image_orientation, image_array)


# Get the most dominant colour in an image and quantise it to one of 5 colours or shades
def get_dominant_colour(image):

    # 0 for white, 1 for black, 2 for red, 3 for green and 4 for blue
    colours = [[256, 256, 256], [0, 0, 0], [255, 0, 0], [0, 255, 0], [0, 0, 255]]

    # Set the initial minimum euclidean distance to be higher than any possible distance between 256 bit colours
    min_distance = 257
    min_distance_index = -1

    # Get the average colour of the image
    average = cv2.mean(image)

    # Loop through each of the five colours/shades and find the euclidean distances between them and the average colour
    for index, colour in enumerate(colours):
        distance = math.sqrt((colour[0] - average[0]) ** 2 +
                             (colour[1] - average[1]) ** 2 +
                             (colour[2] - average[2]) ** 2)

        # If the new distance is smaller than the current minimum distance then this is the new min distance
        if distance < min_distance:
            min_distance, min_distance_index = distance, index

    # Return the number (0 to 4) corresponding to the dominant colour
    return min_distance_index


# Execute given target function for each image in an array
def process_array(target_function, image_array):

    # Create a zeroed numpy array
    array = np.zeros(len(image_array))

    # Execute target function passing in each image in array as parameter
    for i in range(len(array)):
        array[i] = target_function(image_array[i])

    # Return the values returned from each execution of target function
    return array


# Read each image in an array in a form that Open CV can read (e.g. for number of faces or dominant colour)
def read_image_array(image_array):

    array = []

    for image in image_array:
        array.append([plt.imread(image), image])

    # Returns an array of Open CV readable images
    return array


def read_image(image):
    return plt.imread(os.path.join(image))


# Retrieves an Open CV readable image from each image file in a given directory (e.g. "C:/user/images")
def images_from_directory(directory_path, lower_limit=0, upper_limit=0):

    array = []

    # Assumes all files in directory are images to improve efficiency
    for subdir, dirs, files in os.walk(directory_path):

        # If there is a given file limit then only look for this amount of files
        if upper_limit > 0:
            for index, image in enumerate(files[lower_limit:upper_limit]):
                # Issue with reading through cv2.imread on some files
                # Remove ".jpg" from image id

                try:
                    array.append([plt.imread(os.path.join(subdir, image)), image[:-4]])
                except IOError:
                    pass

        else:

            # Look at all possible files after the given (if any) offset
            # Offsets are used to split up the training and test sets so they do not read the same images
            for index, image in enumerate(files[lower_limit:]):

                # Issue with reading through cv2.imread on some files
                # Remove ".jpg" from image id
                try:
                    array.append([plt.imread(os.path.join(subdir, image)), image[:-4]])
                except IOError:
                    pass

    # Return an array of Open CV readable images
    return np.array(array)


def get_exif(photo_filename):

    f = open(photo_filename, 'rb')
    f = exifread.process_file(f)

    photo = {}
    photo['id'] = photo_filename
    photo['lat'], photo['lon'] = convert_to_degress(f)

    # Return Exif tags
    return photo


# From http://stackoverflow.com/questions/6460381/translate-exif-dms-to-dd-geolocation-with-python

def convert_to_degress(photo):
    lat = [float(x) / float(y) for x, y in photo['GPS GPSLatitude']]
    latref = photo['GPS GPSLatitudeRef']
    lon = [float(x) / float(y) for x, y in photo['GPS GPSLongitude']]
    lonref = photo['GPS GPSLongitudeRef']

    lat = lat[0] + lat[1] / 60 + lat[2] / 3600
    lon = lon[0] + lon[1] / 60 + lon[2] / 3600
    if latref == 'S':
        lat = -lat
    if lonref == 'W':
        lon = -lon

    return lat, lon