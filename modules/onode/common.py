import os
import cPickle as pickle


def delegate_methods(cls, mod):
    def delegate_method(name):
        fun = getattr(mod, name)
        def wrapper(self, *args, **kwargs):
            return fun(*args, **kwargs)
        wrapper.__name__ = name
        setattr(cls, name, wrapper)

    for name in mod.__all__:
        delegate_method(name)


def roll_data(filename, data, default=None):
    if os.path.exists(filename):
        with open(filename, 'r') as od:
            res = pickle.load(od)
        with open(filename, 'w') as od:
            pickle.dump(data, od)
        return res
    else:
        with open(filename, 'w') as od:
            pickle.dump(data, od)
        return default

