from django import forms
from models import Rating, UserImage


class RatingForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        choice_list = kwargs.pop('choice_list')
        super(RatingForm, self).__init__(*args, **kwargs)
        for i, choice in enumerate(choice_list):
            self.fields['selected_%d' % (i + 1)] = forms.BooleanField(required=False, label=choice)

    system_choice = forms.CharField(max_length=20, widget=forms.HiddenInput())
    selected_1 = forms.BooleanField(required=False, widget=forms.CheckboxInput(attrs={'class': 'eval-check'}))
    selected_2 = forms.BooleanField(required=False, widget=forms.CheckboxInput(attrs={'class': 'eval-check'}))
    selected_3 = forms.BooleanField(required=False, widget=forms.CheckboxInput(attrs={'class': 'eval-check'}))
    selected_4 = forms.BooleanField(required=False, widget=forms.CheckboxInput(attrs={'class': 'eval-check'}))
    selected_5 = forms.BooleanField(required=False, widget=forms.CheckboxInput(attrs={'class': 'eval-check'}))

    class Meta:

        model = Rating
        fields = ('system_choice', 'selected_1', 'selected_2', 'selected_3', 'selected_4', 'selected_5')


class ImageForm(forms.ModelForm):

    img = forms.ImageField(label='Upload Images')
    tag = forms.CharField(max_length=100)

    class Meta:
        model = UserImage
        fields = ('img', 'tag')

