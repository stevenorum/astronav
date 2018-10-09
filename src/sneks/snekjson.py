import json
from decimal import Decimal

class blob(dict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__predefined_attributes__ = [a for a in dir(self)]
        self.__predefined_attributes__.append("__predefined_attributes__")
        for key in self.keys():
            if not key in self.__predefined_attributes__:
                setattr(self, key, self[key])
                pass
            pass
        pass

    def __setitem__(self, key, value):
        super().__setitem__(key, value)
        if not key in self.__predefined_attributes__:
            setattr(self, key, self[key])
            pass
        pass

    def __delitem__(self, key):
        super().__delitem__(key)
        if not key in self.__predefined_attributes__:
            delattr(self, key)
            pass
        pass

class SnekJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        # Let the base class default method raise the TypeError
        return json.JSONEncoder.default(self, obj)

class SafeSnekJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        try:
            return SnekJSONEncoder.default(self, obj)
        except TypeError:
            return "<unserializable object of type '{}' with string repr '{}'>".format(type(obj), repr(obj))

def get_kwargs_and_encoder(kwargs):
    if kwargs.get("ignore_type_error") == True:
        del kwargs["ignore_type_error"]
        return kwargs, SafeSnekJSONEncoder
    return kwargs, SnekJSONEncoder

def dump(*args, **kwargs):
    kwargs, encoder = get_kwargs_and_encoder(kwargs)
    return json.dump(cls=encoder, *args, **kwargs)

def dumps(*args, **kwargs):
    kwargs, encoder = get_kwargs_and_encoder(kwargs)
    return json.dumps(cls=encoder, *args, **kwargs)

def dumpf(obj, filename, *args, **kwargs):
    with open(filename, "w") as f:
        return dump(obj, f, *args, **kwargs)

def load(*args, **kwargs):
    return json.load(*args, **kwargs)

def loads(*args, **kwargs):
    if isinstance(args[0], dict):
        return args[0]
    return json.loads(*args, **kwargs)

def loadf(filename, *args, **kwargs):
    with open(filename, "r") as f:
        return json.load(f, *args, **kwargs)
