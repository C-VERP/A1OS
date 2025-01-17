# -*- coding: utf-8 -*-
import odoo
import werkzeug
from types import CodeType
from odoo.tools import ustr

from psycopg2 import OperationalError
from odoo.tools.safe_eval import check_values, _BUILTINS, _SAFE_OPCODES, test_expr, _logger

unsafe_eval = eval


class MarketplaceException(Exception):
    """Specific exception subclass for marketplace related errors"""

    def __init__(self, message, title=None, additional_context=None):
        super().__init__(message, title, additional_context)

def marketplace_safe_eval(expr, globals_dict=None, locals_dict=None, mode="eval", nocopy=False, locals_builtins=False, filename=None):
    """safe_eval(expression[, globals[, locals[, mode[, nocopy]]]]) -> result
    System-restricted Python expression evaluation
    Evaluates a string that contains an expression that mostly
    uses Python constants, arithmetic expressions and the
    objects directly provided in context.
    This can be used to e.g. evaluate
    an OpenERP domain expression from an untrusted source.
    :param filename: optional pseudo-filename for the compiled expression,
                     displayed for example in traceback frames
    :type filename: string
    :throws TypeError: If the expression provided is a code object
    :throws SyntaxError: If the expression provided is not valid Python
    :throws NameError: If the expression provided accesses forbidden names
    :throws ValueError: If the expression provided uses forbidden bytecode
    """
    if type(expr) is CodeType:
        raise TypeError("safe_eval does not allow direct evaluation of code objects.")
    # prevent altering the globals/locals from within the sandbox
    # by taking a copy.
    if not nocopy:
        # isinstance() does not work below, we want *exactly* the dict class
        if (globals_dict is not None and type(globals_dict) is not dict) \
                or (locals_dict is not None and type(locals_dict) is not dict):
            _logger.warning(
                "Looks like you are trying to pass a dynamic environment, "
                "you should probably pass nocopy=True to safe_eval().")
        if globals_dict is not None:
            globals_dict = dict(globals_dict)
        if locals_dict is not None:
            locals_dict = dict(locals_dict)
    check_values(globals_dict)
    check_values(locals_dict)
    if globals_dict is None:
        globals_dict = {}
    globals_dict['__builtins__'] = _BUILTINS
    if locals_builtins:
        if locals_dict is None:
            locals_dict = {}
        locals_dict.update(_BUILTINS)
    c = test_expr(expr, _SAFE_OPCODES, mode=mode, filename=filename)
    try:
        return unsafe_eval(c, globals_dict, locals_dict)
    except odoo.exceptions.UserError:
        raise
    except odoo.addons.base_marketplace.models.exceptions.MarketplaceException:
        raise
    except odoo.exceptions.RedirectWarning:
        raise
    except werkzeug.exceptions.HTTPException:
        raise
    except OperationalError:
        # Do not hide PostgreSQL low-level exceptions, to let the auto-replay
        # of serialized transactions work its magic
        raise
    except ZeroDivisionError:
        raise
    except Exception as e:
        raise ValueError('%r while evaluating\n%r' % (e, expr))
