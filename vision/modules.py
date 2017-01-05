"""
This file implements Modules and Definitions.
"""

# Python Libraries
import attr
import pprint
import ordered_set
import collections

# Vision Libraries
import tokens

#@attr.s(slots=True)
#class Lexicon(object):
#    """
#    This is an ephemeral object that keeps track of what modules are
#    currently available and supplies the definitions for the currently
#    available keywords, after merging them together.
#    """
#
#
#    """
#    To add definitions to the module, use the add_definition method.
#    This will add a very simple implmentation of a 'click' keyword.
#    >>> def print_it(text):
#    ...   print text
#    ...   return True
#    >>> module.add_definition(FullDefinition(
#    ...   name='click',
#    ...   modules=[module],
#    ...   token_type=tokens.Verb,
#    ...   consumers={
#    ...     tokens.Command: {},},
#    ...   outputters={
#    ...     'raw': lambda token: print_it("Raw output of a click"),
#    ...     'prettified': lambda token: print_it("Prettified output of a click"),},
#    ...   interpretation=lambda token, interpreter: print_it("Clicked a thing!"),))
#
#    """

@attr.s(slots=True)
class Module(object):
    """
    A group of Definitions, and the methods necessary to merge modules
    into combination modules.
    """

    name = attr.ib(
        validator=attr.validators.instance_of(str))
    module_tokens = attr.ib(
        default=attr.Factory(dict),
        validator=attr.validators.instance_of(collections.Mapping),
        repr=False)
    definitions = attr.ib(
        default=attr.Factory(dict),
        init=False,
        validator=lambda self, name, value: (
            attr.validators.instance_of(collections.MutableMapping) and
            self._validate_difinitions(name, value)),
        repr=False)
    required_modules = attr.ib(
        default=attr.Factory(ordered_set.OrderedSet),
        validator=lambda self, name, value: (
            attr.validators.instance_of(collections.Sequence)(self, name, value) and 
            [attr.validators.instance_of((str, Module))(self, name, v) for v in values]),
        repr=True)

    """
    Modules hold definitions for how to handle the different keywords in
    a particular module, such as a module for handling jqWidgets, or for
    basic modules, like the one for html.

    >>> module = Module(name='testmodule')
    >>> module

    Modules have a mapping of root token types to the class that
    actually implements them, called module_tokens.  By default, this is
    just a mapping of each class descended from ParseUnit in the tokens
    module to itself.
    >>> pprint.pprint(module.module_tokens)

    Modules have a mapping of definition names to their respective
    definitions.
    >>> pprint.pprint(module.definitions)

    Modules can require other modules to already be loaded.  The
    required_modules tuple keeps those modules, and the order in which
    they must be loaded.  We'll add a couple more modules so that they
    can require one another to demonstrate.
    >>> module2 = Module(
    ...   name='testmodule2',
    ...   required_modules=[
    ...     module,
    ...     Module(name='testmodule1a')])
    >>> pprint.pprint(module2.required_modules)

    It is possible to see all the modules that this module is guaranteed
    to have access to, based on its required modules, and their
    requirements, etc.  We'll create yet another module to demonstrate
    that.
    >>> module3 = Module(
    ...   name='testmodule3',
    ...   required_modules=[module3])
    >>> pprint.pprint(module3.available_modules)

    """

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

        new_required = ordered_set.OrderedSet()
        for mod in self.required_modules:
            if not isinstance(mod, Module):
                mod = Module.load_module(mod)
            new_required.append(mod)
        self.required_modules = new_required

    def _validate_definitions(self, name, value):
        bad_definitions = dict(
            (name, defintion) for (name, definition) in value.iteritems() if
            not isinstance(definition, Definition) and definition.name == name)
        if bad_definitions:
            raise ValueError((
                "There are definitions that are not of the right type or "
                "have mismatched names:\n%s" % (pprint.pformat(bad_definitions))))
        return True

    @property
    def available_modules(self):
        available = ordered_set.OrderedSet()
        for module in self.required_modules.values():
            available |= module.available_modules
        available.append(self)
        return available

    @classmethod
    def load_module(cls, name):
        """
        This will load a Vision module and return it.
        """
        return getattr(importlib.import_module(name), name.rsplit(".")[-1])

    def add_definition(self, definition, merge=True):
        """
        Add a definition to the module's definition list.  If the
        definition is already there, the new is merged with the old.
        If the definition is an alias, then it is added to the backlinks
        in the aliased definition.
        """

        if definition.name in self.definitions:
            my_definition = copy.deepcopy(self.definitions[definition.name])
            my_definition.update(definition, merge)
            definition = my_definition
        self.definitions[definition.name] = definition
        if hasattr(definition, 'target_name'):
            if definition.target_name in definition.module.definitions:
                definition.module.defintions[self.target_name].aliases |= ordered_set.OrderedSet([self])
            for dname, ddef in definition.definitions.items():
                if definition.target_name == dname:
                    ddef.aliases |= ddef

    def remove_definition(self, definition):
        """
        This removes a definition from the module, as well as any
        aliases to it.
        >>> module = Module(name='testmodule')
        >>> module.add_definition(
        ...   FullDefinition(
        ...     name='click',
        ...     token_type=tokens.Verb))
        >>> module.add_definition(
        ...   DefinitionAlias(
        ...     name='clack',
        ...     module=module,
        ...     target_name='click'))
        >>> pprint.pprint(module.definitions)
        >>> module.remove_definition('click')
        >>> pprint.pprint(module.definitions)

        If the definition we remove is an alias, then the backreference
        in its target is removed as well.
        >>> module.add_definition(
        ...   FullDefinition(
        ...     name='click',
        ...     token_type=tokens.Verb))
        >>> module.add_definition(
        ...   DefinitionAlias(
        ...     name='clack',
        ...     module=module,
        ...     target_name='click'))
        >>> pprint.pprint(module.definitions)
        >>> module.remove_definition('clack')
        >>> pprint.pprint(module.definitions)
        >>> pprint.pprint(module.definitions['click'].aliases)
        """
        definition = self.definitions.get(definition, definition)
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
    """

    token_type = attr.ib(
        validator=attr.validators.instance_of(tokens.ParseUnit))
    """
    token_type is the type of token this keyword will generate.  It's
    here more as a marker than as the type that will actually be used,
    as it's possible some modules may define their own token types
    decended from the ones provided in the tokens python module.
    token_type must be a ParseUnit.
    >>> parse_unit_token_type = FullDefinition(
    ...   name='parse_unit',
    ...   token_type=tokens.Verb)
    >>> parse_unit_token_type

    An exception will be raised if the token_type is not provided...
    >>> must_provide_a_token_type = FullDefinition(
    ...   name='no token type')

    or if the token_type is not a ParseUnit.
    >>> token_type_must_be_parse_unit = FullDefinition(
    ...   name='no token type',
    ...   token_type=None)
    """

    name = attr.ib(
        default=None,
        validator=attr.validators.optional(attr.validators.instance_of(str)))
    """
    name is the name of a keyword definition, which will be used to look
    it up in the Module.  If this is None, then this is a definition
    that will be used as a base for all tokens of this token_type.
    """

    pattern = attr.ib(
        default=None,
        validator=attr.validators.optional(attr.validators.instance_of(str)))
    """
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
    """

    modules = attr.ib(
        default=attr.Factory(list),
        init=False,
        validator=lambda self, name, value: (
            att.validators.instance_of(collections.Sequence)(self, name, value) and
            [att.validators.instance_of(Module)(self, name, v) for v in values] and
            value[0]))
    """
    modules keeps track of what modules have updated this definition
    from their own definitions or registered it.  It cannot be provided at initialization...
    >>> cant_provide_modules = FullDefinition(
    ...   name='select',
    ...   token_type=tokens.Verb,
    ...   modules=['fred', 'barney'])

    But is updated when a definition is added to a module...
    >>> module = Module(name='testmodule')
    >>> click_copy = copy.deepcopy(click)
    >>> pprint.pprint(click_copy.modules)
    >>> module.add_definition(click_copy)
    >>> pprint.pprint(click_copy.modules)

    Or when .update() is used (more on this later).
    """

    consumers = attr.ib(
        default=attr.Factory(dict),
        validator=lambda self, name, value: (
            attr.validators.instance_of(collections.MutableMapping)(self, name, value) and
            [attr.validators.instance_of(collections.MutableMapping)(self, k, v) for (k, v) in value.iteritems()] and
            self._validate_consumer(name, value)),
        repr=False)
    """
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
    ...   consumer=5)

    >>> consumers_mapping_keys_are_tokens_or_strings = FullDefinition(
    ...   name='select',
    ...   token_type=tokens.Verb,
    ...   consumer={5:None})

    >>> consumers_mapping_values_are_mappings = FullDefinition(
    ...   name='select',
    ...   token_type=tokens.Verb,
    ...   consumers={'fred':None})

    >>> consumers_inner_mapping_keys_are_strings = FullDefinition(
    ...   name='select',
    ...   token_type=tokens.Verb,
    ...   consumers={'fred':{5:None}})

    >>> consumers_inner_mapping_values_are_callables = FullDefinition(
    ...   name='select',
    ...   token_type=tokens.Verb,
    ...   consumers={'fred':{'barney':None}})

    """

    interpretations = attr.ib(
        default=attr.Factory(dict),
        validator=lambda self, name, value: (
            attr.validators.instance_of(collections.MutableMapping)(self, name, value) and
            [attr.validators.instance_of(str, tokens.ParseUnit)(self, name, k) for k in value] and
            self._validate_callable_mapping(name, value)),
        repr=False)
    """
    interpreters provides a way for tokens to be interpreted differently
    based on their parent tokens.  This is a Mapping of consumers ->
    callables.  The consumer is either a string or a ParseUnit.  If
    these conditions are not met, an exception is raised.
    >>> interpretations_must_be_a_mapping = FullDefinition(
    ...   name='select',
    ...   token_type=tokens.Verb,
    ...   interpretations=5)

    >>> interpretations_mapping_keys_are_tokens_or_strings = FullDefinition(
    ...   name='select',
    ...   token_type=tokens.Verb,
    ...   interpretations={5:None})

    >>> interpretations_mapping_values_are_callables = FullDefinition(
    ...   name='select',
    ...   token_type=tokens.Verb,
    ...   interpretations={'fred':None})
    """

    outputters = attr.ib(
        default=attr.Factory(dict),
        validator=lambda self, name, value: (
            attr.validators.instance_of(collections.Mapping)(self, name, value) and
            [attr.validators.instance_of(str)(self, name, k) for k in value] and
            self._validate_callable_mapping(name, value)),
        repr=False)
    """
    outputters tells how to output a token in different situations.  It
    is a Mapping of string -> callable, where the string is a particular
    kind of output, and the callable is how to get that output.  If
    these conditions are not met, and exception is raised.
    >>> outputters_must_be_a_mapping = FullDefinition(
    ...   name='select',
    ...   token_type=tokens.Verb,
    ...   outputters=5)

    >>> outputters_mapping_keys_are_strings = FullDefinition(
    ...   name='select',
    ...   token_type=tokens.Verb,
    ...   outputters={5:None})

    >>> outputters_mapping_values_are_callables = FullDefinition(
    ...   name='select',
    ...   token_type=tokens.Verb,
    ...   outputters={'fred':None})
    """

    aliases = attr.ib(
        init=False,
        default=attr.Factory(ordered_set.OrderedSet),
        validator=attr.validators.instance_of(collections.Sequence),
        repr=False)
    """
    aliases is an OrderedSet of the aliases to this Definition.  This is
    here so that if the definition is removed, the aliases can be as
    well.  It is not provided to the init function, if one tries, and
    exception is raised.
    >>> cant_provide_aliases = FullDefinition(
    ...   name='select',
    ...   token_type=tokens.Verb,
    ...   aliases=[])
    """

    def __attrs_post_init__(self):
        """
        Set up the token_type to be whatever the matching token_type in
        its modules module_tokens mapping is.  Also set up the pattern
        to be based on the name, if none is provided.
        """
        for module in reversed(self.modules):
            if self.token_type in module.module_tokens:
                self.token_type = module.module_tokens[self.token_type]
                break

        if self.pattern is None and self.name is not None:
            self.pattern = r"[ \t]+".join(self.name.split)

    def __eq__(self, other):
        return isinstance(other, Definition) and self.name==other.name and isinstance(other.token_type, type(self.token_type))

    def _validate_callable_mapping(self, name, value):
        bad_outputters = dict((k, v) for (k, v) in value.items() if not callable(v))
        if bad_outputters:
            raise ValueError((
                ("The following %s in the definition of %s:%s have uncallable values\n" % (name, self.module.name, self.name)) +
                pprint.pformat(bad_outputters)))

    def _validate_consumer(self, name, value):
        consumer = set(value)
        available = set.union(*[set(module.all_definitions) for module in self.modules])
        if not consumer <= available:
            # if we have a key in the definition that is not represented
            # in the definitions that our module has access to, raise an
            # error
            raise ValueError((
                "The following consumers in the definition of %s:%s are"
                "not available from its module: %s") % (
                    self.module.name, self.name, consumer - available))
        not_callables = {}
        bad_consumers = {}
        for consumer, rules in value.iteritems():
            if not isinstance(consumer, (str, tokens.ParseUnit)):
                bad_consumers[consumer] = type(consumer)
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
                    ("The following consumers in the definition of %s:%s have consumers of the wrong type\n" % (self.module.name, self.name)) +
                    pprint.pformat(bad_consumers)))
            if not_callables:
                # There were hook implementations that aren't callable
                raise ValueError((
                    ("The following consumerss in the definition of %s:%s have hooks that are not callable\n" % (self.module.name, self.name)) +
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

        An exception is raised if the updating definition has a
        different name...
        >>> update_wrong_name = Definition(
        ...   name='click wrong name',
        ...   token_type=tokens.Verb)
        >>> verb_copy.update(update_wrong_name)

        Or if the token_types are different.
        >>> update_wrong_token_type = Definition(
        ...   token_type=tokens.Noun)
        >>> verb_copy.update(update_wrong_token_type)

        We can update one defintition with another to change the pattern.
        >>> click_copy = copy.deepcopy(click)
        >>> click_copy.pattern
        >>> update_pattern = FullDefinition(
        ...   name='click',
        ...   token_type=tokens.Verb,
        ...   pattern='otherpattern')
        >>> update_pattern.pattern
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
        For modules, update will append the modules from other to the
        end...
        >>> module1 = Module(name='testmodule')
        >>> module1.add_definition(
        ...   click_copy)
        >>> click_copy.modules
        >>> click_copy2 = copy.deepcopy(click)
        >>> module2 = Module(name='testmodule2')
        >>> module2.add_definition(
        ...   click_copy2)
        >>> click_copy2.modules
        >>> click_copy.update(click_copy2) is click_copy2
        True
        >>> click_copy.modules

        Unless they are already in self.
        >>> click_copy3 = copy.deepcopy(click)
        >>> module2.add_definition(
        ...   click_copy3)
        >>> click_copy3.modules
        >>> click_copy.update(click_copy3) is click_copy3
        True
        >>> click_copy.modules

        Consumers will be merged, hook by hook.  If a hook exists for a
        consumer, new implementations will be added to it via the update
        method unless merge is set to False.
        >>> click_preconsume = FullDefinition(
        ...   name='click',
        ...   token_type=tokens.Verb,
        ...   consumers={
        ...     tokens.Command: {'preconsume': lambda token, interpreter: True},
        ...   })
        >>> pprint.pprint(click_preconsume.consumers)
        >>> click_copy.update(click_preconsume) is click_preconsume
        True
        >>> pprint.pprint(click_copy.consumers)
        >>> click_postconsume = FullDefinition(
        ...   name='click',
        ...   token_type=tokens.Verb,
        ...   consumers={
        ...     tokens.Command: {'postconsume': lambda token, interpreter: True},
        ...   })
        >>> pprint.pprint(click_postconsume.consumers)
        >>> click_copy.update(click_postconsume) is click_postconsume
        True
        >>> pprint.pprint(click_copy.consumers)

        Outputters are updated via the update method of the mapping
        unless merge is set to False.
        >>> click_raw_outputter = FullDefinition(
        ...   name='click',
        ...   token_type=tokens.Verb,
        ...   outputters={
        ...     'raw': lambda token: str(token),
        ...   })
        >>> pprint.pprint(click_raw_outputter.outputters)
        >>> click_copy.update(click_raw_outputter) is >>> click_raw_outputter
        True
        >>> pprint.pprint(click_copy.outputters)

        Interpretations will be merged the same way as outputters.  This
        is most likely to happen in the case of a Noun, so we'll show an
        example of that in the update method for CompilableDefinition.
        """
        if self.name != other.name:
            raise ValueError(
                "Definition '%s' cannot be updated with '%s', name mismatch" % (self.name, other.name))
        if not isinstance(other.token_type, type(self.token_type)):
            raise ValueError(
                "Definition '%s' cannot be updated with '%s', token_type mismatch" % (self.name, other.name))

        if isinstance(other, FullDefinition):
            other_copy = copy.deepcopy(other)
            modules = collections.OrderedDict(zip(self.modules, itertools.repeat(True)) if merge else {})
            for module in other_copy.modules:
                modules[module] = True
            self.modules = modules.keys()
            self.pattern = (other_copy.pattern or self.pattern) if merge else other_copy.pattern
            for consumer, hooks in other_copy.consumer.iteritems():
                hooks = copy.deepcopy(hooks)
                if merge and consumer in self.consumer:
                    for hook, implementation in hooks:
                        if hook in self.consumer[consumer]:
                            self.consumer[consumer][hook].update(hooks[hook])
                        else:
                            self.consumer[consumer][hook] = hooks[hook]
                else:
                    self.consumer[consumer] = hooks
            if merge:
                self.interpretations.update(other_copy.interpretations)
                self.outputters.update(other_copy.outputters)
            else:
                self.interpretations = other_copy.interpretations
                self.outputters = other_copy.outputters
            self.validate(self)
        return other

@attr.s(slots=True)
class CompilableDefinition(FullDefinition):
    """
    This is a definition for tokens that can be compiled to xpaths.
    """
    good_xpath_templates = attr.ib(
        default=attr.Factory(list),
        validator=lambda self, name, value: (
            attr.validators.instance_of(collections.Sequence)(self, name, value) and
            [attr.validators.instance_of(str)(self, name, v) for v in value]),
        repr=False)

    """
    good_xpath_templates is a Sequence of strings representing the
    xpaths matching html that is considered "good form" to use.  These
    wlll not result in a warning if the element is found using these.
    An exception is raised if it is not a Sequence of strings.
    >>> xpaths_must_be_sequences = CompilableDefinition(
    ...   name='button',
    ...   token_type=tokens.Noun,
    ...   good_xpath_templates=5)

    >>> xpaths_must_be_sequences_of_strings = CompilableDefinition(
    ...   name='button',
    ...   token_type=tokens.Noun,
    ...   good_xpath_templates=[5])
    """

    sloppy_xpath_templates = attr.ib(
        default=attr.Factory(list),
        validator=lambda self, name, value: (
            attr.validators.instance_of(collections.Sequence)(self, name, value) and
            [attr.validators.instance_of(str)(self, name, v) for v in value] and
            self._validate_sloppy_xpath_templates(name, value)),
        repr=False)
    """
    sloppy_xpath_templates is a Sequence of strings representing xpaths
    matching html that is considered "sloppy".  These will result in
    warnings, and errors in pedantic mode.  They will always be used
    after all good xpaths have failed.  This must be a Sequence of
    strings, and none of them can match any of the "good" xpaths.  If
    these requirements are not matched, and exception is raised.
    >>> xpaths_must_be_sequences = CompilableDefinition(
    ...   name='button',
    ...   token_type=tokens.Noun,
    ...   sloppy_xpath_templates=5)

    >>> xpaths_must_be_sequences_of_strings = CompilableDefinition(
    ...   name='button',
    ...   token_type=tokens.Noun,
    ...   sloppy_xpath_templates=[5])

    >>> sloopy_xpaths_must_not_match_good = CompilableDefinition(
    ...   name='button',
    ...   token_type=tokens.Noun,
    ...   good_xpath_templates=['./descendant::button[@value="%{value}s"]'],
    ...   sloppy_xpath_templates=['./descendant::button[@value="%{value}s"]'])
    """

    filters = attr.ib(
        default=lambda token, interpreter: True,
        validator=lambda self, name, value: (
            attrs.validators.instance_of(collections.Sequence)(self, name, value) and
            self._validate_filters(name, value)),
        repr=False)
    """
    filters is a Sequence of callables that will be called to filter out
    elements that would otherwise match (such as those that are not
    clickable) or to perform operations on the element (such as
    scrolling it to the center of the screen to make screenshots
    easier).  An exception is raised if this is not a Sequnce of
    callables.
    >>> filters_must_be_sequences = CompilableDefinition(
    ...   name='button',
    ...   token_type=tokens.Noun,
    ...   sloppy_xpath_templates=5)

    >>> filters_must_be_sequences_of_callables = CompilableDefinition(
    ...   name='button',
    ...   token_type=tokens.Noun,
    ...   sloppy_xpath_templates=[5])
    """

    def _validate_sloppy_xpath_templates(self, name, value):
        both = set(value) & set(self.good_xpath_templates)
        if both:
            # There are xpath templates that are both good and sloppy,
            # raise a ValueError
            raise ValueError(
                "The following templates are in both 'good' and 'sloppy':\n%s" % (
                    pprint.pformat(both)))
        return True

    def _validate_filters(self, name, value):
        bad_filters = [f for f in values if not callable(f)]
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
            other_copy = copy.deepcopy(other)
            self.good_xpath_templates = (self.good_xpath_templates + other_copy.good_xpath_templates) if merge else other_copy.good_xpath_templates
            self.sloppy_xpath_templates = (self.sloppy_xpath_templates + other_copy.sloppy_xpath_templates) if merge else other_copy.sloppy_xpath_templates
            self.center = (self.center + other_copy.center) if merge else other_copy.center
        self.validate(self)
        return other

@attr.s(slots=True)
class DefinitionAlias(Definition):
    """
    This represents the definition of a keyword that is just an alias
    for another keyword.
    """
    module = attr.ib(
        validator=attr.validators.instance_of(Module))
    target_name = attr.ib(
        validator=lambda self, name, value: (
            attr.validators.instance_of(str)) and
            self._validate_target_name(name, value))
    pattern = attr.ib(
        default=None,
        validator=attr.validators.optional(attr.validators.instance_of(str)))

    """
    An alias is intended to use all the information from its target
    definition except for the information regarding tokenization.
    >>> module = Module(name="bedrock")
    >>> base_definition = FullDefinition(
    ...   name="fred",
    ...   token_type=tokens.Verb)
    >>> base_definition
    >>> module.add_definition(base_definition)
    >>> alias = DefinitionAlias(
    ...   name="flintstone",
    ...   module=module,
    ...   target_name="fred")
    >>> alias

    If one tries to get an attribute that an alias does not have, it
    will try to retrieve from its target.
    >>> alias.modules
    """

    def __attrs_post_init__(self):
        """
        Set up the token_type to be whatever the matching token_type in
        its modules module_tokens mapping is.  Also set up the pattern
        to be based on the name, if none is provided.
        """

        if self.pattern is None:
            self.pattern = r"[ \t]+".join(self.name.split)

        self.module.definitions[self.target_name].aliases.append(self)

    def _validate_target_name(self, name, value):
        if value not in self.module.definitions:
            raise ValueError(
                "There is no defintion '%s' in module '%s', required for '%s'" % (value, self.module.name, self.name))

    def __getattr__(self, name):
        return getattr(self.module.definitions[self.target_name], name)

if __name__ == "__main__":
    import doctest
    doctest.testmod()
