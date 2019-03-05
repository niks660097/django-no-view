import json as json_lib
from django.core.serializers.base import DeserializationError
from django.http.response import HttpResponse
from django.core.serializers.python import _get_model
from django.db import transaction
from django.views.decorators.csrf import csrf_exempt

from utils.view_utils import atomic_exception_handler
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from functools import partial

INTERNAL_SERVER_TOKENS = {'PINT_SERVER': '8c7031da1987404f8f5bfca85917a09c'}


class MissingRpcData(Exception):
    pass


class InvalidRpcRequestData(Exception):
    pass


class InvalidAuthData(Exception):
    pass


def auth_fn_internal_rpc(request, *args, **kwargs):
    token = request.META.get('HTTP_INTERNAL_RPC_TOKEN')
    if token in INTERNAL_SERVER_TOKENS.values():
        return True
    return False


class RPCEndpoint:

    process_pool = ThreadPoolExecutor(max_workers=4)

    def __init__(self, auth_fn):
        self.auth_fn = auth_fn

    @atomic_exception_handler(default_handling=(MissingRpcData, InvalidRpcRequestData, InvalidAuthData))
    @csrf_exempt
    def view_code(self, request, exc_obj, *args, **kwargs):
        if not self.auth_fn(request, *args, **kwargs):
            raise InvalidAuthData({'request': request})
        return RPCHandler.view(request, *args, **kwargs)

    @csrf_exempt
    def view(self, request, *args, **kwargs):
        # return RPCEndpoint.view_code(request, *args, **kwargs)
        f = RPCEndpoint.process_pool.submit(partial(self.view_code, request, *args, **kwargs))
        return f.result()

    @csrf_exempt
    def get_view(self):
        return self.view


class RPCHandler:
    REQUEST_DATA_MISSING = 'REQUEST_DATA_MISSING'
    INVALID_REQUEST_DATA = 'INVALID_REQUEST_DATA'
    AUTH_DATA_MISSING = 'REQUEST_DATA_MISSING'

    @staticmethod
    @csrf_exempt
    def view(request, *args, **kwargs):
        with transaction.atomic():
            req_payload = json_lib.loads(request.body.decode('utf-8'))
            auth_info = req_payload.get('auth')
            request_params = req_payload.get('request_params')
            if not request_params:
                raise MissingRpcData({'error': RPCHandler.REQUEST_DATA_MISSING, 'msg': 'No request params found in request..'})

            app_str = request_params.get('app')
            model_str = request_params.get('model')
            manager_str = request_params.get('manager')
            procedure_str = request_params.get('procedure')
            try:
                model = _get_model('%s.%s' % (app_str, model_str))
            except DeserializationError as e:
                raise InvalidRpcRequestData('invalid app or model name')
            try:
                manager = getattr(model, manager_str)
            except AttributeError:
                raise InvalidRpcRequestData('invalid manager name')
            if manager:
                try:
                    procedure = getattr(manager, procedure_str)
                except AttributeError as e:
                    raise InvalidRpcRequestData("no such procedure with name %s" % procedure_str)
                res = procedure(**request_params.get("procedure_params"))#only named parameters calls allowed
                return HttpResponse(json_lib.dumps(res), status=200, content_type='application/json')
            raise InvalidRpcRequestData({'error': RPCHandler.INVALID_REQUEST_DATA, 'msg': 'Invalid or missing request data'})
