from django.forms import Form, DateInput, DateField, ChoiceField, Select
from .models import Currency


class DateSelectForm(Form):
    """Form for select date"""
    edt_select_date = DateField(widget=DateInput(format='%Y-%m-%d'))


class RateSelectForm(Form):
    """Form for select date and currency code"""
    edt_select_date = DateField(widget=DateInput(format='%Y-%m-%d'))
    cmb_select_currency = ChoiceField(
        widget= Select(
            choices=[(cur.cur_id, cur.code) for cur in Currency.objects.all()]
        )
    )