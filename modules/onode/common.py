

def delegate_methods(cls, mod):
    def delegate_method(name):
        fun = getattr(mod, name)

        def wrapper(self, *args, **kwargs):
            return fun(*args, **kwargs)
        wrapper.__name__ = name
        setattr(cls, name, wrapper)

    for name in mod.__all__:
        delegate_method(name)
