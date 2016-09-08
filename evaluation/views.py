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
data = {'form-TOTAL_FORMS': '20', 'form-INITIAL_FORMS': '0', 'form-MAX_NUM_FORMS': ''}


def rating_form(request):

    global choice_list
    global system_choice
    global image

    if request.method == 'POST':

        form = RatingForm(request.POST, choice_list=choice_list)

        # Check the user has provided a valid form
        if form.is_valid():

            # Save the new rating to the database.
            form.save(commit=True)

            form, image, img_name, tag = interface.next_img()

            if form is None:
                return render(request, 'complete.html')

            return render(request, 'eval.html', {'form': form, 'img': '/media/user_images/' + img_name, 'tag': tag})
        else:
            # The supplied form contained errors - just print them to the terminal.
            print form.errors

    else:

        form, image = interface.next_img()

    # Bad form (or form details), no form supplied...
    # Render the form with error messages (if any).
    return render(request, "eval.html", {'form': form, 'img': '/' + image})


def upload_image(request):

    global choice_list
    global system_choice
    global image

    image_form_set = formset_factory(ImageForm, extra=2)

    if request.method == 'POST':

        form = image_form_set(request.POST, request.FILES, data)

        # Have we been provided with a valid form?
        if form.is_valid():

            # Save the new category to the database.
            for f in form:
                f.save(commit=True)

            interface.create_image_data()
            form, image, img_name, tag = interface.next_img()

            return render(request, 'eval.html', {'form': form, 'img': '/media/user_images/' + img_name, 'tag': tag})

    else:

        # If the request was not a POST, display the form to enter details.
        form = image_form_set(data)
        print(form.as_table())

    # Bad form (or form details), no form supplied...
    # Render the form with error messages (if any).
    return render(request, "img_upload.html", {'formset': form})
