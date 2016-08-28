import flickrapi
import json

# Set up the Flickr API
api_key = u'267fe530e588c482dfdad60a0ea85955'
api_secret = u'05307043c90701cf'
flickr = flickrapi.FlickrAPI(api_key, api_secret, format='json')


# Given a tag return the top x recommended tags based on Flickr's getRelated function
# (where x is the amount_results parameter)
def get_recommended(tag, amount_results):

    # Get the related tags from Flickr and parse
    tags = flickr.tags.getRelated(tag=tag)
    tags = json.loads(tags.decode('utf-8'))

    # If there are tags returned then limit the results to x tags
    if 'tags' in tags:
        tags = tags['tags']['tag'][:amount_results]

    # If related tags cannot be found inform the calling method
    else:
        return []

    # Create and return an array of x recommended tags
    tag_array = []
    for tag in tags:
        tag_array.append(tag['_content'])
    return tag_array
