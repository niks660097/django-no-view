import sys
import json
import traceback
from functools import wraps
from django.http.response import HttpResponse
from django.db.transaction import atomic
JSON_VALIDATION_TYPES = ['string', 'integer', 'float', 'bool', 'schema', 'enum']#single or list, schema means dict inside dict

# except type everything is optional
JSON_VALIDATION_SAMPLE = {'name': {'type': 'string', 'required': True, 'custom': '<function>', 'list': True},  # except type everything is optional
                          'enum_name': {'type': 'enum', 'required': True, 'custom': '<function>', 'enum_list': ['A',
                                                                                                                'B', 'C']},
                          'details': {'type': 'schema', 'schema': {'address1': {'type': 'string'},
                                                                   'address2': {"type": 'string'}}
                                      },
                          '__custom': '<function>'
                          }
# JSON VALIDATOR DOCUMENTATION,


class InvalidJSONData(Exception):
    pass


class InvalidJSONValidatorSchema(Exception):
    pass


class JSONValidator:

    @staticmethod
    def validate_string(key, json_val, _schema):
        if type(json_val) == list:
            for i in json_val:
                if type(i) != str:
                    raise InvalidJSONData('Invalid field type ' + key + ' allowed string, given ' + str(type(i)))
        else:
            if type(json_val) != str:
                raise InvalidJSONData('Invalid field type ' + key + ' allowed string, given ' + str(type(json_val)))

    @staticmethod
    def validate_integer(key, json_val, _schema):
        if type(json_val) == list:
            for i in json_val:
                if type(i) != int:
                    raise InvalidJSONData('Invalid field type ' + key + ' allowed integer, given ' + str(type(i)))
        else:
            if type(json_val) != int:
                raise InvalidJSONData('Invalid field type ' + key + ' allowed integer, given ' + str(type(json_val)))

    @staticmethod
    def validate_float(key, json_val, _schema):
        if type(json_val) == list:
            for i in json_val:
                if type(i) != float:
                    raise InvalidJSONData('Invalid field type ' + key + ' allowed float, given ' + str(type(i)))
        else:
            if type(json_val) != float:
                raise InvalidJSONData('Invalid field type ' + key + ' allowed float, given ' + str(type(json_val)))

    @staticmethod
    def validate_bool(key, json_val, _schema):
        if type(json_val) == list:
            for i in json_val:
                if type(i) != bool:
                    raise InvalidJSONData('Invalid field type ' + key + ' allowed bool, given ' + str(type(i)))
        else:
            if type(json_val) != bool:
                raise InvalidJSONData('Invalid field type ' + key + ' allowed bool, given ' + str(type(json_val)))

    @staticmethod
    def validate_enum(key, json_val, _schema):
        if type(json_val) == list:
            for i in json_val:
                if i not in _schema[key]['enum_list']:
                    raise InvalidJSONData('Invalid field type ' + key + 'enum not in ' + str(_schema[key]['enum_list']))
        else:
            if json_val not in _schema[key]['enum_list']:
                raise InvalidJSONData('Invalid field type ' + key + 'enum not in ' + str(_schema[key]['enum_list']))


def _validate_json(_schema, _json):
    if _schema.get('__custom'):
        _schema['__custom'](_schema, _json)
    for key in _schema.keys():
        json_val = _json.get(key, None)
        if json_val is None and _schema[key].get('required', None):
            raise InvalidJSONData('Required field ' + key, 'missing from data')
        if json_val:
            if _schema[key].get('list') and not type(json_val) == list:
                raise InvalidJSONData('key %s should be an array' % key)

            if _schema[key].get('custom'):
                if not _schema[key]['custom'](json_val):
                    raise InvalidJSONData('custom validation failed for, %s key while calling %s' %
                                          (key, str(_schema[key]['custom'])))
            _type = _schema[key]['type']

            if _type in JSON_VALIDATION_TYPES:
                if _type == 'schema':
                    _validate_json(_schema[key]['schema'], json_val)  # recurring to validate nested schema
                else:
                    getattr(JSONValidator, 'validate_' + _type)(key, json_val, _schema)
            else:
                raise InvalidJSONValidatorSchema('no such type "{_type}"'.format(_type=_type))


def validate_json(schema, methods=('POST', ), custom_validator=None):
    def decorator(view):
        def wrapped(request, *args, **kwargs):
            if request.method in methods:
                _json = request.body.decode('utf-8')
                _json = json.loads(_json)
                _validate_json(schema, _json)
                if custom_validator:
                    if not custom_validator(_json):
                        raise InvalidJSONData('custom validation failed')
            return view(request, *args, **kwargs)
        return wrapped

    return decorator


def wrap_json_response(json_dump_callable=None):
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            _dict = view(*args, **kwargs)
            if type(_dict) == HttpResponse:
                return _dict
            if type(_dict) != str:
                if json_dump_callable:
                    return HttpResponse(json.dumps(_dict, default=json_dump_callable), content_type='application/json')
                else:
                    return HttpResponse(json.dumps(_dict), content_type='application/json')
            else:
                return HttpResponse(_dict, content_type='application/json')
        return wrapped

    return decorator


def atomic_exception_handler(default_handling=()):
    #default handling can also be a function directly
    #default_handling means don't raise exception for these exception types
    #default handling is a list of Exceptions for which exception will not be raised and an exception message will be sent
    def decorator(view_func):
        view_func = atomic(view_func)

        @wraps(view_func)
        def wrapped(*args, **kwargs):
            excp_obj = {'error': True}
            try:
                resp = view_func(*args, exc_obj=excp_obj, **kwargs)
            except Exception as e:
                print(e)
                print(str(sys.exc_info()[2]))
                if not excp_obj.get('msg'):#that means view didn't pass any message or data in excp_obj
                    if not callable(default_handling) and not type(e) in default_handling:
                        raise e
                    else:
                        return HttpResponse(json.dumps({"msg": str(e),
                                                        "error": True,
                                                        "exception_type": str(type(e))}),
                                            status=400)
                return HttpResponse(json.dumps(excp_obj),
                                    status=400,
                                    content_type='application/json')
            else:
                return resp
        return wrapped

    if callable(default_handling):
        return decorator(default_handling)

    return decorator


def json_from_request(request):
    return json.loads(request.body.decode('utf-8'))


class UnAuthorized(Exception):
    pass


def authorize(auth_fn_list=()):
    def decorator(view):
        @wraps(view)
        def wrapped(request, *args, **kwargs):
            for f in auth_fn_list:
                if not f(request, *args, **kwargs):
                    raise UnAuthorized('authorization failed from method {method}'.format(method=str(f)))
            return view(request, *args, **kwargs)
        return wrapped
    return decorator


def not_allowed(request, exc_obj):
    exc_obj['error'] = True
    exc_obj['msg'] = 'method not allowed..'
    exc_obj['traceback'] = str(traceback.format_exc())
    raise Exception('MethodNotallowed')
