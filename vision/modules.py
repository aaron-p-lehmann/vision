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
import operator

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
    ...     tokens.Command: lambda token, parent, interpreter: "Clicked a thing in module1!"},))
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
    ...     tokens.Command: lambda token, parent, interpreter: "Clicked a thing in module2!"},))

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
        ...     tokens.Command: {'preconsume': lambda token, parent, interpreter: "preconsume on click in module1"}}))
        >>> module1.add_definition(FullDefinition(
        ...   name=None,
        ...   token_type=tokens.Verb,
        ...   consumers={
        ...     tokens.Command: {'postconsume': lambda token, parent, interpreter: "postconsume on Verb in module1"}}))
        >>> module2 = Module(name='module2')
        >>> module2.add_definition(FullDefinition(
        ...   name='click',
        ...   token_type=tokens.Verb,
        ...   consumers={
        ...     tokens.Command: {'preconsume': lambda token, parent, interpreter: "preconsume on click in module2"}}))

        We'll make a Lexicon with module1, to see that we can get
        definitions based on keywords from a Lexicon.
        >>> lex1 = Lexicon(modules=ordered_set.OrderedSet([module1]))
        >>> lex1_click = lex1['click']
        >>> lex1_click.consumers[tokens.Command]['preconsume'](None, None, None)
        'preconsume on click in module1'
        >>> lex1_click.consumers[tokens.Command]['postconsume'](None, None, None)
        'postconsume on Verb in module1'

        Lexicons get their definitions with later modules in the set
        given preference to earlier ones.
        Since module2 is later in the modules list in the following
        Lexicon, its preconsume will shadow the one from module1.
        >>> lex2 = Lexicon(modules=ordered_set.OrderedSet([module1, module2]))
        >>> lex2_click = lex2['click']
        >>> lex2_click.consumers[tokens.Command]['preconsume'](None, None, None)
        'preconsume on click in module2'
        >>> lex2_click.consumers[tokens.Command]['postconsume'](None, None, None)
        'postconsume on Verb in module1'

        The following Lexicon will have module1 last, and so its
        consumers will dominate.
        >>> lex3 = Lexicon(modules=ordered_set.OrderedSet([module2, module1]))
        >>> lex3_click = lex3['click']
        >>> lex3_click.consumers[tokens.Command]['preconsume'](None, None, None)
        'preconsume on click in module1'
        >>> lex3_click.consumers[tokens.Command]['postconsume'](None, None, None)
        'postconsume on Verb in module1'
        """

        def clean_hooks(hooks, clean_implementations=lambda hooks:None):
            """
            Removes cues to remove hooks from the definition.
            """
            for cls, hook in hooks.items():
                if hook is None:
                    del hooks[cls]
                else:
                    clean_implementations(hook)

        token_type = None

        # Find out what token_type this key maps to.  Look in the most
        # recent module possible, because recent shadows old.
        for module in reversed(self.available_modules):
            if key in module:
                if module[key]:
                    # This is a real definition, and not a mark for
                    # removal, so get its token_type
                    token_type = module[key].token_type
                break
        else:
            raise KeyError(key)

        if not token_type:
            # If we haven't found a token_type, it's because this
            # keyword was removed here.  raise KeyError
            raise KeyError(key)

        # Create a new Definition, then update it using definitions from
        # all modules
        definition = None
        for module in self.available_modules:
            try:
                defn = module[key, token_type]
            except RemovedDefinition as rd:
                definition = None
            else:
                if not definition:
                    definition = defn.type(
                        name=key,
                        token_type=token_type)
                elif definition.type is not defn.type:
                    temp_definition = defn.type(
                        name=key,
                        token_type=token_type)
                    temp_definition.update(definition)
                    definition = temp_definition
                definition.update(DefinitionAlias(
                    name=key,
                    pattern=defn.pattern,
                    target=defn))

        if not definition:
            raise KeyError(key)

        clean_hooks(definition.consumers)
        clean_hooks(definition.interpretations)
        clean_hooks(definition.outputters)
        return definition

    @property
    def available_modules(self):
        """
        This takes the modules in self.modules and expands them into a
        set that includes all the modules they require, as well.

        Create a Lexicon with a module that requires another module and
        verify that the Lexicon has both modules available.
        >>> lex = Lexicon(
        ...   modules=ordered_set.OrderedSet([
        ...     Module(
        ...       name='mod1',
        ...       required_modules=ordered_set.OrderedSet([
        ...         Module(name='mod1_requirement')]))]))
        >>> lex.available_modules
        OrderedSet([Module(name='mod1_requirement'), Module(name='mod1')])
        """
        return reduce(operator.or_, (module.available_modules for module in self.modules))

    def add_modules(self, module):
        """
        This adds a module to the Lexicon as the most recent.  Its
        definitions will shadow any older ones.
        """
        self.modules.append(module)

    def keys(self):
        """
        This returns all the keywords that are available from this Lexicon.

        It does not return token defaults, but does return keywords
        >>> module1 = Module(name='module1')
        >>> module1.add_definition(
        ...   definition=FullDefinition(
        ...     name='click',
        ...     token_type=tokens.Verb,
        ...     consumers={
        ...       tokens.Command: {
        ...         'preconsume': lambda token, parent, interpreter: 'click preconsume module1'}}))
        >>> module1.add_definition(
        ...   definition=FullDefinition(
        ...     name=None,
        ...     token_type=tokens.Verb,
        ...     consumers={
        ...       tokens.Command: {
        ...         'postconsume': lambda token, parent, interpreter: 'Verb postconsume module1'}}))
        >>> Lexicon(modules=ordered_set.OrderedSet([module1])).keys()
        ['click']

        It also does not return keywords that are there for removing a
        keyword from a Lexicon (keywords with a Falsey value).
        >>> module1.add_definition(
        ...   name='select',
        ...   definition=None)
        >>> Lexicon(modules=ordered_set.OrderedSet([module1])).keys()
        ['click']
        """

        key_set = set()
        for module in self.available_modules:
            for keyword in module.definitions:
                if isinstance(keyword, str):
                    # this is a keyword, not a token type default
                    try:
                        definition = module[keyword]
                    except RemovedDefinition as rd:
                        if keyword in key_set:
                            # The definition is Falsey, we need to
                            # remove this from the set
                            key_set -= set([keyword])
                    else:
                        # Add the keyword to the set
                        key_set |= set([keyword])
        return list(key_set)

    def values(self):
        """
        This returns the keyword definitions that are available from the
        lexicon.
        >>> module1 = Module(name='module1')
        >>> module1.add_definition(
        ...   definition=FullDefinition(
        ...     name='click',
        ...     token_type=tokens.Verb,
        ...     consumers={
        ...       tokens.Command: {
        ...         'preconsume': lambda token, parent, interpreter: 'click preconsume module1'}}))
        >>> Lexicon(modules=ordered_set.OrderedSet([module1])).values()
        [FullDefinition(token_type=<class 'tokens.Verb'>, title='click', pattern='click')]
        """
        return [self[keyword] for keyword in self.keys()]

    def items(self):
        """
        This returns the (keyword,definition) pairs that are available from the
        lexicon.
        >>> module1 = Module(name='module1')
        >>> module1.add_definition(
        ...   definition=FullDefinition(
        ...     name='click',
        ...     token_type=tokens.Verb,
        ...     consumers={
        ...       tokens.Command: {
        ...         'preconsume': lambda token, parent, interpreter: 'click preconsume module1'}}))
        >>> Lexicon(modules=ordered_set.OrderedSet([module1])).items()
        [('click', FullDefinition(token_type=<class 'tokens.Verb'>, title='click', pattern='click'))]
        """
        return zip(self.keys(), self.values())

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
    module_definitions = attr.ib(
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
        ...     tokens.Command: {'preconsume': lambda token, parent, interpreter: "preconsume on click"}})
        >>> module.add_definition(click)
        >>> module_click = module['click']

        The new definition is not the same as the one we added to the
        module, but it has all the same stuff.
        >>> module_click is not click
        True
        >>> repr(module_click) == repr(click)
        True
        >>> click.consumers[tokens.Command]['preconsume'](None, None, None)
        'preconsume on click'
        >>> module_click.consumers[tokens.Command]['preconsume'](None, None, None)
        'preconsume on click'

        Now we'll add a Definition to be used for all Verbs.
        >>> module.add_definition(FullDefinition(
        ...   name=None,
        ...   token_type=tokens.Verb,
        ...   consumers={
        ...     tokens.Command: {'postconsume': lambda token, parent, interpreter: "postconsume on Verb"}}))

        We can get it by looking for (None, tokens.Verb).
        >>> module_verb = module[None, tokens.Verb]
        >>> module_verb.consumers[tokens.Command]['postconsume'](None, None, None)
        'postconsume on Verb'

        If we look for 'click', we'll get a merged definition that has
        the stuff from both.
        >>> module_click = module['click']
        >>> module_click.consumers[tokens.Command]['preconsume'](None, None, None)
        'preconsume on click'
        >>> module_click.consumers[tokens.Command]['postconsume'](None, None, None)
        'postconsume on Verb'

        If we update the definition for 'click' to have a postconsume,
        when we get the definition for 'click', we'll get THAT function.
        >>> module.add_definition(FullDefinition(
        ...   name='click',
        ...   token_type=tokens.Verb,
        ...   consumers={
        ...     tokens.Command: {'postconsume': lambda token, parent, interpreter: "postconsume on click"}}))
        >>> module_click = module['click']
        >>> module_click.consumers[tokens.Command]['preconsume'](None, None, None)
        'preconsume on click'
        >>> module_click.consumers[tokens.Command]['postconsume'](None, None, None)
        'postconsume on click'

        We can still get the one for Verb, by searching for (None, tokens.Verb).
        >>> module_verb = module[None, tokens.Verb]
        >>> module_verb.consumers[tokens.Command]['postconsume'](None, None, None)
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
        ...         'postconsume': lambda token, parent, interpreter: "Post-consume"}}))
        >>> lex1 = Lexicon(modules=[module_added_keyword])
        >>> lex1['click'].consumers[tokens.Command]['postconsume'](None, None, None)
        'Post-consume'
        >>> lex2 = Lexicon(modules=[module_added_keyword, module_removed_keyword])
        >>> lex2['click'].consumers[tokens.Command]['postconsume'](None, None, None)
        Traceback (most recent call last):
          ...
        RemovedDefinition: Definition for 'click' removed in module 'removed keyword'

        A Lexicon that has a module that re-adds a removed keyword will
        have the definitions after the removal, but none from before.
        >>> module_readded_keyword = Module(name='readded keyword')
        >>> module_readded_keyword.add_definition(
        ...   definition=FullDefinition(
        ...     name='click',
        ...     token_type=tokens.Verb,
        ...     consumers={
        ...       tokens.Command: {
        ...         'preconsume': lambda token, parent, interpreter: "Pre-consume"}}))
        >>> lex3 = Lexicon(modules=[module_added_keyword, module_removed_keyword, module_readded_keyword])
        >>> lex3['click'].consumers[tokens.Command]['preconsume'](None, None, None)
        'Pre-consume'
        >>> lex3['click'].consumers[tokens.Command]['postconsume'](None, None, None)
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

        # make sure we have the token this module uses for the
        # token_type of the keyword
        toktype = self.module_tokens.get(token_type, token_type)

        # Make a new definition and update it with definitions for the
        # token types in the MRO of the token_type

        definition_type = None
        for key in [keyword] + [cls for cls in token_type.__mro__ if issubclass(cls, tokens.ParseUnit)]:
            # Search in the token_type->definition mappings to find the
            # right kind of new definition.  First look by keyword, then
            # look up the MRO for the token_type
            definition_type = self.module_definitions.get(key, None)
            if definition_type:
                break
        else:
            # We'll default to using a FullDefinition
            definition_type = FullDefinition
        definition = definition_type(
            name=keyword,
            token_type=token_type)

        for tt in reversed([ttype for ttype in toktype.__mro__ if issubclass(ttype, tokens.ParseUnit)]):
            if tt in self.definitions:
                if not self.definitions[tt]:
                    # If the definition tests False, we ignore the rest,
                    # we raise an exception
                    raise RemovedDefinition(
                        "Definition for '%s' removed in module '%s'" % (keyword if keyword else str(toktype), self.name))
                definition.update(DefinitionAlias(
                    name=keyword,
                    pattern=self.definitions[tt].pattern,
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
        bad_keys = [k for k in value if not (isinstance(k, str) or (isinstance(k, type) and issubclass(k, tokens.ParseUnit)))]
        if bad_keys:
            raise ValueError((
                "There are base token types listed that are not subclasses of tokens.ParseUnit: %s" % (pprint.pformat(bad_keys))))
        bad_values = dict((k, v) for k, v in value.items() if not (isinstance(v, type) or issubclass(v, k)))
        if bad_values:
            raise ValueError((
                "There are module token types listed that are not subclasses of their base token types: %s" % (pprint.pformat(bad_values))))
        return True

    def _validate_module_definitions(self, name, value):
        bad_keys = [k for k in value if not (isinstance(k, type) or issubclass(k, FullDefinition))]
        if bad_keys:
            raise ValueError((
                "There are base token types listed that are not subclasses of tokens.ParseUnit: %s" % (pprint.pformat(bad_keys))))
        bad_values = dict((k, v) for k, v in value.items() if not issubclass(v, FullDefinition))
        if bad_values:
            raise ValueError((
                "There are definition types listed that are not subclasses of FullDefinition: %s" % (pprint.pformat(bad_values))))
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

        return reduce(
            operator.or_,
            (ordered_set.OrderedSet([module]) for module in (self.required_modules | ordered_set.OrderedSet([self]))))

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

@attr.s(
    slots=True,
    cmp=False)
class Definition(object):
    """
    This is a base class for FullDefinition and DefinitionAlias
    """

    @property
    def type(self):
        """
        This returns the type of Definiton this is.  It will be
        overwritten by DefinitionAlias to provide the type of its
        ultimate target.
        """
        return type(self)

    def update(self, other, merge=True):
        if not (issubclass(other.type, self.type) or issubclass(self.type, other.type)):
            raise ValueError(
                "Cannot update '%s' with '%s', definition type mismatch" % (self.name, other.name))

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
    ValueError: The following consumers in the definition of 'select' have consumers of the wrong type: [5]

    >>> consumers_mapping_values_are_mappings = FullDefinition(
    ...   name='select',
    ...   token_type=tokens.Verb,
    ...   consumers={'fred':[]}) #doctest: +ELLIPSIS
    Traceback (most recent call last):
      ...
    TypeError: ("'consumers' must be <class '_abcoll.MutableMapping'> (got [] that is a <type 'list'>).", Attribute(name='consumers', default=Factory(factory=<type 'dict'>), validator=<function <lambda> at 0x...>, repr=False, cmp=True, hash=True, init=True, convert=None, metadata=mappingproxy({})), <class '_abcoll.MutableMapping'>, [])

    >>> consumers_inner_mapping_keys_are_strings = FullDefinition(
    ...   name='select',
    ...   token_type=tokens.Verb,
    ...   consumers={'fred':{5:None}}) #doctest: +ELLIPSIS
    Traceback (most recent call last):
      ...
    ValueError: The following consumers in the definition of 'select' have hooks names that are not strings: {'fred': [5]}

    >>> consumers_inner_mapping_values_are_callables = FullDefinition(
    ...   name='select',
    ...   token_type=tokens.Verb,
    ...   consumers={'fred':{'barney':5}}) #doctest: +ELLIPSIS
    Traceback (most recent call last):
      ...
    ValueError: The following consumers in the definition of 'select' have hooks that are not callable: {'fred': ['barney']}

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
            attr.validators.optional(attr.validators.instance_of(collections.MutableMapping))(self, name, value),
            [attr.validators.optional(attr.validators.instance_of(collections.MutableMapping))(self, name, v) for (k, v) in value.iteritems()] if isinstance(value, collections.MutableMapping) else None,
            self._validate_consumer(name, value) if isinstance(value, collections.MutableMapping) else None),
        repr=False)

    interpretations = attr.ib(
        default=attr.Factory(dict),
        validator=lambda self, name, value: (
            attr.validators.optional(attr.validators.instance_of(collections.MutableMapping))(self, name, value),
            self._validate_callable_mapping(name, value) if isinstance(value, collections.MutableMapping) else None),
        repr=False)

    outputters = attr.ib(
        default=attr.Factory(dict),
        validator=lambda self, name, value: (
            attr.validators.optional(attr.validators.instance_of(collections.Mapping))(self, name, value),
            [attr.validators.instance_of(str)(self, name, k) for k in value] if isinstance(value, collections.MutableMapping) else None,
            self._validate_callable_mapping(name, value) if isinstance(value, collections.MutableMapping) else None),
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
        bad_consumers = []
        bad_implementations = {}
        for consumer, rules in value.iteritems():
            if not isinstance(consumer, str) and not (isinstance(consumer, type) and issubclass(consumer, tokens.ParseUnit)):
                bad_consumers.append(consumer)
            elif rules is not None:
                for hook, value in rules.iteritems():
                    if not isinstance(hook, str):
                        bad_implementations[consumer] = bad_implementations.get(consumer, [])
                        bad_implementations[consumer].append(hook)
                    if value and not callable(value):
                        # The implementation of this hook is not a
                        # callable
                        not_callables[consumer] = not_callables.get(consumer, [])
                        not_callables[consumer].append(hook)
        else:
            if bad_implementations:
                # There were invalid implementations given
                raise ValueError((
                    ("The following consumers in the definition of '%s' have hooks names that are not strings: " % self.name) +
                    pprint.pformat(bad_implementations)))
            if bad_consumers:
                # There were invalid consumers given
                raise ValueError((
                    ("The following consumers in the definition of '%s' have consumers of the wrong type: " % self.name) +
                    pprint.pformat(bad_consumers)))
            if not_callables:
                # There were hook implementations that aren't callable
                raise ValueError((
                    ("The following consumers in the definition of '%s' have hooks that are not callable: " % self.name) +
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
        ...     tokens.Command: {'preconsume': lambda token, parent, interpreter: True},
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
        ...     tokens.Command: {'postconsume': lambda token, parent, interpreter: True},
        ...   })
        >>> pprint.pprint(click_postconsume.consumers) #doctest: +ELLIPSIS
        {<class 'tokens.Command'>: {'postconsume': <function <lambda> at 0x...>}}
        >>> click_copy.update(click_postconsume) is click_postconsume
        True
        >>> pprint.pprint(click_copy.consumers) #doctest: +ELLIPSIS
        {<class 'tokens.Command'>: {'postconsume': <function <lambda> at 0x...>,
                                    'preconsume': <function <lambda> at 0x...>}}

        If an implementation is Falsey, then it will be removed from the
        definitions when updates happen.
        >>> click_remove_postconsume = FullDefinition(
        ...   name='click',
        ...   token_type=tokens.Verb,
        ...   consumers={
        ...     tokens.Command: {'postconsume': None}})
        >>> click_copy.update(click_remove_postconsume) is click_remove_postconsume
        True
        >>> pprint.pprint(click_copy.consumers) #doctest: +ELLIPSIS
        {<class 'tokens.Command'>: {'preconsume': <function <lambda> at 0x...>}}

        Similarly, if a hook is None, updating will remove it completely
        from consumers.
        >>> click_remove_command_consumers = FullDefinition(
        ...   name='click',
        ...   token_type=tokens.Verb,
        ...   consumers={
        ...     tokens.Command: None})
        >>> click_copy.update(click_remove_command_consumers) is click_remove_command_consumers
        True
        >>> pprint.pprint(click_copy.consumers) #doctest: +ELLIPSIS
        {}

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
        is most likely to happen in the case of a Noun.
        >>> button = CompilableDefinition(
        ...   name='button',
        ...   token_type=tokens.Noun)
        >>> button_verb_interpretation = CompilableDefinition(
        ...   name='button',
        ...   token_type=tokens.Noun,
        ...   interpretations={
        ...     tokens.Verb: lambda token, context, interpreter: 'interpreting button'
        ...   })
        >>> pprint.pprint(button_verb_interpretation.interpretations) #doctest: +ELLIPSIS
        {<class 'tokens.Verb'>: <function <lambda> at 0x...>}
        >>> button.update(button_verb_interpretation) is button_verb_interpretation
        True
        >>> pprint.pprint(button.interpretations) #doctest: +ELLIPSIS
        {<class 'tokens.Verb'>: <function <lambda> at 0x...>}

        """
        def merge_implementations(self_implementations, other_implementations):
            """
            This merges the interior dict in a nested hook dict (such as
            consumers)
            """
            for hook, implementation in other_implementations.iteritems():
                if hook in self_implementations:
                    if not implementation:
                        # This is a cue to remove the implementation
                        del self_implementations[hook]
                    else:
                        self_implementations[hook] = implementation
                else:
                    self_implementations[hook] = implementation

        def update_hooks(self_hooks, other_hooks, merge, merge_implementations_func=lambda x, y:None):
            """
            This is a function used to update dicts of hooks
            (consumers, interpretations, outputters).  It takes a
            collback function so that it can handle nested dicts of
            hooks like consumers.
            """
            for cls, hooks in other_hooks.iteritems():
                if cls in self_hooks:
                    if hooks is None:
                        # This is a cue to remove this hook
                        del self_hooks[cls]
                    elif merge and self_hooks[cls] is not None:
                        merge_implementations_func(self_hooks[cls], hooks)
                    else:
                        self_hooks[cls] = hooks
                else:
                    self_hooks[cls] = hooks

        super(FullDefinition, self).update(other, merge=merge)
        if not (issubclass(other.token_type, self.token_type) or issubclass(self.token_type, other.token_type)):
            raise ValueError(
                "Definition '%s' cannot be updated with '%s', token_type mismatch" % (self.name, other.name))
        if self.name != other.name:
            raise ValueError(
                "Definition '%s' cannot be updated with '%s', name mismatch" % (self.name, other.name))

        self.pattern = (other.pattern or self.pattern) if merge else other.pattern
        try:
            other_consumers = copy.deepcopy(other.consumers)
        except AttributeError as ae:
            # This attribute is not in other, so skip
            pass
        else:
            update_hooks(self.consumers, other_consumers, merge, merge_implementations)
        try:
            other_outputters = copy.deepcopy(other.outputters)
        except AttributeError as ae:
            # This attribute is not in other, so skip
            pass
        else:
            update_hooks(self.outputters, other_outputters, merge)
        try:
            other_interpretations = copy.deepcopy(other.interpretations)
        except AttributeError as ae:
            # This attribute is not in other, so skip
            pass
        else:
            update_hooks(self.interpretations, other_interpretations, merge)
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
        if not (issubclass(other.token_type, self.token_type) or issubclass(self.token_type, other.token_type)):
            raise ValueError(
                "Definition '%s' cannot be updated with '%s', token_type mismatch" % (self.name, other.name))
        try:
            other_good_xpath_templates = copy.deepcopy(other.good_xpath_templates)
        except AttributeError as ae:
            # The attribute's not there, pass
            pass
        else:
            self.good_xpath_templates = (self.good_xpath_templates | other_good_xpath_templates) if merge else other_good_xpath_templates
        try:
            other_sloppy_xpath_templates = copy.deepcopy(other.sloppy_xpath_templates)
        except AttributeError as ae:
            # The attribute's not there, pass
            pass
        else:
            self.sloppy_xpath_templates = (self.sloppy_xpath_templates | other_sloppy_xpath_templates) if merge else other_sloppy_xpath_templates
        try:
            other_filters = copy.deepcopy(other.sloppy_xpath_templates)
        except AttributeError as ae:
            # The attribute's not there, pass
            pass
        else:
            self.sloppy_xpath_templates = (self.sloppy_xpath_templates | other_filters) if merge else other_filters
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
    >>> alias.token_type
    <class 'tokens.Verb'>

    If one tries to set an attribute that an alias doesn't have, it will
    try and set the attribute in the target.
    >>> alias.token_type = tokens.Noun
    >>> alias.token_type
    <class 'tokens.Noun'>
    >>> base_definition.token_type
    <class 'tokens.Noun'>
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

    def __setattr__(self, name, value):
        if name in self.__slots__:
            # this is an attribute we have locally, so set it locally.
            # We need to engage in some shenanigans using the descriptor
            # for it on our class, because this is an object using
            # __slots__, so it doesn't have a dict
            type(self).__dict__[name].__set__(self, value)
        else:
            setattr(self.target, name, value)
        return value

    def _validate_target_cycles(self, name, value):
        v = value
        while isinstance(v, DefinitionAlias):
            if v.target is self:
                raise ValueError(
                    "Cannot create cyclical alias: %s -> %s" % (self.name, v.name))
            else:
                v = v.target
        return True

    @property
    def type(self):
        """
        Returns the type of this DefinitionAlias's ultimate target.

        First, we'll prove it with one level of indirection...
        >>> alias1 = DefinitionAlias(
        ...   name="alias1",
        ...   target=FullDefinition(
        ...     name="bob",
        ...     token_type=tokens.Verb))
        >>> alias1.type
        <class '__main__.FullDefinition'>

        And with two.
        >>> alias2 = DefinitionAlias(
        ...   name="alias2",
        ...   target=alias1.target)
        >>> alias2.type
        <class '__main__.FullDefinition'>
        """
        return self.target.type

    def update(self, other, merge=True):
        """
        Updates this DefinitionAlias and its target.

        First, create a Definition and an alias to test with.
        >>> click = FullDefinition(
        ...   name='click',
        ...   token_type=tokens.Verb)
        >>> alias = DefinitionAlias(
        ...   name='click',
        ...   target=click)

        If we update the DefinitionAlias, the pattern of the
        DefinitionAlias will be updated.  Other parts of the updating
        Definition will be applied to the target.
        >>> alias.pattern
        'click'
        >>> throwaway = alias.update(FullDefinition(
        ...   name='click',
        ...   pattern='fred',
        ...   token_type=tokens.Verb,
        ...   consumers={
        ...     tokens.Command:{}}))
        >>> alias.pattern
        'fred'
        >>> pprint.pprint(click.consumers)
        {<class 'tokens.Command'>: {}}

        If we make an alias to an alias, non-pattern updates will be
        applied to the eventual target.
        >>> alias2 = DefinitionAlias(
        ...   name='alias',
        ...   target=alias)
        >>> throwaway = alias2.update(FullDefinition(
        ...   name='alias',
        ...   token_type=tokens.Verb,
        ...   consumers={
        ...     tokens.Command:{
        ...       'preconsume':lambda token, parent, interpreter: 'preconsume'}}))
        >>> pprint.pprint(click.consumers) #doctest: +ELLIPSIS
        {<class 'tokens.Command'>: {'preconsume': <function <lambda> at 0x...>}}

        Update will raise an exception if the names don't match.
        >>> alias_wrong_name = DefinitionAlias(
        ...   name='alias wrong name',
        ...   target=alias)
        >>> alias.update(alias_wrong_name)
        Traceback (most recent call last):
          ...
        ValueError: Alias 'click' to Definition 'click' cannot be updated with 'alias wrong name', name mismatch

        Aliases can be used as a way to update a Definition from a
        Definiton with a different name.  It's sort of like casting in
        statically typed languages.
        >>> update_definition = FullDefinition(
        ...   name='some other name',
        ...   token_type=tokens.Verb,
        ...   consumers={
        ...     tokens.Command:{
        ...       'postconsume': lambda token, parent, interpreter: 'postconsume'}})
        >>> click.update(update_definition)
        Traceback (most recent call last):
          ...
        ValueError: Definition 'click' cannot be updated with 'some other name', name mismatch
        >>> throwaway = click.update(DefinitionAlias(
        ...   name='click',
        ...   pattern=click.pattern,
        ...   target=update_definition))
        >>> pprint.pprint(click.consumers) #doctest: +ELLIPSIS
        {<class 'tokens.Command'>: {'postconsume': <function <lambda> at 0x...>}}

        They cannot be used to update across token_type boundaries,
        though.
        >>> click.update(DefinitionAlias(
        ...   name='click',
        ...   target=FullDefinition(
        ...     name='alias',
        ...     token_type=tokens.Noun)))
        Traceback (most recent call last):
          ...
        ValueError: Definition 'click' cannot be updated with 'click', token_type mismatch
        """
        super(DefinitionAlias, self).update(other, merge=merge)
        me = self.target
        while hasattr(me, 'target'):
            me = me.target
        if not (issubclass(other.token_type, self.token_type) or issubclass(self.token_type, other.token_type)):
            raise ValueError(
                "Alias '%s' to Definition '%s' cannot be updated with '%s', token_type mismatch" % (self.name, me.name, other.name))
        if self.name != other.name:
            raise ValueError(
                "Alias '%s' to Definition '%s' cannot be updated with '%s', name mismatch" % (self.name, me.name, other.name))
        me.update(
            other=DefinitionAlias(
                name=me.name,
                pattern=other.pattern,
                target=other),
            merge=merge)
        self.pattern = (other.pattern or self.pattern) if merge else other.pattern
        self.title = (other.title or self.title) if merge else other.title
        attr.validate(self)
        return other

if __name__ == "__main__":
    import doctest
    print doctest.testmod()
