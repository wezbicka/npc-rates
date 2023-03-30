import logging
import json
from datetime import datetime, date, timedelta
import binascii
from http import HTTPStatus

from django.core.serializers import serialize
from django.http import HttpResponseRedirect, JsonResponse
from django.urls import reverse
from django.views import generic
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

from .models import Currency, Rate
from .forms import DateSelectForm, RateSelectForm


logger = logging.getLogger('rates:views')


class OperationView(generic.TemplateView):
    """Choice operations with currency."""
    template_name = 'rates/operations.html'


class DateSelectView(generic.FormView):
    """Select date and upload currency rates to DB"""
    template_name = 'rates/select_date.html'
    form_class = DateSelectForm

    def get(self, request, *args, **kwargs):
        context = {'date_default': datetime.strftime(date.today(), '%Y-%m-%d')}
        return self.render_to_response(context)


class RateSelectView(generic.FormView):
    """Select date and currency code to show information"""
    template_name = 'rates/select_rate.html'
    form_class = RateSelectForm

    def get(self, request, *args, **kwargs):
        if request.GET:
            date_rate = request.GET.get('edt_select_date', '')
            currency = request.GET.get('cmb_select_currency', '')
            params = {'date_rate': date_rate, 'currency': currency}
            if not date_rate or not currency:
                params['message'] = 'Date and currency must be specified.'
                return JsonResponse(data=params, status=HTTPStatus.BAD_REQUEST)
            else:
                return HttpResponseRedirect(reverse('rates:get_rate', kwargs=params))
        else:
            currency_list = [row['code'] for row in Currency.objects.values('code')]
            currency_list = list(set(currency_list))
            currency_list.sort()
            context = {
                'date_default': datetime.strftime(date.today(), '%Y-%m-%d'),
                'currency_list': currency_list
            }
            return self.render_to_response(context)


@method_decorator(csrf_exempt, name='dispatch')
class RateView(generic.View):

    def _add_crc32(self, response):
        """Add crc32 value to response header"""
        crc32 = binascii.crc32(response.content)
        response.headers['crc32'] = crc32

    def get(self, request, date_rate, currency):
        """Get rate information by date and currency"""
        logger.info(f'{request.method} {request.path} START')
        try:
            date_rate = datetime.strptime(date_rate, '%Y-%m-%d').date()
        except ValueError:
            text = f'Date "{date_rate}" must be in YYYY-MM-DD format.'
            data = {'message': text}
            status = HTTPStatus.BAD_REQUEST
        else:
            rates = Rate.objects.filter(date=date_rate, currency__code=currency)
            if len(rates) == 0:
                text = f'Data on the currency "{currency}" for the date {date_rate} is not loaded.'
                data = {'message': text}
                status = HTTPStatus.NOT_FOUND
            else:
                rate = rates[0]
                date_rate -= timedelta(days=1)
                rates_prev = Rate.objects.filter(date=date_rate, currency__code=currency)
                if len(rates_prev) > 0:
                    delta = rate.official - rates_prev[0].official
                else:
                    delta = 0
                delta = f'+{delta}' if delta > 0 else f'{delta}'
                serialized_rate = serialize('python', [rate], fields=('currency', 'official'))
                serialized_currency = serialize(
                    format='python',
                    queryset=[rate.currency],
                    fields=('numeric_code', 'code', 'name', 'name_multi', 'scale')
                )
                serialized_currency = serialized_currency[0]['fields']
                text = f'{rate.currency.name} ({rate.currency.scale}) {rate.currency.code} {rate.official}({delta})'
                data = {
                    'rate': serialized_rate[0]['fields']['official'],
                    'delta': delta,
                    'currency': serialized_currency,
                    'message': text
                }
                status = HTTPStatus.OK
        logger.info(f'{request.method} {request.path} FINISH {status}')
        response = JsonResponse(data=data, status=status)
        self._add_crc32(response)
        return response

    def post(self, request):
        """Upload currency rates to DB on date"""
        logger.info(f'{request.method} {request.path} START')
        if request.POST:
            date_import = request.POST['edt_select_date']
        else:
            post_body = json.loads(request.body)
            date_import = post_body['date_import']
        logger.info(f'{request.method} {request.path} {date_import}')
        status = Rate.load_from_nbrb(date_import)
        if status == HTTPStatus.CREATED:
            text = f'Currency data for date {date_import} loaded successfully.'
        elif status == HTTPStatus.CONFLICT:
            text = f'Currency data for the date {date_import} already exists in the system.'
        else:
            text = f'Currency data for the date {date_import} is not available in the NBRB system.'
            status = HTTPStatus.NOT_ACCEPTABLE
        data = {'message': text}
        logger.info(f'{request.method} {request.path} FINISH {status}')
        response = JsonResponse(data=data, status=status)
        self._add_crc32(response)
        return response
