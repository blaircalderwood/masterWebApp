import flickrapi
import json
import numpy as np

api_key = u'267fe530e588c482dfdad60a0ea85955'
api_secret = u'05307043c90701cf'
flickr = flickrapi.FlickrAPI(api_key, api_secret, format='json')

# Builds lists of data retrieved from Flickr (such as Camera brand names) and saves them as Numpy array files

camera_brands = flickr.cameras.getBrands()
camera_brands = json.loads(camera_brands.decode('utf-8'))['brands']['brand']

models = []
cameras = []

# Loop through all camera brands and remove any dashes or underscores as these are not found in tags
for brand in camera_brands:

    new_camera = brand['name'].replace("-", "").replace("_", "").lower()
    cameras.append(new_camera)

    # Get all of the models for this brand
    brand_models = flickr.cameras.getBrandModels(brand=brand['id'])
    brand_models = json.loads(brand_models.decode('utf-8'))['cameras']['camera']

    # Add models to an array of all camera models
    for model in brand_models:
        new_model = model['id'].replace("-", "").replace("_", "").lower()
        models.append(new_model)

# Save arrays as numpy files
np.save('flickr_data/camera_brands', cameras)
np.save('flickr_data/camera_models', models)


