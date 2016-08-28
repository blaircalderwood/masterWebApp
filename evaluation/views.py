from django.shortcuts import render
from forms import RatingForm, ImageForm
from backend import interface
from random import choice
from django.forms import formset_factory
import os

choice_list = []
system_choice = ''
systems = ['flickr_recommended', 'tag_cooccurrence', 'phillip_system', 'new_sys']
imgs = []
image = ''


def rating_form(request):

    global choice_list
    global system_choice
    global image

    if request.method == 'POST':

        form = RatingForm(request.POST, choice_list=choice_list)

        # Have we been provided with a valid form?
        if form.is_valid():

            system_choice = choice(systems)
            choice_list = interface.get_recommendations(system_choice, image)

            # Save the new category to the database.
            form.save(commit=True)
            form = RatingForm(choice_list=choice_list)
            form.fields["system_choice"].initial = system_choice

            image = "/media/%s" % interface.get_next_image()

            return render(request, 'eval.html', {'form': form, 'img': image})
        else:
            # The supplied form contained errors - just print them to the terminal.
            print form.errors

    else:

        system_choice = choice(systems)
        choice_list = interface.get_recommendations(system_choice, image)

        # If the request was not a POST, display the form to enter details.
        form = RatingForm(choice_list=choice_list)
        form.fields["system_choice"].initial = system_choice

    # Bad form (or form details), no form supplied...
    # Render the form with error messages (if any).
    return render(request, "eval.html", {'form': form, 'img': image})


def upload_image(request):

    global choice_list
    global system_choice
    global image

    imageFormSet = formset_factory(ImageForm, extra=2)

    if request.method == 'POST':

        form = imageFormSet(request.POST, request.FILES)

        # Have we been provided with a valid form?
        if form.is_valid():

            # Save the new category to the database.
            for f in form:
                f.save(commit=True)

            image = interface.get_next_image()

            system_choice = choice(systems)
            form = RatingForm(choice_list=choice_list)
            choice_list = interface.get_recommendations(system_choice, image)

            return render(request, 'eval.html', {'form': form, 'img': image})

    else:

        # If the request was not a POST, display the form to enter details.
        form = imageFormSet()
        print(form.as_table())

    # Bad form (or form details), no form supplied...
    # Render the form with error messages (if any).
    return render(request, "img_upload.html", {'formset': form})