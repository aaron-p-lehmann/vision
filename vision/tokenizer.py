"""
This implements the tokenizer which takes Commands with no tokens and
splits it up into tokens, one token per keyword.
"""

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

@attr.s(
    slots=True,
    str=False)
class BadToken(Exception):
    code_provider=attr.ib(
        validator=attr.validators.instance_of(tokens.CommandCodeProvider))

    def __attrs_post_init__(self):
        self.message = "Unrecognized token '%s' in command '%s'" % (
            str(self.code_provider),
            tokens.CommandCodeProvider(command=self.code_provider.command))

    def __str__(self):
        return self.message

def tokenize(command, lexicon):
    """
    tokenize the code in a command.

    First, we'll make a Lexicon with a Module that defines a couple of
    keywords.
    >>> module1 = modules.Module(name='module1')
    >>> module1.add_definition(
    ...   definition=modules.FullDefinition(
    ...     name='fred',
    ...     token_type=tokens.Verb))
    >>> module1.add_definition(
    ...   definition=modules.FullDefinition(
    ...     name='space',
    ...     pattern=' ',
    ...     token_type=tokens.Token))
    >>> lex1 = modules.Lexicon(modules=ordered_set.OrderedSet([module1]))

    Now we'll use the Lexicon to tokenize a Command.
    >>> command1 = tokens.Command(
    ...   code_provider=tokens.StringCodeProvider(
    ...     code="fred fred"))
    >>> pprint.pprint(tokenize(
    ...   command=command1,
    ...   lexicon=lex1))
    [Verb(code_provider=CommandCodeProvider(command=Command(code_provider=StringCodeProvider(code='fred fred', start=0, end=None)), start=0, end=4)),
     Token(code_provider=CommandCodeProvider(command=Command(code_provider=StringCodeProvider(code='fred fred', start=0, end=None)), start=4, end=5)),
     Verb(code_provider=CommandCodeProvider(command=Command(code_provider=StringCodeProvider(code='fred fred', start=0, end=None)), start=5, end=9))]

    If we send it a command with some unrecognized code, we'll get an
    exception.
    >>> command2 = tokens.Command(
    ...   code_provider=tokens.StringCodeProvider(
    ...     code="fred barney"))
    >>> pprint.pprint(tokenize(
    ...   command=command2,
    ...   lexicon=lex1))
    Traceback (most recent call last):
      ...
    BadToken: Unrecognized token 'barney' in command 'fred barney'

    If there are good tokens after the bad, the exception will only
    mention the bad parts.
    >>> command3 = tokens.Command(
    ...   code_provider=tokens.StringCodeProvider(
    ...     code="fred barney fred"))
    >>> tokenize(
    ...   command=command3,
    ...   lexicon=lex1)
    Traceback (most recent call last):
      ...
    BadToken: Unrecognized token 'barney' in command 'fred barney fred'
    """
    code = str(tokens.CommandCodeProvider(command=command))
    definitions = collections.OrderedDict(
        sorted(lexicon.items(), key=lambda pair: len(pair[1].pattern)))
    start = 0
    end = 0
    found_tokens = []
    match = None
    while code[start:]:
        # So long as there is code to tokenize, we tokenize code
        for keyword, definition in definitions.items():
            compiled = re.compile(
                pattern=definition.pattern,
                flags=re.IGNORECASE)
            match = compiled.match(
                string=code,
                pos=start)
            if match:
                if not end:
                    found_tokens.append(definition.token_type(
                        code_provider=tokens.CommandCodeProvider(
                            command=command,
                            start=match.start(),
                            end=match.end()),
                        definition=definition))
                    start = match.end()

                # We've found a token, break this loop
                break
        else:
            # there were no matches, move the provider one character
            # down and try again.  At this point, we're trying to get
            # the characters that are breaking things to create an error
            # message
            if not end:
                end = start
            start += 1
        if match and end:
            # we found a match after finding an error, break out of this
            # loop
            break
        match = None

    if end:
        # We're looking to create an error message, so raise
        # BadToken
        raise BadToken(
            code_provider=tokens.CommandCodeProvider(
                command=command,
                start=end,
                end=match.start() if match else match))

    return found_tokens

if __name__ == "__main__":
    import doctest
    print doctest.testmod()
