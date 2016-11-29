import attr
import collections
import functools

@attr.s(slots=True)
class LanguageModule(object):
    """
    This represents a collection of Vision keywords and the rules for
    how they're to be parsed, compiled, and interpreted.
    """
    name = attr.ib()
    requires = attr.ib(default=attr.Factory(collections.OrderedDict))

    _keywords = attr.ib(default=attr.Factory(list))
    _parse_rules = attr.ib(default=attr.Factory(
        functools.partial(
            collections.defaultdict, lambda: lambda self, , module=None: True)))
    _compile_rules = attr.ib(default=attr.Factory(
        functools.partial(
            collections.defaultdict, lambda: lambda self, ele=None, module=None: True)))
    _interpretation_rules = attr.ib(default=attr.Factory(
        functools.partial(
            collections.defaultdict, lambda: lambda self, ele=None, module=None: True)))

    def __init__(self, name, requires=None, defaults={}):
        self.name = name
        self._parse_rules.default_factory = defaults.get(
            'parse', self._parse_rules.default_factory)
        self._compile_rules.default_factory = defaults.get(
            'compile', self._compile_rules.default_factory)
        self._interpretation_rules.default_factory = defaults.get(
            'interpretation', self._interpretation_rules.default_factory)

    def add_keyword(self, keyword, parse=None, compile=None, interpret=None):
        self._keywords.append(keyword)
        if parse:
            self._parse_rules
