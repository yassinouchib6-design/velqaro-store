import re

from django import forms


MOROCCAN_CITIES = [
    ("Casablanca", "Casablanca"),
    ("Rabat", "Rabat"),
    ("Marrakech", "Marrakech"),
    ("Fes", "Fes"),
    ("Tangier", "Tangier"),
    ("Agadir", "Agadir"),
    ("Meknes", "Meknes"),
    ("Oujda", "Oujda"),
    ("Tetouan", "Tetouan"),
    ("Kenitra", "Kenitra"),
    ("Safi", "Safi"),
    ("El Jadida", "El Jadida"),
]


class CheckoutForm(forms.Form):
    full_name = forms.CharField(label="Nom complet", max_length=140)
    phone = forms.CharField(label="Telephone", max_length=30)
    city = forms.ChoiceField(label="Ville", choices=MOROCCAN_CITIES)
    address = forms.CharField(label="Adresse", widget=forms.Textarea(attrs={"rows": 3}))
    note = forms.CharField(
        label="Note",
        required=False,
        widget=forms.Textarea(attrs={"rows": 3}),
    )
    checkout_token = forms.CharField(widget=forms.HiddenInput)

    def clean_phone(self):
        phone = self.cleaned_data["phone"]
        compact = re.sub(r"[\s.-]", "", phone)
        if not re.match(r"^(0[67]\d{8}|\+212[67]\d{8})$", compact):
            raise forms.ValidationError("Entrez un numero marocain valide.")
        return compact
