from random import choice

from django.forms import formset_factory
from django.shortcuts import render
import backend.baselines.tag_cooccurrence as tc
import interface
from forms import RatingForm, ImageForm
from models import UserImage

choice_list = []
system_choice = ''
systems = ['flickr_recommended', 'tag_cooccurrence', 'phillip_system', 'new_sys']
imgs = []
image = ''
# This is the total amount of images the system will ask the user to upload
data = {'form-TOTAL_FORMS': '20', 'form-INITIAL_FORMS': '0', 'form-MAX_NUM_FORMS': ''}


def rating_form(request):

    global choice_list
    global system_choice
    global image

    # Check if the user wishes to POST data or GET the web page
    if request.method == 'POST':

        # Create a new rating form
        form = RatingForm(request.POST, choice_list=choice_list)

        # Check the user has provided a valid form
        if form.is_valid():

            # Save the new rating to the database.
            form.save(commit=True)

            # Get the next image
            form, image, img_name, tag = interface.next_img()

            # If there is no next image then display the page that informs the user evaluation is complete
            if form is None:
                return render(request, 'complete.html')

            # Display the ratings page with the image, inputted tag and recommended tags
            return render(request, 'eval.html', {'form': form, 'img': '/media/user_images/' + img_name, 'tag': tag})
        else:
            print form.errors

    else:

        # Get the next image
        form, image = interface.next_img()

    # Render the form with error messages (if any)
    return render(request, "eval.html", {'form': form, 'img': '/' + image})


def upload_image(request):

    global choice_list
    global system_choice
    global image

    # Create image upload buttons and tag entry text inputs
    image_form_set = formset_factory(ImageForm, extra=2)

    # If the user has clicked 'upload photos'
    if request.method == 'POST':

        # Get the form
        form = image_form_set(request.POST, request.FILES, data)

        if form.is_valid():

            # Save the new photos to the database.
            for f in form:
                f.save(commit=True)

            # Create the image data (find number of faces etc.)
            interface.create_image_data()

            # Get the first image
            form, image, img_name, tag = interface.next_img()

            # Display the ratings page with the image, inputted tag and recommended tags
            return render(request, 'eval.html', {'form': form, 'img': '/media/user_images/' + img_name, 'tag': tag})

    else:

        # If the request was not a POST, display the form to enter details
        form = image_form_set(data)
        print(form.as_table())

    # Render the form with error messages (if any)
    return render(request, "img_upload.html", {'formset': form})
