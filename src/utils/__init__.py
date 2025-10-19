class DotDict(dict):
    def __getattr__(self, key):
        return self[key]

    def __setattr__(self, key, value):
        self[key] = value

    def _call_func(self, key, val):
        new_val = val
        func_key = "function"
        if isinstance(val, dict) and val.get(func_key) and callable(val.get(func_key)):
            try:
                func = val.get(func_key)
                new_val = func(**{k: val[k] for k in val if k != func_key})
            except TypeError:
                new_val = val
            self[key] = new_val
        return new_val

    def __getitem__(self, key):
        res = super().__getitem__(key)
        res = self._call_func(key, res)

        if isinstance(res, dict):
            self[key] = DotDict(res)
        elif isinstance(res, list):
            for i in range(len(res)):
                if isinstance(res[i], dict):
                    res[i] = DotDict(res[i])
        return super().__getitem__(key)  # reload value again to get dotdict effect

    def __missing__(self, key):
        return rf"[~~missing-key-{key}~~]"

    def get(self, *args, **kwargs):
        res = super().get(*args, **kwargs)
        key = args[0] if args else kwargs.get("key")
        self._call_func(key, res)

        return super().get(*args, **kwargs)

    def values(self, is_raw=False):
        if is_raw:
            return super().values()
        _ = [self._call_func(key, val) for key, val in super().items()]
        return super().values()

    def items(self, is_raw=False):
        if is_raw:
            return super().items()
        _ = [self._call_func(key, val) for key, val in super().items()]
        return super().items()
