import logging
from datetime import datetime, date
from http import HTTPStatus
import requests

from django.db import models


logger = logging.getLogger('rates:models')

NBRN_NAMES = {
    'Cur_ID': 'cur_id',
    'Cur_ParentID': 'cur_parent_id',
    'Cur_Code': 'numeric_code',
    'Cur_Abbreviation': 'code',
    'Cur_Name': 'name',
    'Cur_Name_Bel': 'name_bel',
    'Cur_Name_Eng': 'name_eng',
    'Cur_QuotName': 'quot_name',
    'Cur_QuotName_Bel': 'quot_name_bel',
    'Cur_QuotName_Eng': 'quot_name_eng',
    'Cur_NameMulti': 'name_multi',
    'Cur_Name_BelMulti': 'name_multi_bel',
    'Cur_Name_EngMulti': 'name_multi_eng',
    'Cur_Scale': 'scale',
    'Cur_Periodicity': 'periodicity',
    'Cur_DateStart': 'date_start',
    'Cur_DateEnd': 'date_end'
}

NBRB_CURRENCY_URL = 'https://www.nbrb.by/api/exrates/currencies/'
NBRB_RATE_URL = 'https://www.nbrb.by/api/exrates/rates/'

def nbrb_currency_to_kwargs(nbrb_currency):
    result = {}
    for k, v in nbrb_currency.items():
        field_name = NBRN_NAMES[k]
        result[field_name] = v
    result['date_start'] = datetime.strptime(result['date_start'], '%Y-%m-%dT%H:%M:%S').date()
    result['date_end'] = datetime.strptime(result['date_end'], '%Y-%m-%dT%H:%M:%S').date()
    return result

def nbrb_rates_to_kwargs(nbrb_rate, currencies):
    result = {
        'currency': currencies.get(cur_id=nbrb_rate['Cur_ID']),
        'date': datetime.strptime(nbrb_rate['Date'], '%Y-%m-%dT%H:%M:%S').date(),
        'official': nbrb_rate['Cur_OfficialRate']
    }
    return result


class Currency(models.Model):
    """Model for currency catalog"""
    cur_id = models.IntegerField(verbose_name='internal code')
    cur_parent_id = models.IntegerField(verbose_name='reference code')
    numeric_code = models.CharField(max_length=3)
    code = models.CharField(max_length=3)
    name = models.CharField(max_length=256)
    name_bel = models.CharField(max_length=256)
    name_eng = models.CharField(max_length=256)
    quot_name = models.CharField(max_length=256)
    quot_name_bel = models.CharField(max_length=256)
    quot_name_eng = models.CharField(max_length=256)
    name_multi = models.CharField(max_length=256)
    name_multi_bel = models.CharField(max_length=256)
    name_multi_eng = models.CharField(max_length=256)
    scale = models.IntegerField(verbose_name='exchange units')
    periodicity = models.IntegerField(
        verbose_name='periodicity(0 – daily, 1 – monthly)'
    )
    date_start = models.DateField()
    date_end = models.DateField()

    def __str__(self):
        return f'{self.code}({self.numeric_code}) {self.name}'

    @staticmethod
    def load_from_nbrb(filter_ids=None):
        """Load currency catalog to db from NBRB"""
        logger.info('Currency.load_from_nbrb: START')
        resp = requests.get(NBRB_CURRENCY_URL)
        if resp.status_code == HTTPStatus.OK:
            rows = []
            for nbrb_currency in resp.json():
                if filter_ids and nbrb_currency['Cur_ID'] not in filter_ids:
                    continue
                kwargs = nbrb_currency_to_kwargs(nbrb_currency)
                currency = Currency(**kwargs)
                rows.append(currency)
                if filter_ids:
                    logger.info(f'Currency.load_from_nbrb: cur_id={currency.cur_id} added')
            Currency.objects.bulk_create(rows)
            logger.info(f'Currency.load_from_nbrb: {len(rows)} loaded FINISH')
        else:
            logger.info(f'Currency.load_from_nbrb: FINISH {resp.status_code} (NBRB)')

    @staticmethod
    def check_and_update_catalog(rates):
        """Load new currencies to db from NBRB"""
        logger.info('Currency.check_and_update_catalog: START')
        currencies = Currency.objects.all()
        cur_ids = [cur.cur_id for cur in currencies]
        input_cur_ids = [rate['Cur_ID'] for rate in rates]
        missing_ids = set(input_cur_ids) - set(cur_ids)
        Currency.load_from_nbrb(missing_ids)
        logger.info('Currency.check_and_update_catalog: FINISH')



class Rate(models.Model):
    """Model for currency rates by dates"""
    currency = models.ForeignKey(Currency, on_delete=models.CASCADE)
    date = models.DateField()
    official = models.DecimalField(max_digits=13, decimal_places=4)

    def __str__(self):
        return f'{self.currency.code}({self.date}) = {self.official}'

    @staticmethod
    def load_from_nbrb(date_rate):
        """Load currency rates to db from NBRB by date"""
        logger.info('Rate.load_from_nbrb: START')
        date_filter = datetime.strptime(date_rate, '%Y-%m-%d').date()
        rate_by_date = Rate.objects.filter(date=date_filter)[:1]
        if len(rate_by_date) == 0:
            params = {'ondate': date_rate, 'periodicity': 0, 'parammode': 0}
            resp = requests.get(NBRB_RATE_URL, params=params)
            if resp.status_code == HTTPStatus.OK:
                rows = []
                rates = resp.json()
                if rates:
                    if Currency.objects.count() == 0:
                        Currency.load_from_nbrb()
                    currencies = Currency.objects.all()
                    for nbrb_rate in rates:
                        try:
                            kwargs = nbrb_rates_to_kwargs(nbrb_rate, currencies)
                        except Currency.DoesNotExist:
                            cur_id = nbrb_rate['Cur_ID']
                            cur_code = nbrb_rate['Cur_Abbreviation']
                            logger.exception(f'Rate.load_from_nbrb: id={cur_id} code={cur_code}')
                            Currency.check_and_update_catalog(rates)
                            # after update try again
                            currencies = Currency.objects.all()
                            kwargs = nbrb_rates_to_kwargs(nbrb_rate, currencies)
                        rows.append(Rate(**kwargs))
                    Rate.objects.bulk_create(rows)
                    logger.info(f'Rate.load_from_nbrb: {len(rows)} LOADED')
                    result = HTTPStatus.CREATED
                else:
                    result = HTTPStatus.NOT_ACCEPTABLE
        else:
            result = HTTPStatus.CONFLICT
        logger.info(f'Rate.load_from_nbrb: FINISH {result}')
        return result