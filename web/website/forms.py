from django import forms

from web.character_helpers import get_race_choices


class WebCharacterCreateForm(forms.Form):
    name = forms.CharField(max_length=80, strip=True)
    race = forms.ChoiceField(choices=())

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["race"].choices = get_race_choices()