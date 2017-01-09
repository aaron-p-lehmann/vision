"""
This file implements Modules and Definitions.
"""

# Python Libraries
import attr
import pprint
import ordered_set
import collections
import importlib
import copy
import itertools

# Vision Libraries
import tokens

# Make collections.Sequence an abc for ordered_set.OrderedSet
collections.Sequence.register(ordered_set.OrderedSet)

class RemovedDefinition(Exception):
    pass

@attr.s(slots=True)
class Lexicon(object):
    """
    This is an ephemeral object that keeps track of what modules are
    currently available and supplies the definitions for the currently
    available keywords, after merging them together.

    First, we'll make a couple of Modules for testing with.
    >>> module1 = Module(name='module1')
    >>> module1.add_definition(FullDefinition(
    ...   name='click',
    ...   token_type=tokens.Verb,
    ...   consumers={
    ...     tokens.Command: {},},
    ...   outputters={
    ...     'raw': lambda token: "Raw output module1",
    ...     'prettified': lambda token: "Prettified output module1",},
    ...   interpretations={
    ...     tokens.Command: lambda token, interpreter: "Clicked a thing in module1!"},))
    >>> module2 = Module(name='module2')
    >>> module2.add_definition(FullDefinition(
    ...   name='click',
    ...   token_type=tokens.Verb,
    ...   consumers={
    ...     tokens.Command: {},},
    ...   outputters={
    ...     'raw': lambda token: "Raw output module2",
    ...     'prettified': lambda token: "Prettified output module2",},
    ...   interpretations={
    ...     tokens.Command: lambda token, interpreter: "Clicked a thing in module2!"},))

    Now make a Lexicon.
    >>> Lexicon(modules=ordered_set.OrderedSet([module1]))
    Lexicon(modules=OrderedSet([Module(name='module1')]))

    Lexicons raise exceptions if modules isn't provided...
    >>> Lexicon()
    Traceback (most recent call last):
      ...
    TypeError: __init__() takes exactly 2 arguments (1 given)

    Or if it is not an OrderedSet...
    >>> Lexicon(modules=None)
    Traceback (most recent call last):
      ...
    TypeError: 'NoneType' object is not iterable

    Or if it contains elements that are not modules.
    >>> Lexicon(modules=ordered_set.OrderedSet([5])) #doctest: +ELLIPSIS
    Traceback (most recent call last):
      ...
    TypeError: ("'modules' must be <class '__main__.Module'> (got 5 that is a <type 'int'>).", Attribute(name='modules', default=NOTHING, validator=<function <lambda> at 0x...>, repr=True, cmp=True, hash=True, init=True, convert=None, metadata=mappingproxy({})), <class '__main__.Module'>, 5)
    """

    modules = attr.ib(
        validator=lambda self, name, value: (
            attr.validators.instance_of(ordered_set.OrderedSet),
            [attr.validators.instance_of(Module)(self, name, v) for v in value]))
    """
    modules is an OrderedSet of the modules that are used to make up
    this Lexicon.  They must be ordered in the order they appeared in
    the script.
    """

    def __getitem__(self, key):
        """
        This gets the definition for a keyword from the Lexicon.  This
        defintion will be made by using the update of all the
        definitions associated with the keyword and any defintions
        associated with classes in its MRO.

        First, we'll make two modules to use for our testing.
        >>> module1 = Module(name='module1')
        >>> module1.add_definition(FullDefinition(
        ...   name='click',
        ...   token_type=tokens.Verb,
        ...   consumers={
        ...     tokens.Command: {'preconsume': lambda token, interpreter: "preconsume on click in module1"}}))
        >>> module1.add_definition(FullDefinition(
        ...   name=None,
        ...   token_type=tokens.Verb,
        ...   consumers={
        ...     tokens.Command: {'postconsume': lambda token, interpreter: "postconsume on Verb in module1"}}))
        >>> module2 = Module(name='module2')
        >>> module2.add_definition(FullDefinition(
        ...   name='click',
        ...   token_type=tokens.Verb,
        ...   consumers={
        ...     tokens.Command: {'preconsume': lambda token, interpreter: "preconsume on click in module2"}}))

        We'll make a Lexicon with module1, to see that we can get
        definitions based on keywords from a Lexicon.
        >>> lex1 = Lexicon(modules=ordered_set.OrderedSet([module1]))
        >>> lex1_click = lex1['click']
        >>> lex1_click.consumers[tokens.Command]['preconsume'](None, None)
        'preconsume on click in module1'
        >>> lex1_click.consumers[tokens.Command]['postconsume'](None, None)
        'postconsume on Verb in module1'

        Lexicons get their definitions with later modules in the set
        given preference to earlier ones.
        Since module2 is later in the modules list in the following
        Lexicon, its preconsume will shadow the one from module1.
        >>> lex2 = Lexicon(modules=ordered_set.OrderedSet([module1, module2]))
        >>> lex2_click = lex2['click']
        >>> lex2_click.consumers[tokens.Command]['preconsume'](None, None)
        'preconsume on click in module2'
        >>> lex2_click.consumers[tokens.Command]['postconsume'](None, None)
        'postconsume on Verb in module1'

        The following Lexicon will have module1 last, and so its
        consumers will dominate.
        >>> lex3 = Lexicon(modules=ordered_set.OrderedSet([module2, module1]))
        >>> lex3_click = lex3['click']
        >>> lex3_click.consumers[tokens.Command]['preconsume'](None, None)
        'preconsume on click in module1'
        >>> lex3_click.consumers[tokens.Command]['postconsume'](None, None)
        'postconsume on Verb in module1'
        """
        token_type = None
        module_definition = collections.OrderedDict()

        # Find out what token_type this key maps to.  Look in the most
        # recent module possible, because recent shadows old.
        for module in reversed(self.modules):
            if key in module:
                if module[key]:
                    # This is a real definition, and not a mark for
                    # removal, so get it's token_type
                    token_type = module[key].token_type
                break
        else:
            raise KeyError(key)

        if not token_type:
            # If we haven't found a token_type, it's because this
            # keyword was removed here.  raise KeyError
            raise KeyError(key)

        # Create a new Defition, then update it using definitions from
        # all modules
        definition = None
        for module in self.modules:
            try:
                defn = module[key, token_type]
            except RemovedDefinition as rd:
                definition = None
            else:
                if not definition:
                    definition = FullDefinition(
                        name=key,
                        token_type=token_type)
                definition.update(DefinitionAlias(
                    name=key,
                    target=defn))

        if not definition:
            raise KeyError(key)

        return definition

@attr.s(
    slots=True,
    hash=False)
class Module(object):
    """
    A group of Definitions, and the methods necessary to merge modules
    into combination modules.

    Modules hold definitions for how to handle the different keywords in
    a particular module, such as a module for handling jqWidgets, or for
    basic modules, like the one for html.

    >>> module = Module(name='testmodule')
    >>> module
    Module(name='testmodule')

    Modules have a mapping of root token types to the class that
    actually implements them, called module_tokens.  By default, this is
    just a mapping of each class descended from ParseUnit in the tokens
    module to itself.
    >>> pprint.pprint(module.module_tokens)
    {}

    Modules have a mapping of definition names to their respective
    definitions.
    >>> pprint.pprint(module.definitions)
    {}

    Modules can require other modules to already be loaded.  The
    required_modules tuple keeps those modules, and the order in which
    they must be loaded.  We'll add a couple more modules so that they
    can require one another to demonstrate.
    >>> module2 = Module(
    ...   name='testmodule2',
    ...   required_modules=ordered_set.OrderedSet([
    ...     module,
    ...     Module(name='testmodule1a')]))
    >>> pprint.pprint(module2.required_modules)
    OrderedSet([Module(name='testmodule'), Module(name='testmodule1a')])
    """

    name = attr.ib(
        validator=attr.validators.instance_of(str))
    module_tokens = attr.ib(
        default=attr.Factory(dict),
        validator=lambda self, name, value: (
            attr.validators.instance_of(collections.Mapping),
            self._validate_module_tokens(name, value)),
        repr=False)
    definitions = attr.ib(
        default=attr.Factory(dict),
        init=False,
        validator=lambda self, name, value: (
            attr.validators.instance_of(collections.MutableMapping),
            self._validate_definitions(name, value)),
        repr=False)
    required_modules = attr.ib(
        default=attr.Factory(ordered_set.OrderedSet),
        validator=lambda self, name, value: (
            attr.validators.instance_of(ordered_set.OrderedSet)(self, name, value) and 
            [attr.validators.instance_of(Module)(self, name, v) for v in value]),
        repr=False)

    def __attrs_post_init__(self):
        """
        This builds the default token mapping for this class.
        Subclasses of Module will need to override this method if they
        have another python module to get their tokens from.

        Also loads all the Vision modules that are in the
        required_modules list.
        """

        default = dict([
            (gatattr(tokens, token), getattr(tokens, token))
            for token in dir(tokens)
            if isinstance(getattr(tokens, token), tokens.ParseUnit)])
        default.update(self.module_tokens)
        self.module_tokens = default

    def __hash__(self):
        return hash(self.name)

    def __contains__(self, key):
        return key in self.definitions

    def __getitem__(self, keyword):
        """
        This allows Modules to be indexed like dictionaries.  If a
        string is provided as the argument, it will be treated like a
        keyword.  If a 2-tuple is provided, it will be treated as
        keyword and the type of token it maps to.  The return value a
        new FullDefinition created by merging all applicable default
        Definitions, from closest to ParseUnit to furthest, and then any
        definition for the keyword.

        First, we'll make a module.
        >>> module = Module(name='module')

        Since it has no definitions, trying to get definitions will
        result in a KeyError.
        >>> module['click']
        Traceback (most recent call last):
          ...
        KeyError: 'click'
        >>> module['click', tokens.Verb]
        FullDefinition(token_type=<class 'tokens.Verb'>, title='click', pattern='click')

        We'll add a definition for the 'click' keyword, and get a
        definition from the module by keyword.  We'll also make a
        function that prints some text, so that we can call the hooks.
        >>> click = FullDefinition(
        ...   name='click',
        ...   token_type=tokens.Verb,
        ...   consumers={
        ...     tokens.Command: {'preconsume': lambda token, interpreter: "preconsume on click"}})
        >>> module.add_definition(click)
        >>> module_click = module['click']

        The new definition is not the same as the one we added to the
        module, but it has all the same stuff.
        >>> module_click is not click
        True
        >>> repr(module_click) == repr(click)
        True
        >>> click.consumers[tokens.Command]['preconsume'](None, None)
        'preconsume on click'
        >>> module_click.consumers[tokens.Command]['preconsume'](None, None)
        'preconsume on click'

        Now we'll add a Definition to be used for all Verbs.
        >>> module.add_definition(FullDefinition(
        ...   name=None,
        ...   token_type=tokens.Verb,
        ...   consumers={
        ...     tokens.Command: {'postconsume': lambda token, interpreter: "postconsume on Verb"}}))

        We can get it by looking for (None, tokens.Verb).
        >>> module_verb = module[None, tokens.Verb]
        >>> module_verb.consumers[tokens.Command]['postconsume'](None, None)
        'postconsume on Verb'

        If we look for 'click', we'll get a merged definition that has
        the stuff from both.
        >>> module_click = module['click']
        >>> module_click.consumers[tokens.Command]['preconsume'](None, None)
        'preconsume on click'
        >>> module_click.consumers[tokens.Command]['postconsume'](None, None)
        'postconsume on Verb'

        If we update the definition for 'click' to have a postconsume,
        when we get the definition for 'click', we'll get THAT function.
        >>> module.add_definition(FullDefinition(
        ...   name='click',
        ...   token_type=tokens.Verb,
        ...   consumers={
        ...     tokens.Command: {'postconsume': lambda token, interpreter: "postconsume on click"}}))
        >>> module_click = module['click']
        >>> module_click.consumers[tokens.Command]['preconsume'](None, None)
        'preconsume on click'
        >>> module_click.consumers[tokens.Command]['postconsume'](None, None)
        'postconsume on click'

        We can still get the one for Verb, by searching for (None, tokens.Verb).
        >>> module_verb = module[None, tokens.Verb]
        >>> module_verb.consumers[tokens.Command]['postconsume'](None, None)
        'postconsume on Verb'

        It is possible for keyword or token type in definitions to map
        to a Falsey value.  That means that definition has been removed.
        This is intended for use in Lexicons, which are built from
        multiple modules.
        Trying to get a definition that has been removed results in a
        RemovedDefinition eception being thrown.

        >>> module_removed_keyword = Module(name='removed keyword')
        >>> module_removed_keyword.add_definition(
        ...   name='click',
        ...   definition=None)
        >>> module_removed_keyword['click']
        Traceback (most recent call last):
          ...
        RemovedDefinition: Definition for 'click' removed in module 'removed keyword'

        A Lexicon where a removed keyword shadows one that already
        existed will raise a KeyError when one looks for the
        definition.
        >>> module_added_keyword = Module(name='added keyword')
        >>> module_added_keyword.add_definition(
        ...   name='click',
        ...   definition=FullDefinition(
        ...     name='click',
        ...     token_type=tokens.Verb,
        ...     consumers={
        ...       tokens.Command: {
        ...         'postconsume': lambda token, interpreter: "Post-consume"}}))
        >>> lex1 = Lexicon(modules=[module_added_keyword])
        >>> lex1['click'].consumers[tokens.Command]['postconsume'](None, None)
        'Post-consume'
        >>> lex2 = Lexicon(modules=[module_added_keyword, module_removed_keyword])
        >>> lex2['click'].consumers[tokens.Command]['postconsume'](None, None)
        Traceback (most recent call last):
          ...
        RemovedDefinition: Definition for 'click' removed in module 'removed keyword'

        A Lexicon that has a module that re-adds a removed keyword will
        have the definitions after the removal, but none from before.
        >>> module_readded_keyword = Module(name='readded keyword')
        >>> module_readded_keyword.add_definition(
        ...   name='click',
        ...   definition=FullDefinition(
        ...     name='click',
        ...     token_type=tokens.Verb,
        ...     consumers={
        ...       tokens.Command: {
        ...         'preconsume': lambda token, interpreter: "Pre-consume"}}))
        >>> lex3 = Lexicon(modules=[module_added_keyword, module_removed_keyword, module_readded_keyword])
        >>> lex3['click'].consumers[tokens.Command]['preconsume'](None, None)
        'Pre-consume'
        >>> lex3['click'].consumers[tokens.Command]['postconsume'](None, None)
        Traceback (most recent call last):
          ...
        KeyError: 'postconsume'
        """
        try:
            # if the keyword is actually a 2-tuple, split it up
            keyword, token_type = keyword
        except ValueError as ve:
            # if it is not, then set token_type to None, because we
            # don't have one
            token_type = None

        if keyword and keyword in self.definitions:
            # We have a valid keyword
            if not self.definitions[keyword]:
                # This keyword is here to mark that this module removes
                # it.  raise the RemovedDefinition exception
                raise RemovedDefinition(
                    "Definition for '%s' removed in module '%s'" % (keyword, self.name))

        # if the token_type is None, we need to get one
        if not token_type:
            token_type = self.definitions[keyword].token_type

        # Make a new definition and update it with definitions for the
        # token types in the MRO of the token_type
        definition = FullDefinition(
            name=keyword,
            token_type=token_type)

        # make sure we have the token this module uses for the
        # token_type of the keyword
        toktype = self.module_tokens.get(token_type, token_type)

        for tt in reversed([ttype for ttype in toktype.__mro__ if issubclass(ttype, tokens.ParseUnit)]):
            if tt in self.definitions:
                if not self.definitions[tt]:
                    # If the definition tests False, we ignore the rest,
                    # we raise an exception
                    raise RemovedDefinition(
                        "Definition for '%s' removed in module '%s'" % (keyword if keyword else str(toktype), self.name))
                definition.update(DefinitionAlias(
                    name=keyword,
                    target=self.definitions[tt]))
        if keyword in self.definitions:
            definition.update(self.definitions[keyword])

        return definition

    def _validate_definitions(self, name, value):
        bad_definitions = dict(
            (name, definition) for (name, definition) in value.iteritems() if
            definition and not (isinstance(definition, Definition) and (definition.name == name or not definition.name)))
        if bad_definitions:
            raise ValueError((
                "There are definitions that are not of the right type or "
                "have mismatched names:\n%s" % (pprint.pformat(bad_definitions))))
        return True

    def _validate_module_tokens(self, name, value):
        bad_keys = [k for k in value if not (isinstance(k, type) or issubclass(k, tokens.ParseUnit))]
        if bad_keys:
            raise ValueError((
                "There are base token types listed that are not subclasses of tokens.ParseUnit: %s" % (pprint.pformat(bad_keys))))
        bad_values = dict((k, v) for k, v in value.items() if not (isinstance(v, type) or issubclass(v, k)))
        if bad_values:
            raise ValueError((
                "There are module token types listed that are not subclasses of their base token types: %s" % (pprint.pformat(bad_values))))
        return True

    @property
    def available_modules(self):
        """
        It is possible to see all the modules that this module is guaranteed
        to have access to, based on its required modules, and their
        requirements, etc.  We'll create yet another module to demonstrate
        that.
        >>> module = Module(
        ...   name='testmodule')
        >>> pprint.pprint(module.available_modules)
        OrderedSet([Module(name='testmodule')])

        If a module requires another module, then it's available modules
        are also available.
        >>> module2 = Module(
        ...   name='testmodule2',
        ...   required_modules=ordered_set.OrderedSet([module]))
        >>> pprint.pprint(module2.available_modules)
        OrderedSet([Module(name='testmodule'), Module(name='testmodule2')])
        """

        available = ordered_set.OrderedSet()
        for module in self.required_modules:
            available |= module.available_modules
            available.append(module)
        available.append(self)
        return available

    def add_definition(self, definition, name=None, merge=True):
        """
        Add a definition to the module's definition list.  If the
        definition is already there, the new is merged with the old.
        If the definition is an alias, then it is added to the backlinks
        in the aliased definition.
        >>> module = Module(name='testmodule')
        >>> pprint.pprint(module.definitions)
        {}
        >>> click = FullDefinition(
        ...     name='click',
        ...     token_type=tokens.Verb)
        >>> module.add_definition(click)
        >>> pprint.pprint(module.definitions)
        {'click': FullDefinition(token_type=<class 'tokens.Verb'>, title='click', pattern='click')}
        >>> clack = DefinitionAlias(
        ...     name='clack',
        ...     target=click)
        >>> module.add_definition(clack)
        >>> pprint.pprint(module.definitions)
        {'clack': DefinitionAlias(target=FullDefinition(token_type=<class 'tokens.Verb'>, title='click', pattern='click'), title='clack', pattern='clack'),
         'click': FullDefinition(token_type=<class 'tokens.Verb'>, title='click', pattern='click')}
        """
        if not (definition or name):
            raise ValueError("Have to have either a name or a definition")
        elif not definition:
            # We're setting this module to delete this definition.  It
            # doesn't matter what's here now.
            self.definitions[name] = definition
        else:
            definition_key = name or definition.name or definition.token_type
            definition = copy.deepcopy(definition)
            if definition_key in self.definitions and self.definitions[definition_key]:
                my_definition = copy.deepcopy(self.definitions[definition_key])
                my_definition.update(definition, merge)
                definition = my_definition
            if definition:
                attr.validate(definition)
            self.definitions[definition_key] = definition
            attr.validate(self)

    def remove_definition(self, definition):
        """
        Create the module for testing...
        >>> module = Module(name='testmodule')

        And a couple of definitions.
        >>> click = FullDefinition(
        ...   name='click',
        ...   token_type=tokens.Verb)
        >>> clack = DefinitionAlias(
        ...   name='clack',
        ...   target=click)

        This removes a definition from the module, as well as any
        aliases to it.
        >>> module.add_definition(click)
        >>> module.add_definition(clack)
        >>> pprint.pprint(module.definitions)
        {'clack': DefinitionAlias(target=FullDefinition(token_type=<class 'tokens.Verb'>, title='click', pattern='click'), title='clack', pattern='clack'),
         'click': FullDefinition(token_type=<class 'tokens.Verb'>, title='click', pattern='click')}
        >>> module.remove_definition('click')
        >>> pprint.pprint(module.definitions)
        {'clack': DefinitionAlias(target=FullDefinition(token_type=<class 'tokens.Verb'>, title='click', pattern='click'), title='clack', pattern='clack')}

        If the definition we remove is an alias, then the backreference
        in its target is removed as well.
        >>> module.add_definition(click)
        >>> module.add_definition(clack)
        >>> pprint.pprint(module.definitions)
        {'clack': DefinitionAlias(target=FullDefinition(token_type=<class 'tokens.Verb'>, title='click', pattern='click'), title='clack', pattern='clack'),
         'click': FullDefinition(token_type=<class 'tokens.Verb'>, title='click', pattern='click')}
        >>> module.remove_definition('clack')
        >>> pprint.pprint(module.definitions)
        {'click': FullDefinition(token_type=<class 'tokens.Verb'>, title='click', pattern='click')}
        """
        definition = self.definitions[definition]
        del self.definitions[definition.name]
        for alias in definition.aliases:
            alias.module.remove_definition(alias)
            definition.aliases -= ordered_set.OrderedSet([alias])
        if hasattr(self, 'target_name') and self.target_name in self.module.definitions:
            self.module.defintions[self.target_name].aliases -= ordered_set.OrderedSet([self])

@attr.s(
    slots=True,
    cmp=False)
class Definition(object):
    """
    This is a base class for FullDefinition and DefinitionAlias
    """
    pass

@attr.s(
    slots=True,
    cmp=False)
class FullDefinition(Definition):
    """
    This class implements the definition of a single keyword.  It should
    include all information about how to tokenize, parse, compile,
    interpret, and output the keyword.

    We'll create a simple definition for a 'click' keyword, letting the
    defaults handle things as much as possible.
    >>> click = FullDefinition(
    ...   name='click',
    ...   token_type=tokens.Verb)
    >>> click
    FullDefinition(token_type=<class 'tokens.Verb'>, title='click', pattern='click')

    token_type is the type of token this keyword will generate.  It's
    here more as a marker than as the type that will actually be used,
    as it's possible some modules may define their own token types
    decended from the ones provided in the tokens python module.
    token_type must be a ParseUnit.
    >>> parse_unit_token_type = FullDefinition(
    ...   name='parse_unit',
    ...   token_type=tokens.Verb)
    >>> parse_unit_token_type
    FullDefinition(token_type=<class 'tokens.Verb'>, title='parse_unit', pattern='parse_unit')

    An exception will be raised if the token_type is not provided...
    >>> must_provide_a_token_type = FullDefinition()
    ...   name='no token type')
    Traceback (most recent call last):
      ...
    TypeError: __init__() takes at least 2 arguments (1 given)

    or if the token_type is not a ParseUnit.
    >>> token_type_must_be_parse_unit = FullDefinition(
    ...   name='no token type',
    ...   token_type=None)
    Traceback (most recent call last):
      ...
    TypeError: None is not a <class 'tokens.ParseUnit'>

    pattern is the regular expression used to find the token this
    definition represents.  If it is not provided, it will be set to
    match the name attribute.
    >>> click.pattern
    'click'

    An exception will be raised if pattern is not a string or None.
    >>> bad_pattern = FullDefinition(
    ...   name='select',
    ...   token_type=tokens.Verb,
    ...   pattern=5)
    Traceback (most recent call last):
      ...
    TypeError: ("'pattern' must be <type 'str'> (got 5 that is a <type 'int'>).", Attribute(name='pattern', default=None, validator=<optional validator for <instance_of validator for type <type 'str'>> or None>, repr=True, cmp=True, hash=True, init=True, convert=None, metadata=mappingproxy({})), <type 'str'>, 5)

    modules keeps track of what modules have updated this definition
    from their own definitions or registered it.  It cannot be provided at initialization...
    >>> cant_provide_modules = FullDefinition(
    ...   name='select',
    ...   token_type=tokens.Verb)

    Or when .update() is used (more on this later).

    consumers provides the hooks to be used at various stages of the
    parsing process.  It is named so because the parsing is done by
    different tokens 'consuming' subsequent tokens and adding them to
    their children.  This results in a tree structure.

    consumers is a nested Mapping of Mappings.  The exterior Mapping is
    consumer -> hooks telling how the consumer should parse the token
    defined by this definition.  This might be a string, indicating
    parsing rules for a particular keyword, or a ParseUnit, indicating
    parsing rules for a whole class of tokens.  The hooks Mapping is str
    -> callable, providing callables to be used at different stages of
    the parsing.  If these requirements are not met, an exception will
    be raised.
    >>> consumers_must_be_a_mapping = FullDefinition(
    ...   name='select',
    ...   token_type=tokens.Verb,
    ...   consumers=5) #doctest: +ELLIPSIS
    Traceback (most recent call last):
      ..
    TypeError: ("'consumers' must be <class '_abcoll.MutableMapping'> (got 5 that is a <type 'int'>).", Attribute(name='consumers', default=Factory(factory=<type 'dict'>), validator=<function <lambda> at 0x...>, repr=False, cmp=True, hash=True, init=True, convert=None, metadata=mappingproxy({})), <class '_abcoll.MutableMapping'>, 5)

    >>> consumers_mapping_keys_are_tokens_or_strings = FullDefinition(
    ...   name='select',
    ...   token_type=tokens.Verb,
    ...   consumers={5:None}) #doctest: +ELLIPSIS
    Traceback (most recent call last):
      ...
    TypeError: ("'consumers' must be <class '_abcoll.MutableMapping'> (got None that is a <type 'NoneType'>).", Attribute(name='consumers', default=Factory(factory=<type 'dict'>), validator=<function <lambda> at 0x...>, repr=False, cmp=True, hash=True, init=True, convert=None, metadata=mappingproxy({})), <class '_abcoll.MutableMapping'>, None)

    >>> consumers_mapping_values_are_mappings = FullDefinition(
    ...   name='select',
    ...   token_type=tokens.Verb,
    ...   consumers={'fred':None}) #doctest: +ELLIPSIS
    Traceback (most recent call last):
      ...
    TypeError: ("'consumers' must be <class '_abcoll.MutableMapping'> (got None that is a <type 'NoneType'>).", Attribute(name='consumers', default=Factory(factory=<type 'dict'>), validator=<function <lambda> at 0x...>, repr=False, cmp=True, hash=True, init=True, convert=None, metadata=mappingproxy({})), <class '_abcoll.MutableMapping'>, None)

    >>> consumers_inner_mapping_keys_are_strings = FullDefinition(
    ...   name='select',
    ...   token_type=tokens.Verb,
    ...   consumers={'fred':{5:None}}) #doctest: +ELLIPSIS
    Traceback (most recent call last):
      ...
    ValueError: The following consumers in the definition of 'select' have hooks that are not callable{'fred': [5]}

    >>> consumers_inner_mapping_values_are_callables = FullDefinition(
    ...   name='select',
    ...   token_type=tokens.Verb,
    ...   consumers={'fred':{'barney':None}}) #doctest: +ELLIPSIS
    Traceback (most recent call last):
      ...
    ValueError: The following consumers in the definition of 'select' have hooks that are not callable{'fred': ['barney']}

    interpretations provides a way for tokens to be interpreted differently
    based on their parent tokens.  This is a Mapping of consumers ->
    callables.  The consumer is either a string or a ParseUnit.  If
    these conditions are not met, an exception is raised.
    >>> interpretations_must_be_a_mapping = FullDefinition(
    ...   name='select',
    ...   token_type=tokens.Verb,
    ...   interpretations=5) #doctest: +ELLIPSIS
    Traceback (most recent call last):
      ...
    TypeError: ("'interpretations' must be <class '_abcoll.MutableMapping'> (got 5 that is a <type 'int'>).", Attribute(name='interpretations', default=Factory(factory=<type 'dict'>), validator=<function <lambda> at 0x...>, repr=False, cmp=True, hash=True, init=True, convert=None, metadata=mappingproxy({})), <class '_abcoll.MutableMapping'>, 5)

    >>> interpretations_mapping_keys_are_tokens_or_strings = FullDefinition(
    ...   name='select',
    ...   token_type=tokens.Verb,
    ...   interpretations={5:None}) #doctest: +ELLIPSIS
    Traceback (most recent call last):
      ...
    ValueError: The following Attribute(name='interpretations', default=Factory(factory=<type 'dict'>), validator=<function <lambda> at 0x...>, repr=False, cmp=True, hash=True, init=True, convert=None, metadata=mappingproxy({})) in the definition of 'select' have uncallable values: {5: None}

    >>> interpretations_mapping_values_are_callables = FullDefinition(
    ...   name='select',
    ...   token_type=tokens.Verb,
    ...   interpretations={'fred':None}) #doctest: +ELLIPSIS
    Traceback (most recent call last):
      ...
    ValueError: The following Attribute(name='interpretations', default=Factory(factory=<type 'dict'>), validator=<function <lambda> at 0x...>, repr=False, cmp=True, hash=True, init=True, convert=None, metadata=mappingproxy({})) in the definition of 'select' have uncallable values: {'fred': None}

    outputters tells how to output a token in different situations.  It
    is a Mapping of string -> callable, where the string is a particular
    kind of output, and the callable is how to get that output.  If
    these conditions are not met, and exception is raised.
    >>> outputters_must_be_a_mapping = FullDefinition(
    ...   name='select',
    ...   token_type=tokens.Verb,
    ...   outputters=5) #doctest: +ELLIPSIS
    Traceback (most recent call last):
      ...
    TypeError: ("'outputters' must be <class '_abcoll.Mapping'> (got 5 that is a <type 'int'>).", Attribute(name='outputters', default=Factory(factory=<type 'dict'>), validator=<function <lambda> at 0x...>, repr=False, cmp=True, hash=True, init=True, convert=None, metadata=mappingproxy({})), <class '_abcoll.Mapping'>, 5)

    >>> outputters_mapping_keys_are_strings = FullDefinition(
    ...   name='select',
    ...   token_type=tokens.Verb,
    ...   outputters={5:None}) #doctest: +ELLIPSIS
    Traceback (most recent call last):
      ...
    TypeError: ("'outputters' must be <type 'str'> (got 5 that is a <type 'int'>).", Attribute(name='outputters', default=Factory(factory=<type 'dict'>), validator=<function <lambda> at 0x...>, repr=False, cmp=True, hash=True, init=True, convert=None, metadata=mappingproxy({})), <type 'str'>, 5)

    >>> outputters_mapping_values_are_callables = FullDefinition(
    ...   name='select',
    ...   token_type=tokens.Verb,
    ...   outputters={'fred':None}) #doctest: +ELLIPSIS
    Traceback (most recent call last):
      ...
    ValueError: The following Attribute(name='outputters', default=Factory(factory=<type 'dict'>), validator=<function <lambda> at 0x...>, repr=False, cmp=True, hash=True, init=True, convert=None, metadata=mappingproxy({})) in the definition of 'select' have uncallable values: {'fred': None}

    aliases is an OrderedSet of the aliases to this Definition.  This is
    here so that if the definition is removed, the aliases can be as
    well.  It is not provided to the init function, if one tries, and
    exception is raised.
    >>> cant_provide_aliases = FullDefinition(
    ...   name='select',
    ...   token_type=tokens.Verb)
    """

    token_type = attr.ib(
        validator=lambda self, name, value: (
            tokens.ParseUnit.validate(self, name, value)))

    name = attr.ib(
        default=None,
        validator=attr.validators.optional(attr.validators.instance_of(str)),
        repr=False)
    """
    name is the name of a keyword definition, which will be used to look
    it up in the Module.  If this is None, then this is a definition
    that will be used as a base for all tokens of this token_type.
    """

    title = attr.ib(
        default=None,
        validator=attr.validators.optional(attr.validators.instance_of(str)))
    """
    title is the prettified name that will be used for this Definiton.
    """

    pattern = attr.ib(
        default=None,
        validator=attr.validators.optional(attr.validators.instance_of(str)))

    consumers = attr.ib(
        default=attr.Factory(dict),
        validator=lambda self, name, value: (
            attr.validators.instance_of(collections.MutableMapping)(self, name, value),
            [attr.validators.instance_of(collections.MutableMapping)(self, name, v) for (k, v) in value.iteritems()],
            self._validate_consumer(name, value)),
        repr=False)

    interpretations = attr.ib(
        default=attr.Factory(dict),
        validator=lambda self, name, value: (
            attr.validators.instance_of(collections.MutableMapping)(self, name, value),
            self._validate_callable_mapping(name, value)),
        repr=False)

    outputters = attr.ib(
        default=attr.Factory(dict),
        validator=lambda self, name, value: (
            attr.validators.instance_of(collections.Mapping)(self, name, value),
            [attr.validators.instance_of(str)(self, name, k) for k in value],
            self._validate_callable_mapping(name, value)),
        repr=False)

    aliases = attr.ib(
        init=False,
        default=attr.Factory(ordered_set.OrderedSet),
        validator=attr.validators.instance_of(collections.Sequence),
        repr=False)

    def __attrs_post_init__(self):
        """
        Set up the token_type to be whatever the matching token_type in
        its modules module_tokens mapping is.  Also set up the pattern
        to be based on the name, if none is provided.
        """
        if self.pattern is None and self.name is not None:
            self.pattern = r"[ \t]+".join(self.name.split())

        self.title = self.title or self.name or str(self.token_type)

    def __eq__(self, other):
        return isinstance(other, Definition) and self.name==other.name and isinstance(other.token_type, type(self.token_type))

    def _validate_callable_mapping(self, name, value):
        bad_outputters = dict((k, v) for (k, v) in value.items() if not callable(v))
        bad_keys = dict((k, v) for (k, v) in value.items() if not (isinstance(k, str) or (isinstance(k, type) and issubclass(k, tokens.ParseUnit))))
        if bad_outputters:
            raise ValueError((
                ("The following %s in the definition of '%s' have uncallable values: " % (name, self.name)) +
                pprint.pformat(bad_outputters)))
        if bad_keys:
            raise ValueError((
                ("The following %s in the definition of '%s' have keys that are not ParseUnits: " % (name, self.name)) +
                pprint.pformat(bad_keys)))

    def _validate_consumer(self, name, value):
        not_callables = {}
        bad_consumers = {}
        for consumer, rules in value.iteritems():
            if not (isinstance(consumer, str) or issubclass(consumer, tokens.ParseUnit)):
                bad_consumers[consumer] = consumer
            else:
                consumer_hooks = set(rules)
                for hook, value in rules.iteritems():
                    if not callable(value):
                        # The implementation of this hook is not a
                        # callable
                        not_callables[consumer] = not_callables.get(consumer, [])
                        not_callables[consumer].append(hook)
        else:
            if bad_consumers:
                # There were invalid consumers given
                raise ValueError((
                    ("The following consumers in the definition of '%s' have consumers of the wrong type" % self.name) +
                    pprint.pformat(bad_consumers)))
            if not_callables:
                # There were hook implementations that aren't callable
                raise ValueError((
                    ("The following consumers in the definition of '%s' have hooks that are not callable" % self.name) +
                    pprint.pformat(not_callables)))

        return True

    def update(self, other, merge=True):
        """
        Update this defintion with attributes of the other.  This will
        go through all the information of the other, and merge the or
        replace equivalent information in this one with it.  This
        function uses deepcopies of other to insure that the originals are never
        used in the updated copy to prevent accidental modification
        later.  It is assumed that self is similarly copied, and not
        precious.

        This is to be used by Lexicons to create the definitions to be
        given to the Tokenizer.

        First we'll make a simple 'click' definition.
        >>> click = FullDefinition(
        ...   name='click',
        ...   token_type=tokens.Verb)
        >>> click_copy = copy.deepcopy(click)

        An exception is raised if the updating definition has a
        different name...
        >>> update_wrong_name = FullDefinition(
        ...   name='click wrong name',
        ...   token_type=tokens.Verb)
        >>> click_copy.update(update_wrong_name)
        Traceback (most recent call last):
          ...
        ValueError: Definition 'click' cannot be updated with 'click wrong name', name mismatch

        Or if the token_types are different.
        >>> update_wrong_token_type = FullDefinition(
        ...   name='click',
        ...   token_type=tokens.Noun)
        >>> click_copy.update(update_wrong_token_type)
        Traceback (most recent call last):
          ...
        ValueError: Definition 'click' cannot be updated with 'click', token_type mismatch

        We can update one defintition with another to change the pattern.
        >>> click_copy.pattern
        'click'
        >>> update_pattern = FullDefinition(
        ...   name='click',
        ...   token_type=tokens.Verb,
        ...   pattern='otherpattern')
        >>> update_pattern.pattern
        'otherpattern'
        >>> click_copy.update(update_pattern) is update_pattern
        True
        >>> click_copy.pattern
        'otherpattern'

        If the updating definition doesn't have a pattern that tests True, it
        will not be copied.
        >>> update_pattern.pattern=''
        >>> click_copy.update(update_pattern) is update_pattern
        True
        >>> click_copy.pattern
        'otherpattern'

        Unless merge=False is passed to the update function.
        >>> click_copy.update(update_pattern, merge=False) is update_pattern
        True
        >>> click_copy.pattern
        ''

        Update will do fancier merges for the other attributes.
        Consumers will be merged, hook by hook.  If a hook exists for a
        consumer, new implementations will be added to it via the update
        method unless merge is set to False.
        >>> click_preconsume = FullDefinition(
        ...   name='click',
        ...   token_type=tokens.Verb,
        ...   consumers={
        ...     tokens.Command: {'preconsume': lambda token, interpreter: True},
        ...   })
        >>> pprint.pprint(click_preconsume.consumers) #doctest: +ELLIPSIS
        {<class 'tokens.Command'>: {'preconsume': <function <lambda> at 0x...>}}
        >>> click_copy.update(click_preconsume) is click_preconsume
        True
        >>> pprint.pprint(click_copy.consumers) #doctest: +ELLIPSIS
        {<class 'tokens.Command'>: {'preconsume': <function <lambda> at 0x...>}}
        >>> click_postconsume = FullDefinition(
        ...   name='click',
        ...   token_type=tokens.Verb,
        ...   consumers={
        ...     tokens.Command: {'postconsume': lambda token, interpreter: True},
        ...   })
        >>> pprint.pprint(click_postconsume.consumers) #doctest: +ELLIPSIS
        {<class 'tokens.Command'>: {'postconsume': <function <lambda> at 0x...>}}
        >>> click_copy.update(click_postconsume) is click_postconsume
        True
        >>> pprint.pprint(click_copy.consumers) #doctest: +ELLIPSIS
        {<class 'tokens.Command'>: {'postconsume': <function <lambda> at 0x...>,
                                    'preconsume': <function <lambda> at 0x...>}}

        Outputters are updated via the update method of the mapping
        unless merge is set to False.
        >>> click_raw_outputter = FullDefinition(
        ...   name='click',
        ...   token_type=tokens.Verb,
        ...   outputters={
        ...     'raw': lambda token: str(token),
        ...   })
        >>> pprint.pprint(click_raw_outputter.outputters) #doctest: +ELLIPSIS
        {'raw': <function <lambda> at 0x...>}
        >>> click_copy.update(click_raw_outputter) is click_raw_outputter
        True
        >>> pprint.pprint(click_copy.outputters) #doctest: +ELLIPSIS
        {'raw': <function <lambda> at 0x...>}

        Interpretations will be merged the same way as outputters.  This
        is most likely to happen in the case of a Noun, so we'll show an
        example of that in the update method for CompilableDefinition.
        """
        if self.name != other.name:
            raise ValueError(
                "Definition '%s' cannot be updated with '%s', name mismatch" % (self.name, other.name))
        if not issubclass(other.token_type, self.token_type):
            raise ValueError(
                "Definition '%s' cannot be updated with '%s', token_type mismatch" % (self.name, other.name))

        if isinstance(other, (FullDefinition, DefinitionAlias)):
            self.pattern = (other.pattern or self.pattern) if merge else other.pattern
            other_consumers = copy.deepcopy(other.consumers)
            other_interpretations = copy.deepcopy(other.interpretations)
            other_outputters = copy.deepcopy(other.outputters)
            for consumer, hooks in other_consumers.iteritems():
                if merge and consumer in self.consumers:
                    for hook, implementation in hooks.iteritems():
                        self.consumers[consumer][hook] = hooks[hook]
                else:
                    self.consumers[consumer] = hooks
            if merge:
                self.interpretations.update(other_interpretations)
                self.outputters.update(other_outputters)
            else:
                self.interpretations = other_interpretations
                self.outputters = other_outputters
            attr.validate(self)
        return other

@attr.s(slots=True)
class CompilableDefinition(FullDefinition):
    """
    This is a definition for tokens that can be compiled to xpaths. It
    is intended to be used for Nouns.

    We'll make a Definition for a button...
    >>> CompilableDefinition(
    ...   name='button',
    ...   token_type=tokens.Noun,
    ...   good_xpath_templates=ordered_set.OrderedSet([
    ...     'descendant::button[starts-with(@value, "%{value}s")]']))
    CompilableDefinition(token_type=<class 'tokens.Noun'>, title='button', pattern='button', good_xpath_templates=OrderedSet(['descendant::button[starts-with(@value, "%{value}s")]']), sloppy_xpath_templates=OrderedSet())

    And one that allows sloppy xpaths
    >>> CompilableDefinition(
    ...   name='button',
    ...   token_type=tokens.Noun,
    ...   good_xpath_templates=ordered_set.OrderedSet([
    ...     'descendant::button[starts-with(@value, "%{value}s")]']),
    ...   sloppy_xpath_templates=ordered_set.OrderedSet([
    ...     'descendant::span[@class="button" and starts-with(., "%{value}s")]']))
    CompilableDefinition(token_type=<class 'tokens.Noun'>, title='button', pattern='button', good_xpath_templates=OrderedSet(['descendant::button[starts-with(@value, "%{value}s")]']), sloppy_xpath_templates=OrderedSet(['descendant::span[@class="button" and starts-with(., "%{value}s")]']))

    Good and sloppy xpaths must not have any overlap.
    >>> CompilableDefinition(
    ...   name='button',
    ...   token_type=tokens.Noun,
    ...   good_xpath_templates=ordered_set.OrderedSet([
    ...     'descendant::button[starts-with(@value, "%{value}s")]']),
    ...   sloppy_xpath_templates=ordered_set.OrderedSet([
    ...     'descendant::button[starts-with(@value, "%{value}s")]']))
    Traceback (most recent call last):
      ...
    ValueError: The following templates are in both 'good' and 'sloppy':
    OrderedSet(['descendant::button[starts-with(@value, "%{value}s")]'])
    """

    good_xpath_templates = attr.ib(
        default=attr.Factory(ordered_set.OrderedSet),
        validator=lambda self, name, value: (
            attr.validators.instance_of(ordered_set.OrderedSet)(self, name, value),
            [attr.validators.instance_of(str)(self, name, v) for v in value]),
        repr=True)
    """
    good_xpath_templates is a OrderedSet of templates for creating
    xpaths to find elements that is considered "good form" to use. These
    wll not result in a warning if the element is found using these.
    """

    sloppy_xpath_templates = attr.ib(
        default=attr.Factory(ordered_set.OrderedSet),
        validator=lambda self, name, value: (
            attr.validators.instance_of(ordered_set.OrderedSet)(self, name, value),
            [attr.validators.instance_of(str)(self, name, v) for v in value],
            self._validate_sloppy_xpath_templates(name, value)),
        repr=True)
    """
    sloppy_xpath_templates is a OrderedSet of templates for creating
    xpaths to find elements that is considered "sloppy" to use. These
    will result in warnings, and errors in pedantic mode.  They will
    always be used after all good xpaths have failed.
    sloppy_xpath_declarations must not have any overlap with
    good_xpath_templates.
    """

    filters = attr.ib(
        default=attr.Factory(ordered_set.OrderedSet),
        validator=lambda self, name, value: (
            attr.validators.instance_of(ordered_set.OrderedSet)(self, name, value),
            self._validate_filters(name, value)),
        repr=False)
    """
    filters is an Sequence of callables that will be called to filter out
    elements that would otherwise match (such as those that are not
    clickable) or to perform operations on the element (such as
    scrolling it to the center of the screen to make screenshots
    easier).
    """

    def _validate_sloppy_xpath_templates(self, name, value):
        both = value & self.good_xpath_templates
        if both:
            # There are xpath templates that are both good and sloppy,
            # raise a ValueError
            raise ValueError(
                "The following templates are in both 'good' and 'sloppy':\n%s" % (
                    pprint.pformat(both)))
        return True

    def _validate_filters(self, name, value):
        bad_filters = [f for f in value if not callable(f)]
        if bad_filters:
            raise ValueError(
                "The following filters are not collable:\n%s" % (
                    pprint.pformat(bad_filters)))
        return True

    def update(self, other, merge=True):
        """
        Update this defintion with attributes of the other.  This will
        go through all the information of the other, and merge the or
        replace equivalent information in this one with it.  This
        function uses deepcopies of other to insure that the originals are never
        used in the updated copy to prevent accidental modification
        later.  It is assumed that self is similarly copied, and not
        precious.

        This is to be used by Lexicons to create the definitions to be
        given to the Tokenizer.
        """

        other = super(CompilableDefinition, self).update(other, merge=merge)
        if isinstance(other, CompilableDefinition):
            self.good_xpath_templates = (self.good_xpath_templates + other.good_xpath_templates) if merge else copy.deepcopy(other.good_xpath_templates)
            self.sloppy_xpath_templates = (self.sloppy_xpath_templates + other.sloppy_xpath_templates) if merge else copy.deepcopy(other.sloppy_xpath_templates)
            self.filters = (self.filters + other.filters) if merge else copy.deepcopy(other.filters)
        attr.validate(self)
        return other

@attr.s(slots=True)
class DefinitionAlias(Definition):
    """
    This represents the definition of a keyword that is just an alias
    for another keyword.
    >>> module = Module(name="bedrock")
    >>> base_definition = FullDefinition(
    ...   name="fred",
    ...   token_type=tokens.Verb)
    >>> base_definition
    FullDefinition(token_type=<class 'tokens.Verb'>, title='fred', pattern='fred')
    >>> module.add_definition(base_definition)
    >>> alias = DefinitionAlias(
    ...   name="flintstone",
    ...   target=base_definition)
    >>> alias
    DefinitionAlias(target=FullDefinition(token_type=<class 'tokens.Verb'>, title='fred', pattern='fred'), title='flintstone', pattern='flintstone')

    If one tries to get an attribute that an alias does not have, it
    will try to retrieve from its target.
    >>> alias.title
    'flintstone'
    """

    target = attr.ib(
        validator=lambda self, name, value: (
            attr.validators.instance_of(Definition),
            self._validate_target_cycles(name, value)))

    name = attr.ib(
        default=None,
        validator=attr.validators.optional(attr.validators.instance_of(str)),
        repr=False)
    """
    name is the name of a keyword definition, which will be used to look
    it up in the Module.  If it is None, that means the module will know
    this Definition by a type.
    """

    title = attr.ib(
        default=None,
        validator=attr.validators.optional(attr.validators.instance_of(str)))
    """
    title is the prettified name that will be used for this Definiton.
    """

    pattern = attr.ib(
        default=None,
        validator=attr.validators.optional(attr.validators.instance_of(str)))
    """
    pattern is the regular expression used to find the token this
    definition represents.  If it is not provided, it will be set to
    match the name attribute.
    """

    def __hash__(self):
        return hash(self.title)

    def __attrs_post_init__(self):
        """
        Set up the token_type to be whatever the matching token_type in
        its modules module_tokens mapping is.  Also set up the pattern
        to be based on the name, if none is provided.
        """

        if self.pattern is None and self.name:
            self.pattern = r"[ \t]+".join(self.name.split())
        self.title = self.title or self.name or str(self.target.token_type)

    def __getattr__(self, name):
        return getattr(self.target, name)

    def _validate_target_cycles(self, name, value):
        v = value
        while isinstance(v, DefinitionAlias):
            if v.target is self:
                raise ValueError(
                    "Cannot create cyclical alias: %s -> %s" % (self.name, v.name))
            else:
                v = v.target
        return True

    def update(self, other, merge=True):
        """
        Updates this DefinitionAlias.

        First, create a couple of Definitions to test with.
        >>> click1 = FullDefinition(
        ...   name='click1',
        ...   token_type=tokens.Verb)
        >>> click2 = FullDefinition(
        ...   name='click2',
        ...   token_type=tokens.Verb)

        And a couple of aliases to it.
        >>> alias1 = DefinitionAlias(
        ...   name='alias1',
        ...   target=click1)
        >>> alias2 = DefinitionAlias(
        ...   name='alias1',
        ...   pattern='alias2',
        ...   target=click2)

        Update will replace the target and the pattern.
        >>> alias1.update(alias2) is alias2
        True
        >>> alias1
        DefinitionAlias(target=FullDefinition(token_type=<class 'tokens.Verb'>, title='click2', pattern='click2'), title='alias1', pattern='alias2')

        Update will not replace a pattern with one that tests False...
        >>> alias3 = DefinitionAlias(
        ...   name='alias1',
        ...   target=click1,
        ...   pattern='')
        >>> alias1.update(alias3) is alias3
        True
        >>> alias1.pattern
        'alias2'

        Unless the merge flag is False.
        >>> alias1.update(alias3, merge=False) is alias3
        True
        >>> alias1.pattern
        ''

        Update will raise an exception if the names don't match...
        >>> alias_wrong_name = DefinitionAlias(
        ...   name='alias wrong name',
        ...   target=alias1)
        >>> alias1.update(alias_wrong_name)
        Traceback (most recent call last):
          ...
        ValueError: Definition 'alias1' cannot be updated with 'alias wrong name', name mismatch

        Or if other is not a DefinitonAlias...
        >>> alias1.update(click1)
        Traceback (most recent call last):
          ...
        ValueError: Definition 'alias1' cannot be updated with 'click1', token_type mismatch

        Or if the update would result in a cycle of targets
        >>> alias_cycle = DefinitionAlias(
        ...   name='alias1',
        ...   target=alias1)
        >>> alias1.update(alias_cycle)
        Traceback (most recent call last):
          ...
        ValueError: Cannot create cyclical alias: alias1 -> alias1
        """
        if not isinstance(other, type(self)):
            raise ValueError(
                "Definition '%s' cannot be updated with '%s', token_type mismatch" % (self.name, other.name))
        if self.name != other.name:
            raise ValueError(
                "Definition '%s' cannot be updated with '%s', name mismatch" % (self.name, other.name))
        target = self.target
        pattern = self.pattern
        try:
            self.target = other.target
            self.pattern = (other.pattern or self.pattern) if merge else other.pattern
            attr.validate(self)
        except ValueError as ve:
            self.target = target
            self.pattern = pattern
            raise
        return other

if __name__ == "__main__":
    import doctest
    print doctest.testmod()
