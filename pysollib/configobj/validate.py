# validate.py
# A Validator object
# Copyright (C) 2005 Michael Foord, Mark Andrews, Nicola Larosa
# E-mail: fuzzyman AT voidspace DOT org DOT uk
#         mark AT la-la DOT com
#         nico AT tekNico DOT net

# This software is licensed under the terms of the BSD license.
# http://www.voidspace.org.uk/python/license.shtml
# Basically you're free to copy, modify, distribute and relicense it,
# So long as you keep a copy of the license with it.

# Scripts maintained at http://www.voidspace.org.uk/python/index.shtml
# For information about bugfixes, updates and support, please join the
# ConfigObj mailing list:
# http://lists.sourceforge.net/lists/listinfo/configobj-develop
# Comments, suggestions and bug reports welcome.

"""
    The Validator object is used to check that supplied values 
    conform to a specification.
    
    The value can be supplied as a string - e.g. from a config file.
    In this case the check will also *convert* the value to
    the required type. This allows you to add validation
    as a transparent layer to access data stored as strings.
    The validation checks that the data is correct *and*
    converts it to the expected type.
    
    Some standard checks are provided for basic data types.
    Additional checks are easy to write. They can be
    provided when the ``Validator`` is instantiated or
    added afterwards.
    
    The standard functions work with the following basic data types :
    
    * integers
    * floats
    * booleans
    * strings
    * ip_addr
    
    plus lists of these datatypes
    
    Adding additional checks is done through coding simple functions.
    
    The full set of standard checks are : 
    
    * 'integer': matches integer values (including negative)
                 Takes optional 'min' and 'max' arguments : ::
    
                   integer()
                   integer(3, 9)  # any value from 3 to 9
                   integer(min=0) # any positive value
                   integer(max=9)
    
    * 'float': matches float values
               Has the same parameters as the integer check.
    
    * 'boolean': matches boolean values - ``True`` or ``False``
                 Acceptable string values for True are :
                   true, on, yes, 1
                 Acceptable string values for False are :
                   false, off, no, 0
    
                 Any other value raises an error.
    
    * 'ip_addr': matches an Internet Protocol address, v.4, represented
                 by a dotted-quad string, i.e. '1.2.3.4'.
    
    * 'string': matches any string.
                Takes optional keyword args 'min' and 'max'
                to specify min and max lengths of the string.
    
    * 'list': matches any list.
              Takes optional keyword args 'min', and 'max' to specify min and
              max sizes of the list.
    
    * 'int_list': Matches a list of integers.
                  Takes the same arguments as list.
    
    * 'float_list': Matches a list of floats.
                    Takes the same arguments as list.
    
    * 'bool_list': Matches a list of boolean values.
                   Takes the same arguments as list.
    
    * 'ip_addr_list': Matches a list of IP addresses.
                     Takes the same arguments as list.
    
    * 'string_list': Matches a list of strings.
                     Takes the same arguments as list.
    
    * 'mixed_list': Matches a list with different types in 
                    specific positions. List size must match
                    the number of arguments.
    
                    Each position can be one of :
                    'integer', 'float', 'ip_addr', 'string', 'boolean'
    
                    So to specify a list with two strings followed
                    by two integers, you write the check as : ::
    
                      mixed_list('string', 'string', 'integer', 'integer')
    
    * 'pass': This check matches everything ! It never fails
              and the value is unchanged.
    
              It is also the default if no check is specified.
    
    * 'option': This check matches any from a list of options.
                You specify this check with : ::
    
                  option('option 1', 'option 2', 'option 3')
    
    You can supply a default value (returned if no value is supplied)
    using the default keyword argument.
    
    You specify a list argument for default using a list constructor syntax in
    the check : ::
    
        checkname(arg1, arg2, default=list('val 1', 'val 2', 'val 3'))
    
    A badly formatted set of arguments will raise a ``VdtParamError``.
"""

__docformat__ = "restructuredtext en"

__version__ = '0.2.3'

__revision__ = '$Id: validate.py 123 2005-09-08 08:54:28Z fuzzyman $'

__all__ = (
    '__version__',
    'dottedQuadToNum',
    'numToDottedQuad',
    'ValidateError',
    'VdtUnknownCheckError',
    'VdtParamError',
    'VdtTypeError',
    'VdtValueError',
    'VdtValueTooSmallError',
    'VdtValueTooBigError',
    'VdtValueTooShortError',
    'VdtValueTooLongError',
    'VdtMissingValue',
    'Validator',
    'is_integer',
    'is_float',
    'is_boolean',
    'is_list',
    'is_ip_addr',
    'is_string',
    'is_int_list',
    'is_bool_list',
    'is_float_list',
    'is_string_list',
    'is_ip_addr_list',
    'is_mixed_list',
    'is_option',
    '__docformat__',
)

import sys
INTP_VER = sys.version_info[:2]
if INTP_VER < (2, 2):
    raise RuntimeError("Python v.2.2 or later needed")

import re
StringTypes = (str, unicode)


_list_arg = re.compile(r'''
    (?:
        ([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*list\(
            (
                (?:
                    \s*
                    (?:
                        (?:".*?")|              # double quotes
                        (?:'.*?')|              # single quotes
                        (?:[^'",\s\)][^,\)]*?)  # unquoted
                    )
                    \s*,\s*
                )*
                (?:
                    (?:".*?")|              # double quotes
                    (?:'.*?')|              # single quotes
                    (?:[^'",\s\)][^,\)]*?)  # unquoted
                )?                          # last one
            )
        \)
    )
''', re.VERBOSE)    # two groups

_list_members = re.compile(r'''
    (
        (?:".*?")|              # double quotes
        (?:'.*?')|              # single quotes
        (?:[^'",\s=][^,=]*?)       # unquoted
    )
    (?:
    (?:\s*,\s*)|(?:\s*$)            # comma
    )
''', re.VERBOSE)    # one group

_paramstring = r'''
    (?:
        (
            (?:
                [a-zA-Z_][a-zA-Z0-9_]*\s*=\s*list\(
                    (?:
                        \s*
                        (?:
                            (?:".*?")|              # double quotes
                            (?:'.*?')|              # single quotes
                            (?:[^'",\s\)][^,\)]*?)       # unquoted
                        )
                        \s*,\s*
                    )*
                    (?:
                        (?:".*?")|              # double quotes
                        (?:'.*?')|              # single quotes
                        (?:[^'",\s\)][^,\)]*?)       # unquoted
                    )?                              # last one
                \)
            )|
            (?:
                (?:".*?")|              # double quotes
                (?:'.*?')|              # single quotes
                (?:[^'",\s=][^,=]*?)|       # unquoted
                (?:                         # keyword argument
                    [a-zA-Z_][a-zA-Z0-9_]*\s*=\s*
                    (?:
                        (?:".*?")|              # double quotes
                        (?:'.*?')|              # single quotes
                        (?:[^'",\s=][^,=]*?)       # unquoted
                    )
                )
            )
        )
        (?:
            (?:\s*,\s*)|(?:\s*$)            # comma
        )
    )
    '''

_matchstring = '^%s*' % _paramstring

# Python pre 2.2.1 doesn't have bool
try:
    bool
except NameError:
    def bool(val):
        """Simple boolean equivalent function. """
        if val:
            return 1
        else:
            return 0

def dottedQuadToNum(ip):
    """
    Convert decimal dotted quad string to long integer
    
    >>> dottedQuadToNum('1 ')
    1L
    >>> dottedQuadToNum(' 1.2')
    16777218L
    >>> dottedQuadToNum(' 1.2.3 ')
    16908291L
    >>> dottedQuadToNum('1.2.3.4')
    16909060L
    >>> dottedQuadToNum('1.2.3. 4')
    Traceback (most recent call last):
    ValueError: Not a good dotted-quad IP: 1.2.3. 4
    >>> dottedQuadToNum('255.255.255.255')
    4294967295L
    >>> dottedQuadToNum('255.255.255.256')
    Traceback (most recent call last):
    ValueError: Not a good dotted-quad IP: 255.255.255.256
    """
    
    # import here to avoid it when ip_addr values are not used
    import socket, struct
    
    try:
        return struct.unpack('!L',
            socket.inet_aton(ip.strip()))[0]
    except socket.error:
        # bug in inet_aton, corrected in Python 2.3
        if ip.strip() == '255.255.255.255':
            return 0xFFFFFFFFL
        else:
            raise ValueError('Not a good dotted-quad IP: %s' % ip)
    return

def numToDottedQuad(num):
    """
    Convert long int to dotted quad string
    
    >>> numToDottedQuad(-1L)
    Traceback (most recent call last):
    ValueError: Not a good numeric IP: -1
    >>> numToDottedQuad(1L)
    '0.0.0.1'
    >>> numToDottedQuad(16777218L)
    '1.0.0.2'
    >>> numToDottedQuad(16908291L)
    '1.2.0.3'
    >>> numToDottedQuad(16909060L)
    '1.2.3.4'
    >>> numToDottedQuad(4294967295L)
    '255.255.255.255'
    >>> numToDottedQuad(4294967296L)
    Traceback (most recent call last):
    ValueError: Not a good numeric IP: 4294967296
    """
    
    # import here to avoid it when ip_addr values are not used
    import socket, struct
    
    # no need to intercept here, 4294967295L is fine
    try:
        return socket.inet_ntoa(
            struct.pack('!L', long(num)))
    except (socket.error, struct.error, OverflowError):
        raise ValueError('Not a good numeric IP: %s' % num)

class ValidateError(Exception):
    """
    This error indicates that the check failed.
    It can be the base class for more specific errors.
    
    Any check function that fails ought to raise this error.
    (or a subclass)
    
    >>> raise ValidateError
    Traceback (most recent call last):
    ValidateError
    """

class VdtMissingValue(ValidateError):
    """No value was supplied to a check that needed one."""

class VdtUnknownCheckError(ValidateError):
    """An unknown check function was requested"""

    def __init__(self, value):
        """
        >>> raise VdtUnknownCheckError('yoda')
        Traceback (most recent call last):
        VdtUnknownCheckError: the check "yoda" is unknown.
        """
        ValidateError.__init__(
            self,
            'the check "%s" is unknown.' % value)

class VdtParamError(SyntaxError):
    """An incorrect parameter was passed"""

    def __init__(self, name, value):
        """
        >>> raise VdtParamError('yoda', 'jedi')
        Traceback (most recent call last):
        VdtParamError: passed an incorrect value "jedi" for parameter "yoda".
        """
        SyntaxError.__init__(
            self,
            'passed an incorrect value "%s" for parameter "%s".' % (
                value, name))

class VdtTypeError(ValidateError):
    """The value supplied was of the wrong type"""

    def __init__(self, value):
        """
        >>> raise VdtTypeError('jedi')
        Traceback (most recent call last):
        VdtTypeError: the value "jedi" is of the wrong type.
        """
        ValidateError.__init__(
            self,
            'the value "%s" is of the wrong type.' % value)

class VdtValueError(ValidateError):
    """
    The value supplied was of the correct type, but was not an allowed value.
    """

    def __init__(self, value):
        """
        >>> raise VdtValueError('jedi')
        Traceback (most recent call last):
        VdtValueError: the value "jedi" is unacceptable.
        """
        ValidateError.__init__(
            self,
            'the value "%s" is unacceptable.' % value)

class VdtValueTooSmallError(VdtValueError):
    """The value supplied was of the correct type, but was too small."""

    def __init__(self, value):
        """
        >>> raise VdtValueTooSmallError('0')
        Traceback (most recent call last):
        VdtValueTooSmallError: the value "0" is too small.
        """
        ValidateError.__init__(
            self,
            'the value "%s" is too small.' % value)

class VdtValueTooBigError(VdtValueError):
    """The value supplied was of the correct type, but was too big."""

    def __init__(self, value):
        """
        >>> raise VdtValueTooBigError('1')
        Traceback (most recent call last):
        VdtValueTooBigError: the value "1" is too big.
        """
        ValidateError.__init__(
            self,
            'the value "%s" is too big.' % value)

class VdtValueTooShortError(VdtValueError):
    """The value supplied was of the correct type, but was too short."""

    def __init__(self, value):
        """
        >>> raise VdtValueTooShortError('jed')
        Traceback (most recent call last):
        VdtValueTooShortError: the value "jed" is too short.
        """
        ValidateError.__init__(
            self,
            'the value "%s" is too short.' % (value,))

class VdtValueTooLongError(VdtValueError):
    """The value supplied was of the correct type, but was too long."""

    def __init__(self, value):
        """
        >>> raise VdtValueTooLongError('jedie')
        Traceback (most recent call last):
        VdtValueTooLongError: the value "jedie" is too long.
        """
        ValidateError.__init__(
            self,
            'the value "%s" is too long.' %  (value,))

class Validator(object):
    """
        Validator is an object that allows you to register a set of 'checks'.
        These checks take input and test that it conforms to the check.
        
        This can also involve converting the value from a string into
        the correct datatype.
        
        The ``check`` method takes an input string which configures which
        check is to be used and applies that check to a supplied value.
        
        An example input string would be:
        'int_range(param1, param2)'
        
        You would then provide something like:
        
        >>> def int_range_check(value, min, max):
        ...     # turn min and max from strings to integers
        ...     min = int(min)
        ...     max = int(max)
        ...     # check that value is of the correct type.
        ...     # possible valid inputs are integers or strings
        ...     # that represent integers
        ...     if not isinstance(value, (int, long, StringTypes)):
        ...         raise VdtTypeError(value)
        ...     elif isinstance(value, StringTypes):
        ...         # if we are given a string
        ...         # attempt to convert to an integer
        ...         try:
        ...             value = int(value)
        ...         except ValueError:
        ...             raise VdtValueError(value)
        ...     # check the value is between our constraints
        ...     if not min <= value:
        ...          raise VdtValueTooSmallError(value)
        ...     if not value <= max:
        ...          raise VdtValueTooBigError(value)
        ...     return value
        
        >>> fdict = {'int_range': int_range_check}
        >>> vtr1 = Validator(fdict)
        >>> vtr1.check('int_range(20, 40)', '30')
        30
        >>> vtr1.check('int_range(20, 40)', '60')
        Traceback (most recent call last):
        VdtValueTooBigError: the value "60" is too big.
        
        New functions can be added with : ::
        
        >>> vtr2 = Validator()       
        >>> vtr2.functions['int_range'] = int_range_check
        
        Or by passing in a dictionary of functions when Validator 
        is instantiated.
        
        Your functions *can* use keyword arguments,
        but the first argument should always be 'value'.
        
        If the function doesn't take additional arguments,
        the parentheses are optional in the check.
        It can be written with either of : ::
        
            keyword = function_name
            keyword = function_name()
        
        The first program to utilise Validator() was Michael Foord's
        ConfigObj, an alternative to ConfigParser which supports lists and
        can validate a config file using a config schema.
        For more details on using Validator with ConfigObj see:
        http://www.voidspace.org.uk/python/configobj.html
    """

    # this regex does the initial parsing of the checks
    _func_re = re.compile(r'(.+?)\((.*)\)')

    # this regex takes apart keyword arguments
    _key_arg = re.compile(r'^([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*(.*)$')


    # this regex finds keyword=list(....) type values
    _list_arg = _list_arg

    # this regex takes individual values out of lists - in one pass
    _list_members = _list_members

    # These regexes check a set of arguments for validity
    # and then pull the members out
    _paramfinder = re.compile(_paramstring, re.VERBOSE)
    _matchfinder = re.compile(_matchstring, re.VERBOSE)


    def __init__(self, functions=None):
        """
        >>> vtri = Validator()
        """
        self.functions = {
            '': self._pass,
            'integer': is_integer,
            'float': is_float,
            'boolean': is_boolean,
            'ip_addr': is_ip_addr,
            'string': is_string,
            'list': is_list,
            'int_list': is_int_list,
            'float_list': is_float_list,
            'bool_list': is_bool_list,
            'ip_addr_list': is_ip_addr_list,
            'string_list': is_string_list,
            'mixed_list': is_mixed_list,
            'pass': self._pass,
            'option': is_option,
        }
        if functions is not None:
            self.functions.update(functions)
        # tekNico: for use by ConfigObj
        self.baseErrorClass = ValidateError

    def check(self, check, value, missing=False):
        """
        Usage: check(check, value)
        
        Arguments:
            check: string representing check to apply (including arguments)
            value: object to be checked
        Returns value, converted to correct type if necessary
        
        If the check fails, raises a ``ValidateError`` subclass.
        
        >>> vtor.check('yoda', '')
        Traceback (most recent call last):
        VdtUnknownCheckError: the check "yoda" is unknown.
        >>> vtor.check('yoda()', '')
        Traceback (most recent call last):
        VdtUnknownCheckError: the check "yoda" is unknown.
        """
        fun_match = self._func_re.match(check)
        if fun_match:
            fun_name = fun_match.group(1)
            arg_string = fun_match.group(2)
            arg_match = self._matchfinder.match(arg_string)
            if arg_match is None:
                # Bad syntax
                raise VdtParamError
            fun_args = []
            fun_kwargs = {}
            # pull out args of group 2
            for arg in self._paramfinder.findall(arg_string):
                # args may need whitespace removing (before removing quotes)
                arg = arg.strip()
                listmatch = self._list_arg.match(arg)
                if listmatch:
                    key, val = self._list_handle(listmatch)
                    fun_kwargs[key] = val
                    continue
                keymatch = self._key_arg.match(arg)
                if keymatch:
                    val = self._unquote(keymatch.group(2))
                    fun_kwargs[keymatch.group(1)] = val
                    continue
                #
                fun_args.append(self._unquote(arg))
        else:
            # allows for function names without (args)
            (fun_name, fun_args, fun_kwargs) = (check, (), {})
        #
        if missing:
            try:
                value = fun_kwargs['default']
            except KeyError:
                raise VdtMissingValue
            if value == 'None':
                value = None
        if value is None:
            return None
# tekNico: default must be deleted if the value is specified too,
# otherwise the check function will get a spurious "default" keyword arg
        try:
            del fun_kwargs['default']
        except KeyError:
            pass
        try:
            fun = self.functions[fun_name]
        except KeyError:
            raise VdtUnknownCheckError(fun_name)
        else:
##            print fun_args
##            print fun_kwargs
            return fun(value, *fun_args, **fun_kwargs)

    def _unquote(self, val):
        """Unquote a value if necessary."""
        if (len(val) > 2) and (val[0] in ("'", '"')) and (val[0] == val[-1]):
            val = val[1:-1]
        return val

    def _list_handle(self, listmatch):
        """Take apart a ``keyword=list('val, 'val')`` type string."""
        out = []
        name = listmatch.group(1)
        args = listmatch.group(2)
        for arg in self._list_members.findall(args):
            out.append(self._unquote(arg))
        return name, out

    def _pass(self, value):
        """
        Dummy check that always passes
        
        >>> vtor.check('', 0)
        0
        >>> vtor.check('', '0')
        '0'
        """
        return value


def _is_num_param(names, values, to_float=False):
    """
    Return numbers from inputs or raise VdtParamError.
    
    Lets ``None`` pass through.
    Pass in keyword argument ``to_float=True`` to
    use float for the conversion rather than int.
    
    >>> _is_num_param(('', ''), (0, 1.0))
    [0, 1]
    >>> _is_num_param(('', ''), (0, 1.0), to_float=True)
    [0.0, 1.0]
    >>> _is_num_param(('a'), ('a'))
    Traceback (most recent call last):
    VdtParamError: passed an incorrect value "a" for parameter "a".
    """
    fun = to_float and float or int
    out_params = []
    for (name, val) in zip(names, values):
        if val is None:
            out_params.append(val)
        elif isinstance(val, (int, long, float, StringTypes)):
            try:
                out_params.append(fun(val))
            except ValueError, e:
                raise VdtParamError(name, val)
        else:
            raise VdtParamError(name, val)
    return out_params

# built in checks
# you can override these by setting the appropriate name
# in Validator.functions
# note: if the params are specified wrongly in your input string,
#       you will also raise errors.

def is_integer(value, min=None, max=None):
    """
    A check that tests that a given value is an integer (int, or long)
    and optionally, between bounds. A negative value is accepted, while
    a float will fail.
    
    If the value is a string, then the conversion is done - if possible.
    Otherwise a VdtError is raised.
    
    >>> vtor.check('integer', '-1')
    -1
    >>> vtor.check('integer', '0')
    0
    >>> vtor.check('integer', 9)
    9
    >>> vtor.check('integer', 'a')
    Traceback (most recent call last):
    VdtTypeError: the value "a" is of the wrong type.
    >>> vtor.check('integer', '2.2')
    Traceback (most recent call last):
    VdtTypeError: the value "2.2" is of the wrong type.
    >>> vtor.check('integer(10)', '20')
    20
    >>> vtor.check('integer(max=20)', '15')
    15
    >>> vtor.check('integer(10)', '9')
    Traceback (most recent call last):
    VdtValueTooSmallError: the value "9" is too small.
    >>> vtor.check('integer(10)', 9)
    Traceback (most recent call last):
    VdtValueTooSmallError: the value "9" is too small.
    >>> vtor.check('integer(max=20)', '35')
    Traceback (most recent call last):
    VdtValueTooBigError: the value "35" is too big.
    >>> vtor.check('integer(max=20)', 35)
    Traceback (most recent call last):
    VdtValueTooBigError: the value "35" is too big.
    >>> vtor.check('integer(0, 9)', False)
    0
    """
#    print value, type(value)
    (min_val, max_val) = _is_num_param(('min', 'max'), (min, max))
    if not isinstance(value, (int, long, StringTypes)):
        raise VdtTypeError(value)
    if isinstance(value, StringTypes):
        # if it's a string - does it represent an integer ?
        try:
            value = int(value)
        except ValueError:
            raise VdtTypeError(value)
    if (min_val is not None) and (value < min_val):
        raise VdtValueTooSmallError(value)
    if (max_val is not None) and (value > max_val):
        raise VdtValueTooBigError(value)
    return value

def is_float(value, min=None, max=None):
    """
    A check that tests that a given value is a float
    (an integer will be accepted), and optionally - that it is between bounds.
    
    If the value is a string, then the conversion is done - if possible.
    Otherwise a VdtError is raised.
    
    This can accept negative values.
    
    >>> vtor.check('float', '2')
    2.0
    
    From now on we multiply the value to avoid comparing decimals
    
    >>> vtor.check('float', '-6.8') * 10
    -68.0
    >>> vtor.check('float', '12.2') * 10
    122.0
    >>> vtor.check('float', 8.4) * 10
    84.0
    >>> vtor.check('float', 'a')
    Traceback (most recent call last):
    VdtTypeError: the value "a" is of the wrong type.
    >>> vtor.check('float(10.1)', '10.2') * 10
    102.0
    >>> vtor.check('float(max=20.2)', '15.1') * 10
    151.0
    >>> vtor.check('float(10.0)', '9.0')
    Traceback (most recent call last):
    VdtValueTooSmallError: the value "9.0" is too small.
    >>> vtor.check('float(max=20.0)', '35.0')
    Traceback (most recent call last):
    VdtValueTooBigError: the value "35.0" is too big.
    """
    (min_val, max_val) = _is_num_param(
        ('min', 'max'), (min, max), to_float=True)
    if not isinstance(value, (int, long, float, StringTypes)):
        raise VdtTypeError(value)
    if not isinstance(value, float):
        # if it's a string - does it represent a float ?
        try:
            value = float(value)
        except ValueError:
            raise VdtTypeError(value)
    if (min_val is not None) and (value < min_val):
        raise VdtValueTooSmallError(value)
    if (max_val is not None) and (value > max_val):
        raise VdtValueTooBigError(value)
    return value

bool_dict = {
    True: True, 'on': True, '1': True, 'true': True, 'yes': True, 
    False: False, 'off': False, '0': False, 'false': False, 'no': False,
}

def is_boolean(value):
    """
    Check if the value represents a boolean.
    
    >>> vtor.check('boolean', 0)
    0
    >>> vtor.check('boolean', False)
    0
    >>> vtor.check('boolean', '0')
    0
    >>> vtor.check('boolean', 'off')
    0
    >>> vtor.check('boolean', 'false')
    0
    >>> vtor.check('boolean', 'no')
    0
    >>> vtor.check('boolean', 'nO')
    0
    >>> vtor.check('boolean', 'NO')
    0
    >>> vtor.check('boolean', 1)
    1
    >>> vtor.check('boolean', True)
    1
    >>> vtor.check('boolean', '1')
    1
    >>> vtor.check('boolean', 'on')
    1
    >>> vtor.check('boolean', 'true')
    1
    >>> vtor.check('boolean', 'yes')
    1
    >>> vtor.check('boolean', 'Yes')
    1
    >>> vtor.check('boolean', 'YES')
    1
    >>> vtor.check('boolean', '')
    Traceback (most recent call last):
    VdtTypeError: the value "" is of the wrong type.
    >>> vtor.check('boolean', 'up')
    Traceback (most recent call last):
    VdtTypeError: the value "up" is of the wrong type.
    
    """
    if isinstance(value, StringTypes):
        try:
            return bool_dict[value.lower()]
        except KeyError:
            raise VdtTypeError(value)
    # we do an equality test rather than an identity test
    # this ensures Python 2.2 compatibilty
    # and allows 0 and 1 to represent True and False
    if value == False:
        return False
    elif value == True:
        return True
    else:
        raise VdtTypeError(value)


def is_ip_addr(value):
    """
    Check that the supplied value is an Internet Protocol address, v.4,
    represented by a dotted-quad string, i.e. '1.2.3.4'.
    
    >>> vtor.check('ip_addr', '1 ')
    '1'
    >>> vtor.check('ip_addr', ' 1.2')
    '1.2'
    >>> vtor.check('ip_addr', ' 1.2.3 ')
    '1.2.3'
    >>> vtor.check('ip_addr', '1.2.3.4')
    '1.2.3.4'
    >>> vtor.check('ip_addr', '0.0.0.0')
    '0.0.0.0'
    >>> vtor.check('ip_addr', '255.255.255.255')
    '255.255.255.255'
    >>> vtor.check('ip_addr', '255.255.255.256')
    Traceback (most recent call last):
    VdtValueError: the value "255.255.255.256" is unacceptable.
    >>> vtor.check('ip_addr', '1.2.3.4.5')
    Traceback (most recent call last):
    VdtValueError: the value "1.2.3.4.5" is unacceptable.
    >>> vtor.check('ip_addr', '1.2.3. 4')
    Traceback (most recent call last):
    VdtValueError: the value "1.2.3. 4" is unacceptable.
    >>> vtor.check('ip_addr', 0)
    Traceback (most recent call last):
    VdtTypeError: the value "0" is of the wrong type.
    """
    if not isinstance(value, StringTypes):
        raise VdtTypeError(value)
    value = value.strip()
    try:
        dottedQuadToNum(value)
    except ValueError:
        raise VdtValueError(value)
    return value

def is_list(value, min=None, max=None):
    """
    Check that the value is a list of values.
    
    You can optionally specify the minimum and maximum number of members.
    
    It does no check on list members.
    
    >>> vtor.check('list', ())
    ()
    >>> vtor.check('list', [])
    []
    >>> vtor.check('list', (1, 2))
    (1, 2)
    >>> vtor.check('list', [1, 2])
    [1, 2]
    >>> vtor.check('list', '12')
    '12'
    >>> vtor.check('list(3)', (1, 2))
    Traceback (most recent call last):
    VdtValueTooShortError: the value "(1, 2)" is too short.
    >>> vtor.check('list(max=5)', (1, 2, 3, 4, 5, 6))
    Traceback (most recent call last):
    VdtValueTooLongError: the value "(1, 2, 3, 4, 5, 6)" is too long.
    >>> vtor.check('list(min=3, max=5)', (1, 2, 3, 4))
    (1, 2, 3, 4)
    >>> vtor.check('list', 0)
    Traceback (most recent call last):
    VdtTypeError: the value "0" is of the wrong type.
    """
    (min_len, max_len) = _is_num_param(('min', 'max'), (min, max))
    try:
        num_members = len(value)
    except TypeError:
        raise VdtTypeError(value)
    if min_len is not None and num_members < min_len:
        raise VdtValueTooShortError(value)
    if max_len is not None and num_members > max_len:
        raise VdtValueTooLongError(value)
    return value

def is_string(value, min=None, max=None):
    """
    Check that the supplied value is a string.
    
    You can optionally specify the minimum and maximum number of members.
    
    >>> vtor.check('string', '0')
    '0'
    >>> vtor.check('string', 0)
    Traceback (most recent call last):
    VdtTypeError: the value "0" is of the wrong type.
    >>> vtor.check('string(2)', '12')
    '12'
    >>> vtor.check('string(2)', '1')
    Traceback (most recent call last):
    VdtValueTooShortError: the value "1" is too short.
    >>> vtor.check('string(min=2, max=3)', '123')
    '123'
    >>> vtor.check('string(min=2, max=3)', '1234')
    Traceback (most recent call last):
    VdtValueTooLongError: the value "1234" is too long.
    """
    if not isinstance(value, StringTypes):
        raise VdtTypeError(value)
    (min_len, max_len) = _is_num_param(('min', 'max'), (min, max))
    try:
        num_members = len(value)
    except TypeError:
        raise VdtTypeError(value)
    if min_len is not None and num_members < min_len:
        raise VdtValueTooShortError(value)
    if max_len is not None and num_members > max_len:
        raise VdtValueTooLongError(value)
    return value

def is_int_list(value, min=None, max=None):
    """
    Check that the value is a list of integers.
    
    You can optionally specify the minimum and maximum number of members.
    
    Each list member is checked that it is an integer.
    
    >>> vtor.check('int_list', ())
    []
    >>> vtor.check('int_list', [])
    []
    >>> vtor.check('int_list', (1, 2))
    [1, 2]
    >>> vtor.check('int_list', [1, 2])
    [1, 2]
    >>> vtor.check('int_list', [1, 'a'])
    Traceback (most recent call last):
    VdtTypeError: the value "a" is of the wrong type.
    """
    return [is_integer(mem) for mem in is_list(value, min, max)]

def is_bool_list(value, min=None, max=None):
    """
    Check that the value is a list of booleans.
    
    You can optionally specify the minimum and maximum number of members.
    
    Each list member is checked that it is a boolean.
    
    >>> vtor.check('bool_list', ())
    []
    >>> vtor.check('bool_list', [])
    []
    >>> check_res = vtor.check('bool_list', (True, False))
    >>> check_res == [True, False]
    1
    >>> check_res = vtor.check('bool_list', [True, False])
    >>> check_res == [True, False]
    1
    >>> vtor.check('bool_list', [True, 'a'])
    Traceback (most recent call last):
    VdtTypeError: the value "a" is of the wrong type.
    """
    return [is_boolean(mem) for mem in is_list(value, min, max)]

def is_float_list(value, min=None, max=None):
    """
    Check that the value is a list of floats.
    
    You can optionally specify the minimum and maximum number of members.
    
    Each list member is checked that it is a float.
    
    >>> vtor.check('float_list', ())
    []
    >>> vtor.check('float_list', [])
    []
    >>> vtor.check('float_list', (1, 2.0))
    [1.0, 2.0]
    >>> vtor.check('float_list', [1, 2.0])
    [1.0, 2.0]
    >>> vtor.check('float_list', [1, 'a'])
    Traceback (most recent call last):
    VdtTypeError: the value "a" is of the wrong type.
    """
    return [is_float(mem) for mem in is_list(value, min, max)]

def is_string_list(value, min=None, max=None):
    """
    Check that the value is a list of strings.
    
    You can optionally specify the minimum and maximum number of members.
    
    Each list member is checked that it is a string.
    
    >>> vtor.check('string_list', ())
    []
    >>> vtor.check('string_list', [])
    []
    >>> vtor.check('string_list', ('a', 'b'))
    ['a', 'b']
    >>> vtor.check('string_list', ['a', 1])
    Traceback (most recent call last):
    VdtTypeError: the value "1" is of the wrong type.
    >>> vtor.check('string_list', 'hello')
    Traceback (most recent call last):
    VdtTypeError: the value "hello" is of the wrong type.
    """
    if isinstance(value, StringTypes):
        raise VdtTypeError(value)
    return [is_string(mem) for mem in is_list(value, min, max)]

def is_ip_addr_list(value, min=None, max=None):
    """
    Check that the value is a list of IP addresses.
    
    You can optionally specify the minimum and maximum number of members.
    
    Each list member is checked that it is an IP address.
    
    >>> vtor.check('ip_addr_list', ())
    []
    >>> vtor.check('ip_addr_list', [])
    []
    >>> vtor.check('ip_addr_list', ('1.2.3.4', '5.6.7.8'))
    ['1.2.3.4', '5.6.7.8']
    >>> vtor.check('ip_addr_list', ['a'])
    Traceback (most recent call last):
    VdtValueError: the value "a" is unacceptable.
    """
    return [is_ip_addr(mem) for mem in is_list(value, min, max)]

fun_dict = {
    'integer': is_integer,
    'float': is_float,
    'ip_addr': is_ip_addr,
    'string': is_string,
    'boolean': is_boolean,
}

def is_mixed_list(value, *args):
    """
    Check that the value is a list.
    Allow specifying the type of each member.
    Work on lists of specific lengths.
    
    You specify each member as a positional argument specifying type
    
    Each type should be one of the following strings :
      'integer', 'float', 'ip_addr', 'string', 'boolean'
    
    So you can specify a list of two strings, followed by
    two integers as :
    
      mixed_list('string', 'string', 'integer', 'integer')
    
    The length of the list must match the number of positional
    arguments you supply.
    
    >>> mix_str = "mixed_list('integer', 'float', 'ip_addr', 'string', 'boolean')"
    >>> check_res = vtor.check(mix_str, (1, 2.0, '1.2.3.4', 'a', True))
    >>> check_res == [1, 2.0, '1.2.3.4', 'a', True]
    1
    >>> check_res = vtor.check(mix_str, ('1', '2.0', '1.2.3.4', 'a', 'True'))
    >>> check_res == [1, 2.0, '1.2.3.4', 'a', True]
    1
    >>> vtor.check(mix_str, ('b', 2.0, '1.2.3.4', 'a', True))
    Traceback (most recent call last):
    VdtTypeError: the value "b" is of the wrong type.
    >>> vtor.check(mix_str, (1, 2.0, '1.2.3.4', 'a'))
    Traceback (most recent call last):
    VdtValueTooShortError: the value "(1, 2.0, '1.2.3.4', 'a')" is too short.
    >>> vtor.check(mix_str, (1, 2.0, '1.2.3.4', 'a', 1, 'b'))
    Traceback (most recent call last):
    VdtValueTooLongError: the value "(1, 2.0, '1.2.3.4', 'a', 1, 'b')" is too long.
    >>> vtor.check(mix_str, 0)
    Traceback (most recent call last):
    VdtTypeError: the value "0" is of the wrong type.
    
    This test requires an elaborate setup, because of a change in error string
    output from the interpreter between Python 2.2 and 2.3 .
    
    >>> res_seq = (
    ...     'passed an incorrect value "',
    ...     'yoda',
    ...     '" for parameter "mixed_list".',
    ... )
    >>> if INTP_VER == (2, 2):
    ...     res_str = "".join(res_seq)
    ... else:
    ...     res_str = "'".join(res_seq)
    >>> try:
    ...     vtor.check('mixed_list("yoda")', ('a'))
    ... except VdtParamError, err:
    ...     str(err) == res_str
    1
    """
    try:
        length = len(value)
    except TypeError:
        raise VdtTypeError(value)
    if length < len(args):
        raise VdtValueTooShortError(value)
    elif length > len(args):
        raise VdtValueTooLongError(value)
    try:
        return [fun_dict[arg](val) for arg, val in zip(args, value)]
    except KeyError, e:
        raise VdtParamError('mixed_list', e)

def is_option(value, *options):
    """
    This check matches the value to any of a set of options.
    
    >>> vtor.check('option("yoda", "jedi")', 'yoda')
    'yoda'
    >>> vtor.check('option("yoda", "jedi")', 'jed')
    Traceback (most recent call last):
    VdtValueError: the value "jed" is unacceptable.
    >>> vtor.check('option("yoda", "jedi")', 0)
    Traceback (most recent call last):
    VdtTypeError: the value "0" is of the wrong type.
    """
    if not isinstance(value, StringTypes):
        raise VdtTypeError(value)
    if not value in options:
        raise VdtValueError(value)
    return value

def _test(value, *args, **keywargs):
    """
    A function that exists for test purposes.
    
    >>> checks = [
    ...     '3, 6, min=1, max=3, test=list(a, b, c)',
    ...     '3',
    ...     '3, 6',
    ...     '3,',
    ...     'min=1, test="a b c"',
    ...     'min=5, test="a, b, c"',
    ...     'min=1, max=3, test="a, b, c"',
    ...     'min=-100, test=-99',
    ...     'min=1, max=3',
    ...     '3, 6, test="36"',
    ...     '3, 6, test="a, b, c"',
    ...     '3, max=3, test=list("a", "b", "c")',
    ...     '''3, max=3, test=list("'a'", 'b', "x=(c)")''',
    ...     "test='x=fish(3)'",
    ...    ]
    >>> v = Validator({'test': _test})
    >>> for entry in checks:
    ...     print v.check(('test(%s)' % entry), 3)
    (3, ('3', '6'), {'test': ['a', 'b', 'c'], 'max': '3', 'min': '1'})
    (3, ('3',), {})
    (3, ('3', '6'), {})
    (3, ('3',), {})
    (3, (), {'test': 'a b c', 'min': '1'})
    (3, (), {'test': 'a, b, c', 'min': '5'})
    (3, (), {'test': 'a, b, c', 'max': '3', 'min': '1'})
    (3, (), {'test': '-99', 'min': '-100'})
    (3, (), {'max': '3', 'min': '1'})
    (3, ('3', '6'), {'test': '36'})
    (3, ('3', '6'), {'test': 'a, b, c'})
    (3, ('3',), {'test': ['a', 'b', 'c'], 'max': '3'})
    (3, ('3',), {'test': ["'a'", 'b', 'x=(c)'], 'max': '3'})
    (3, (), {'test': 'x=fish(3)'})
    """
    return (value, args, keywargs)


if __name__ == '__main__':
    # run the code tests in doctest format
    import doctest
    m = sys.modules.get('__main__')
    globs = m.__dict__.copy()
    globs.update({
        'INTP_VER': INTP_VER,
        'vtor': Validator(),
    })
    doctest.testmod(m, globs=globs)

"""
    TODO
    ====
    
    Consider which parts of the regex stuff to put back in
    
    Can we implement a timestamp datatype ? (check DateUtil module)
    
    ISSUES
    ======
    
    If we could pull tuples out of arguments, it would be easier
    to specify arguments for 'mixed_lists'.
    
    CHANGELOG
    =========
    
    2006/12/17
    ----------
    
    By Nicola Larosa
    
    Fixed validate doc to talk of ``boolean`` instead of ``bool``, changed the
    ``is_bool`` function to ``is_boolean`` (Sourceforge bug #1531525).
    
    2006/04/23
    ----------
    
    Addressed bug where a string would pass the ``is_list`` test. (Thanks to
    Konrad Wojas.)
    
    2005/12/16
    ----------
    
    Fixed bug so we can handle keyword argument values with commas.
    
    We now use a list constructor for passing list values to keyword arguments
    (including ``default``) : ::
    
        default=list("val", "val", "val")
    
    Added the ``_test`` test. {sm;:-)}
    
    0.2.1
    
    2005/12/12
    ----------
    
    Moved a function call outside a try...except block.
    
    2005/08/25
    ----------
    
    Most errors now prefixed ``Vdt``
    
    ``VdtParamError`` no longer derives from ``VdtError``
    
    Finalised as version 0.2.0
    
    2005/08/21
    ----------
    
    By Nicola Larosa
    
    Removed the "length" argument for lists and strings, and related tests
    
    2005/08/16
    ----------
    
    By Nicola Larosa
    
    Deleted the "none" and "multiple" types and checks
    
    Added the None value for all types in Validation.check
    
    2005/08/14
    ----------
    
    By Michael Foord
    
    Removed timestamp.
    
    By Nicola Larosa
    
    Fixed bug in Validator.check: when a value that has a default is also
    specified in the config file, the default must be deleted from fun_kwargs
    anyway, otherwise the check function will get a spurious "default" keyword
    argument
    
    Added "ip_addr_list" check
    
    2005/08/13
    ----------
    
    By Nicola Larosa
    
    Updated comments at top
    
    2005/08/11
    ----------
    
    By Nicola Larosa
    
    Added test for interpreter version: raises RuntimeError if earlier than
    2.2
    
    Fixed last is_mixed_list test to work on Python 2.2 too
    
    2005/08/10
    ----------
    
    By Nicola Larosa
    
    Restored Python2.2 compatibility by avoiding usage of dict.pop
    
    2005/08/07
    ----------
    
    By Nicola Larosa
    
    Adjusted doctests for Python 2.2.3 compatibility, one test still fails
    for trivial reasons (string output delimiters)
    
    2005/08/05
    ----------
    
    By Michael Foord
    
    Added __version__, __all__, and __docformat__
    
    Replaced ``basestring`` with ``types.StringTypes``
    
    2005/07/28
    ----------
    
    By Nicola Larosa
    
    Reformatted final docstring in ReST format, indented it for easier folding
    
    2005/07/20
    ----------
    
    By Nicola Larosa
    
    Added an 'ip_addr' IPv4 address value check, with tests
    
    Updated the tests for mixed_list to include IP addresses
    
    Changed all references to value "tests" into value "checks", including
    the main Validator method, and all code tests
    
    2005/07/19
    ----------
    
    By Nicola Larosa
    
    Added even more code tests
    
    Refined the mixed_list check
    
    2005/07/18
    ----------
    
    By Nicola Larosa
    
    Introduced more VdtValueError subclasses
    
    Collapsed the ``_function_test`` and ``_function_parse`` methods into the
    ``check`` one
    
    Refined the value checks, using the new VdtValueError subclasses
    
    Changed "is_string" to use "is_list"
    
    Added many more code tests
    
    Changed the "bool" value type to "boolean"
    
    Some more code cleanup
    
    2005/07/17
    ----------
    
    By Nicola Larosa
    
    Code tests converted to doctest format and placed in the respective
    docstrings, so they are automatically checked, and easier to update
    
    Changed local vars "min" and "max" to "min_len", "max_len", "min_val" and
    "max_val", to avoid shadowing the builtin functions (but left function
    parameters alone)
    
    Uniformed value check function names to is_* convention
    
    ``date`` type name changed to ``timestamp``
    
    Avoided some code duplication in list check functions
    
    Some more code cleanup
    
    2005/07/09
    ----------
    
    Recoded the standard functions
    
    2005/07/08
    ----------
    
    Improved paramfinder regex
    
    Ripped out all the regex stuff, checks, and the example functions
    (to be replaced !)
    
    2005/07/06
    ----------
    
    By Nicola Larosa
    
    Code cleanup
"""

