'''
Basic Modules -- Modules that implement basic commands and stucture of Vision.

The Lexicon at the beginning of each line in a basic interpreter will
be made like this.
>>> basic_lexicon = modules.Lexicon(
...   modules=ordered_set.OrderedSet([defaults, structure, interactive, basic_vision]))

It has the following modules available:
>>> pprint.pprint(basic_lexicon.available_modules)
OrderedSet([Module(name='defaults'), Module(name='structure'), Module(name='interactive'), Module(name='basic_vision')])

It has all the following keywords available:
>>> pprint.pprint(basic_lexicon.keys())
['set',
 'show all input',
 'help',
 'step into python',
 'file literal',
 'skip',
 'show context',
 'within',
 'attribute noun',
 'because',
 'tab',
 'close',
 'table',
 'click',
 'select',
 'row',
 'quit',
 'is skipped',
 'space',
 'image',
 'should contain',
 'literal',
 'cell',
 'window',
 'radio button',
 'navigate',
 'test',
 'dropdown',
 'should not exist',
 'type',
 'frame',
 'end test',
 'finish',
 'end require',
 'decline',
 'should exist',
 'verbosely',
 'alert',
 'break',
 'scope change',
 'hover',
 'link',
 'accept',
 'textfield',
 'next command',
 'run test',
 'capture',
 'textarea',
 'should not contain',
 'show input',
 'button',
 'should not be checked',
 'checkbox',
 'where',
 'switch',
 'text',
 'should be checked',
 'save test',
 'load test',
 'the',
 'show test']

A definition for a keyword can be accessed from a Lexicon by keyword.
>>> basic_lexicon['button']
FullDefinition(token_type=<class 'tokens.Noun'>, title='button', pattern='button')

The definitions that get returned are mergings of all the matching
defintions in the Lexicon, and are created on the fly, so a new object
will be returned each time.
>>> basic_lexicon['button'] is not basic_lexicon['button']
True
'''

# Python Libraries
import attr
import itertools
import functools
import platform
import types
import collections
import inspect
import pprint
import re
import ordered_set

# Vision Libraries
import tokens
import modules

# This module gets added to the Lexicon once a non-scope change token is
# tokenized.  It removes the scope-change definition from the Lexicon
_disable_scope_change = modules.Module(name='disable scope change')
_disable_scope_change.add_definition(
    name='scope change',
    definition=None)
# End disable scope change

# This module gets added to the Lexicon once the 'test' verb gets
# consumed.  It adds the 'using' keyword, which allows a module to be
# associated with a scope.
_module_loading = modules.Module(name='module loading')
_module_loading.add_definition(
    definition=modules.FullDefinition(
        name='using',
        token_type=tokens.CommandModifier))
# End module loading

# This module implements the type-based defaults.  It's going to be the
# root module for everything.
defaults = modules.Module(
    name='defaults',
    module_definitions={
        tokens.Noun:modules.CompilableDefinition,
        tokens.Token:modules.FullDefinition})
defaults.add_definition(modules.FullDefinition(
    name=None,
    token_type=tokens.Verb,
    consumers={
        tokens.Command:{}}))
defaults.add_definition(modules.FullDefinition(
    name=None,
    token_type=tokens.CommandModifier,
    consumers={
        tokens.Command:{}}))
defaults.add_definition(modules.FullDefinition(
    name=None,
    token_type=tokens.Literal,
    consumers={
        tokens.Noun:{},
        tokens.Verb:{},
        tokens.CommandModifier:{}}))
defaults.add_definition(modules.CompilableDefinition(
    name=None,
    token_type=tokens.Noun,
    consumers={
        tokens.Verb:{},
        tokens.InteractiveVerb:None,
        'switch':None,
        'select':None,
        'type':None,
        'accept':None,
        'decline':None,
        'should be checked':None,
        'should not be checked':None}))
# End defaults

# This implements the scoping structure of Vision
structure = modules.Module(
    name='structure',
    required_modules=ordered_set.OrderedSet([defaults]))
structure.add_definition(modules.FullDefinition(
    name='test',
    token_type=tokens.Verb,
    consumers={
        tokens.Command: {
            'posttokenize': lambda token, lexicon: lexicon.add_module(_module_loading),
            'postconsume': lambda token, parent, interpreter: setattr(token.command, 'scopechange', 1)}}))
structure.add_definition(modules.FullDefinition(
    name=None,
    token_type=tokens.ScopeChange,
    consumers={
        tokens.Command: {
            'posttokenize': lambda token, parent, interpreter: token.lexicon.add_module(_disable_scope_change)}}))
structure.add_definition(modules.FullDefinition(
    name='end test',
    token_type=tokens.Verb,
    consumers={
        tokens.Command: {
            'postconsume': lambda token, parent, interpreter: setattr(token.command, 'scopechange', -1),}}))
structure.add_definition(modules.FullDefinition(
    name='scope change',
    pattern='    ',
    token_type=tokens.ScopeChange))
# End structure

# This implements the interactive commands in Vision
interactive = modules.Module(
    name='interactive',
    required_modules=ordered_set.OrderedSet([defaults]))
interactive.add_definition(modules.FullDefinition(
    name='end test',
    token_type=tokens.InteractiveVerb))
interactive.add_definition(modules.FullDefinition(
    name='end require',
    token_type=tokens.InteractiveVerb))
interactive.add_definition(modules.FullDefinition(
    name='set',
    token_type=tokens.InteractiveVerb))
interactive.add_definition(modules.FullDefinition(
    name='load test',
    token_type=tokens.InteractiveVerb))
interactive.add_definition(modules.FullDefinition(
    name='run test',
    token_type=tokens.InteractiveVerb))
interactive.add_definition(modules.FullDefinition(
    name='save test',
    token_type=tokens.InteractiveVerb))
interactive.add_definition(modules.FullDefinition(
    name='show context',
    token_type=tokens.InteractiveVerb))
interactive.add_definition(modules.FullDefinition(
    name='where',
    token_type=tokens.InteractiveVerb))
interactive.add_definition(modules.FullDefinition(
    name='show test',
    token_type=tokens.InteractiveVerb))
interactive.add_definition(modules.FullDefinition(
    name='show input',
    token_type=tokens.InteractiveVerb))
interactive.add_definition(modules.FullDefinition(
    name='show all input',
    token_type=tokens.InteractiveVerb))
interactive.add_definition(modules.FullDefinition(
    name='skip',
    token_type=tokens.InteractiveVerb))
interactive.add_definition(modules.FullDefinition(
    name='next command',
    token_type=tokens.InteractiveVerb))
interactive.add_definition(modules.FullDefinition(
    name='break',
    token_type=tokens.InteractiveVerb))
interactive.add_definition(modules.FullDefinition(
    name='step into python',
    token_type=tokens.InteractiveVerb))
interactive.add_definition(modules.FullDefinition(
    name='quit',
    token_type=tokens.InteractiveVerb))
interactive.add_definition(modules.FullDefinition(
    name='finish',
    token_type=tokens.InteractiveVerb))
interactive.add_definition(modules.FullDefinition(
    name='help',
    token_type=tokens.InteractiveVerb,
    consumers={
        tokens.Command:{
            'posttokenize': lambda token, parent, interpreter: token.command.lexicon.add_module(_module_loading)}}))
# End interactive

# This implements the basic keywords for the webdriver
basic_vision = modules.Module(
    name='basic_vision',
    required_modules=ordered_set.OrderedSet([defaults]))

# Literals
basic_vision.add_definition(modules.FullDefinition(
    name='literal',
    pattern=r"""(["'])(?:(?!\1).)*\1""",
    token_type=tokens.Literal))
defaults.add_definition(modules.FullDefinition(
    name='file literal',
    pattern=r"""<[^<]*>""",
    token_type=tokens.FileLiteral,
    consumers={
        tokens.Noun:{},
        tokens.Verb:{},
        tokens.CommandModifier:{}}))
# end Literals

# Seperators
basic_vision.add_definition(modules.FullDefinition(
    name='space',
    pattern=' ',
    token_type=tokens.Seperator,
    consumers={
        tokens.ParseUnit:{},
        tokens.Literal:None,
        tokens.Ordinal:None}))
basic_vision.add_definition(modules.DefinitionAlias(
    name='tab',
    pattern='\t',
    target=basic_vision.definitions['space']))
# end Seperators

# StreamReorderers
basic_vision.add_definition(modules.FullDefinition(
    name='the',
    token_type=tokens.Token,
    consumers={
        tokens.Noun:{}}))
# end StreamReorderers

# Nouns
basic_vision.add_definition(modules.CompilableDefinition(
    name='attribute noun',
    pattern=r"""{[^{=]*=[^{=]*}""",
    token_type=tokens.AttributeNoun))
basic_vision.add_definition(modules.CompilableDefinition(
    name='button',
    token_type=tokens.Noun))
basic_vision.add_definition(modules.CompilableDefinition(
    name='link',
    token_type=tokens.Noun))
basic_vision.add_definition(modules.CompilableDefinition(
    name='radio button',
    token_type=tokens.Noun,
    consumers={
        'should be checked':{},
        'should not be checked':{}}))
basic_vision.add_definition(modules.CompilableDefinition(
    name='checkbox',
    token_type=tokens.Noun,
    consumers={
        'should be checked':{},
        'should not be checked':{}}))
basic_vision.add_definition(modules.CompilableDefinition(
    name='textfield',
    token_type=tokens.Noun,
    consumers={
        'type':{}}))
basic_vision.add_definition(modules.CompilableDefinition(
    name='textarea',
    token_type=tokens.Noun,
    consumers={
        'type':{}}))
basic_vision.add_definition(modules.CompilableDefinition(
    name='dropdown',
    token_type=tokens.Noun))
basic_vision.add_definition(modules.CompilableDefinition(
    name='table',
    token_type=tokens.Noun))
basic_vision.add_definition(modules.CompilableDefinition(
    name='row',
    token_type=tokens.Noun))
basic_vision.add_definition(modules.FullDefinition(
    name='cell',
    token_type=tokens.Noun))
basic_vision.add_definition(modules.CompilableDefinition(
    name='text',
    token_type=tokens.Noun))
basic_vision.add_definition(modules.CompilableDefinition(
    name='image',
    token_type=tokens.Noun))
basic_vision.add_definition(modules.FullDefinition(
    name='alert',
    token_type=tokens.Noun,
    consumers={
        tokens.Verb:None,
        'accept':{},
        'decline':{}}))
basic_vision.add_definition(modules.FullDefinition(
    name='window',
    token_type=tokens.Noun,
    consumers={
        tokens.Verb:None,
        'switch':{},
        'close':{}}))
basic_vision.add_definition(modules.FullDefinition(
    name='frame',
    token_type=tokens.Noun,
    consumers={
        tokens.Verb:None,
        'switch':{}}))
#end Nouns

# Verbs
basic_vision.add_definition(modules.FullDefinition(
    name='click',
    token_type=tokens.Verb))
basic_vision.add_definition(modules.FullDefinition(
    name='type',
    token_type=tokens.Verb))
basic_vision.add_definition(modules.FullDefinition(
    name='select',
    token_type=tokens.Verb))
basic_vision.add_definition(modules.FullDefinition(
    name='hover',
    token_type=tokens.Verb))
basic_vision.add_definition(modules.FullDefinition(
    name='navigate',
    token_type=tokens.Verb))
basic_vision.add_definition(modules.FullDefinition(
    name='accept',
    token_type=tokens.Verb))
basic_vision.add_definition(modules.FullDefinition(
    name='decline',
    token_type=tokens.Verb))
basic_vision.add_definition(modules.FullDefinition(
    name='switch',
    token_type=tokens.Verb))
basic_vision.add_definition(modules.FullDefinition(
    name='capture',
    token_type=tokens.Verb))
basic_vision.add_definition(modules.FullDefinition(
    name='close',
    token_type=tokens.Verb))
basic_vision.add_definition(modules.FullDefinition(
    name='should contain',
    token_type=tokens.Verb))
basic_vision.add_definition(modules.FullDefinition(
    name='should not contain',
    token_type=tokens.Verb))
basic_vision.add_definition(modules.FullDefinition(
    name='should exist',
    token_type=tokens.Verb))
basic_vision.add_definition(modules.FullDefinition(
    name='should not exist',
    token_type=tokens.Verb))
basic_vision.add_definition(modules.FullDefinition(
    name='should be checked',
    token_type=tokens.Verb))
basic_vision.add_definition(modules.FullDefinition(
    name='should not be checked',
    token_type=tokens.Verb))
# end Verbs

# CommandModifiers
basic_vision.add_definition(modules.FullDefinition(
    name='is skipped',
    token_type=tokens.CommandModifier))
basic_vision.add_definition(modules.FullDefinition(
    name='because',
    token_type=tokens.CommandModifier))
basic_vision.add_definition(modules.FullDefinition(
    name='within',
    token_type=tokens.CommandModifier))
basic_vision.add_definition(modules.FullDefinition(
    name='verbosely',
    token_type=tokens.CommandModifier))
# end CommandModifiers
# End basic vision

if __name__ == "__main__":
    import doctest
    print doctest.testmod()
