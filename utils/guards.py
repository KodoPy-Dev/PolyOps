########################•########################
"""                   KodoPy                  """
########################•########################

import traceback

########################•########################
"""                 DECORATORS                """
########################•########################

def try_except_decorator(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            print(f"ERROR: {func.__name__}")
            traceback.print_exc()
    return wrapper

########################•########################
"""                   CATCH                   """
########################•########################

def except_guard(try_func=None, try_args=None):
    try:
        if not hasattr(try_func, '__call__'):
            raise ValueError("try_func not callable")
        if type(try_args) == tuple:
            return try_func(*try_args)
        else:
            return try_func()
    except Exception as e:
        if hasattr(try_func, '__name__'):
            print(try_func.__name__)
        traceback.print_exc()


def except_guard_callback(try_func=None, try_args=None, err_func=None, err_args=None):
    try:
        if not hasattr(try_func, '__call__'):
            raise ValueError("try_func not callable")
        if type(try_args) == tuple:
            return try_func(*try_args)
        else:
            return try_func()
    except Exception as e:
        if hasattr(try_func, '__name__'):
            print(try_func.__name__)
        traceback.print_exc()
        if hasattr(err_func, '__call__'):
            if type(err_args) == tuple:
                return err_func(*err_args)
            else:
                return err_func()


def except_guard_prop_set(try_func=None, try_args=None, err_ref_cls=None, err_prop_name=None, err_prop_val=None):
    try:
        if not hasattr(try_func, '__call__'):
            raise ValueError("try_func not callable")
        if type(try_args) == tuple:
            return try_func(*try_args)
        else:
            return try_func()
    except Exception as e:
        if hasattr(try_func, '__name__'):
            print(try_func.__name__)
        traceback.print_exc()

        if hasattr(err_ref_cls, '__class__'):
            if type(err_prop_name) == str:
                if hasattr(err_ref_cls, err_prop_name):
                    setattr(err_ref_cls, err_prop_name, err_prop_val)

