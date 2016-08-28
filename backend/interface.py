from evaluation.models import UserImage
import image_processing as ip
import os

imgs = []
image_names = []


def add_context(photo_id):

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


def get_recommendations(system, photo_id=""):

    return ['wow', 'there', 'are', 'many', 'recommendations']


def create_image_data():

    global imgs, image_names
    imgs = []
    image_names = []

    for directory, _, files in os.walk('media'):
        for img_file in files:
            image = os.path.join(directory, img_file)
            imgs.append(ip.read_image(image))

            # OS join wasn't working for this line
            img_name = '/' + directory + '/' + img_file
            image_names.append(img_name)
            exif = ip.get_exif(img_name)


def get_next_image():

    return image_names[0]


def delete_images():

    # Delete all images in media folder (needs to be done so no user info is held)
    for directory, _, files in os.walk('media'):
        for img_file in files:
            os.remove(os.path.join(directory, img_file))
