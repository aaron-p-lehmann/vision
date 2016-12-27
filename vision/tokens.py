"""
This implements the parser and the token types.
"""

import os
import attr
import errno
import abc
import collections
import pprint

@attr.s(
    slots=True,
    cmp=False)
class CodeProvider(object):
    """
    CodeProviders abstract away different ways for tokens to access the
    Vision code they're based on.  This just provides a root class for
    type checking and the attribute interface.
    """

    def __cmp__(self, other):
        if self.can_compare_to(other):
            return cmp(self.start, other.start)
        else:
            raise ValueError("These CodeProviders cannot be compared")

    def can_compare_to(self, other):
        """
        Check if 'self' can be meaningfully compared to 'other'
        """
        return False

@attr.s(slots=True)
class ParseUnit(object):
    """
    This represents anything the tokenizer recognizes.  It has the information
    necessary to find the raw code in its command's scanner, and methods to
    output a cleaned up version.

    First, make a Token.  We'll use a StringCodeProvider for testing
    purposes.
    >>> code = "Some code for the test"
    >>> ParseUnit(
    ...  code_provider=StringCodeProvider(
    ...    code=code))
    ParseUnit(code_provider=StringCodeProvider(code='Some code for the test', start=0, end=None))

    """

    code_provider=attr.ib(
        validator=attr.validators.instance_of(CodeProvider),
        repr=True,
        cmp=True)
    definition=attr.ib(
        default=None,
        repr=False,
        cmp=False)
    tokens=attr.ib(
        default=attr.Factory(list),
        validator=attr.validators.instance_of(collections.MutableSequence),
        init=False,
        repr=False,
        cmp=False)
    children=attr.ib(
        default=attr.Factory(list),
        validator=attr.validators.instance_of(collections.MutableSequence),
        init=False,
        repr=False,
        cmp=False)

    def __str__(self):
        """
        Gets the proper string representaion of the token using the
        function provided by the definition
        """
        return self.definition.prettified_code(self)
#        def get_proper_tokens(self):
#            found_first_keyword = False
#            for token in self.tokens:
#                if not found_first_keyword and isinstance(token, Token):
#                    # This is the first Token in the Command
#                    found_first_keyword = True
#                    clean = token.get_clean_code()
#                    yield clean.capitalize() if clean[0] != clean[0].caplitalize() else clean
#                else:
#                    yield token.get_clean_code()
#        return "".join(get_proper_tokens())

    def __cmp__(self, other):
        """
        Allows ParseUnits to be sorted with respect to one another.
        """
        if self.code_provider != other.code_provider:
            # If the code_providers are not the same, we can't compare
            # raise ValueError
            raise ValueError("The CodeProviders cannot be compared")
        return self.code_provider.start - other.code_provider.start

    @property
    def code(self):
        """
        Returns the segment of the code that resulted in this unit and
        its children.
        """
        return str(self.code_provider)
        #return self.definition.raw_code(self)

    @property
    def token(self):
        """
        Returns the part of the line that is the token
        """
        return self.definition.token(self)

    @property
    def tokens(self):
        """
        Flatten the parse tree into a list.  This is done recursively.
        """
        flat =[self]
        for token in self.children:
            flat.extend(token.tokens)
        return flat

@attr.s(slots=True)
class Command(ParseUnit):
    """
    This represents a line of Vision code.  It contains a reference to
    the scanner that scanned this line and the line in the scanner this
    command came from.  It also has any meta-information from processing
    its tokens.
    """
    pass

@attr.s(slots=True)
class Token(ParseUnit):
    """
    This is the base object of all Tokens.
    """
    pass

@attr.s(slots=True)
class Noun(Token):
    """
    This represents a Noun, a thing for Vision to interact with such as
    a frame or a button.  This class is not materially different from
    many of the other Token classes, but it is used to type check while
    parsing.
    """
    pass

@attr.s(slots=True)
class AttributeNoun(Noun):
    """
    Represents a Noun that was described by HTML attribute or XPATH
    """

@attr.s(slots=True)
class Verb(Token):
    """
    This represents a Verb, a thing for Vision to do, such as clicking
    or typing.  This class is not materially different from many of the
    other Token classes, but it is used to type check while parsing.
    """
    pass

@attr.s(slots=True)
class CommandModifier(Token):
    """
    This represents a CommandModifier, which changes how Vision treats a
    Command, such as adding a comment, or skipping a line that is known
    not to work, but should.  This class is not materially different from
    many of the other Token classes, but it is used to type check while
    parsing.
    """
    pass

@attr.s(slots=True)
class Within(CommandModifier):
    """
    This represents Within, which allows the user to set how long a
    particular command can run before it's an error.  This class is not
    materially different from many of the other CommandModifier classes,
    but it is used to type check while parsing.
    """
    pass

@attr.s(slots=True)
class Comment(CommandModifier):
    """
    This represents a Comment, which allows the user to provide
    clarifying information for a Command.  This class is not
    materially different from many of the other CommandModifier classes,
    but it is used to type check while parsing.
    """
    pass

@attr.s(slots=True)
class RecoverableError(CommandModifier):
    """
    This represents a RecoverableError, which allows the user to
    say that a particular command will always fail, but that it should
    not stop the test.  Since this command will always fail, it will not
    be executed, either.  This class is not materially different from
    many of the other CommandModifier classes, but it is used to type
    check while parsing.
    """
    pass

@attr.s(slots=True)
class RelativePostion(Token):
    """
    This represents a RelativePostion, which indicates where a Noun is
    in relation to it's context in the DOM, such as before it or inside
    it.  This class is not materially different from many of the other
    Token classes, but it is used to type check while parsing.
    """
    pass

@attr.s(slots=True)
class StreamReorderer(Token):
    """
    This represents a StreamReorderer, which rearranges the token stream
    for parsing purposes.  The only example in basic Vision is 'the',
    which allows a Noun to come after its modifiers.  This class is not
    materially different from many of the other Token classes, but it is
    used to type check while parsing.
    """
    pass

@attr.s(slots=True)
class ScopeChange(Token):
    """
    This is a ScopeChange, which marks how many scopelevels a Command
    runs .  In basic Vision, 4 spaces before any other kinds of tokens
    are a scopechange.  This is not materially any different from other
    Tokens, it's just here for filtering.
    """
    pass

@attr.s(slots=True)
class Seperator(Token):
    """
    This is a Seperator, which comes between tokens.  In basic Vision,
    tabs and spaces that are not at the beginning of the line and most
    kinds of punctuation are Seperators.  This is not materially any
    different from other Tokens, it's just here for filtering.
    """
    pass

@attr.s(slots=True)
class Ordinal(Token):
    """
    This is an Ordinal (1st, 2nd, 3rd, etc).  This is not materially any
    different from other Tokens, it's just here for filtering.
    """
    pass

@attr.s(slots=True)
class Literal(Token):
    """
    This is a Literal.
    """
    def __str__(self):
        return self.code[1:-1]

@attr.s(slots=True)
class FileLiteral(Literal):
    """
    A FileLiteral is a literal that is gotten by opening the file named by the identifier string.
    """

    base_path = attr.ib(
        default=os.getcwd())

    def __str__(self):
        with open(self.path) as input_file:
            # We found the file we're looking for
            return input_file.read()

    @property
    def path(self):
        return os.path.abspath(
            os.path.join(self.base_path, super(FileLiteral, self).__str__()))

@attr.s(slots=True)
class InteractiveFileLiteral(FileLiteral):
    """
    This represents a FileLiteral in interactive Vision.  It allows the
    user to enter the file line by line if it does not already exist.

    TODO: When I figure out where to put the different modules, this
    should be defined with the module for Interactive Vision
    """

    def __str__(self):
        try:
            return super(InteractiveFileLiteral, self).__str__()
        except IOError as ioe:
            if ioe.errno == errno.ENOENT:
                # The file does not exist, find out if we should make a new
                # one
                answer = None
                while not answer or answer[0] not in ["A", "C"]:
                    answer = raw_input(
                        "The file <%s> does not exist.  Would you like to (C)reate it, or (A)ccept the error and go to a prompt?").upper()
                if answer[0] == "C":
                    # Create the file
                    output = self.get_input("<END OF %s>" % self.code[1:-1])
                    with open(self.path, 'w') as output_file:
                        output_file.write()
                    return output
                else:
                    raise

    def get_input(self, end):
        lines = []
        while not lines or lines[-1] != end:
            lines.append(
                raw_input("Type the file, line by line.  Type %s by itself on the line to finish typing:  " % end).rstrip("\n"))
        return "\n".join(lines[:-1])

    code_provider=attr.ib(
        validator=attr.validators.instance_of(CodeProvider),
        repr=True,
        cmp=True)
    definition=attr.ib(
        default=None,
        repr=False,
        cmp=False)
    tokens=attr.ib(
        default=attr.Factory(list),
        validator=attr.validators.instance_of(collections.MutableSequence),
        init=False,
        repr=False,
        cmp=False)
    children=attr.ib(
        default=attr.Factory(list),
        validator=attr.validators.instance_of(collections.MutableSequence),
        init=False,
        repr=False,
        cmp=False)

@attr.s(
    slots=True,
    cmp=False)
class StringCodeProvider(CodeProvider):
    """
    StringCodeProviders provides the line of code for a Token from a string.  It's
    intended for testing.

    Create a StringCodeProvider with some test code and default 'start'
    and 'end'.  Note that 'end' defaults to None, which means to go to
    the end of the code.
    >>> code1 = "Some code for the test"
    >>> scp1 = StringCodeProvider(code=code1)
    >>> scp1
    StringCodeProvider(code='Some code for the test', start=0, end=None)

    StringCodeProvider implement the __str__ method to return their
    'code'.
    >>> str(scp1)
    'Some code for the test'

    'start' and 'end' can be provided, then the provider will only
    provide text between those indices.
    >>> str(StringCodeProvider(
    ...   code=code1,
    ...   start=5,
    ...   end=9))
    'code'

    StringCodeProviders can be compared if they are based on the
    same text.
    >>> scp5 = StringCodeProvider(code=code1,start=5)
    >>> scp8 = StringCodeProvider(code=code1,start=8)
    >>> scp5.can_compare_to(scp8)
    True

    If they can be compared, they can be sorted
    >>> pprint.pprint([scp8, scp5])
    [StringCodeProvider(code='Some code for the test', start=8, end=None),
     StringCodeProvider(code='Some code for the test', start=5, end=None)]
    >>> pprint.pprint(list(sorted([scp8, scp5])))
    [StringCodeProvider(code='Some code for the test', start=5, end=None),
     StringCodeProvider(code='Some code for the test', start=8, end=None)]

    They cannot be compared if they are based on different strings, though.
    >>> code2 = "Test Text 2"
    >>> scp2 = StringCodeProvider(code=code2)
    >>> scp1.can_compare_to(scp2)
    False
    >>> scp2.can_compare_to(scp1)
    False

    If they cannot be compared, they raise a ValueError.
    >>> pprint.pprint(list(sorted([scp1, scp2])))
    Traceback (most recent call last):
      ...
    ValueError: These CodeProviders cannot be compared
    """
    code = attr.ib(
        validator=attr.validators.instance_of(str))
    start = attr.ib(
        default=0,
        validator=lambda self, name, value:self.code[value])
    end = attr.ib(
        default=None,
        validator=attr.validators.optional(lambda self, name, value:self.code[self.start:value]))

    def __str__(self):
        return str(self.code)[self.start:self.end] if self.end is not None else str(self.code)[self.start:]

    def can_compare_to(self, other):
        """
        Check if 'self' can be meaningfully compared to 'other'
        """
        return self.code is other.code

@attr.s(
    slots=True,
    cmp=False)
class CommandCodeProvider(CodeProvider):
    """
    CodeProviders abstract away different ways for tokens to access the
    Vision code they're based on.
    This provides the line of code for a Token from a Command.

    Create CommandCodeProvider that uses a StringCodeProvider as its
    code_provider.
    >>> code1 = "Some code for the test"
    >>> CommandCodeProvider(
    ...   command=Command(
    ...     code_provider=StringCodeProvider(code=code1)))
    CommandCodeProvider(command=Command(code_provider=StringCodeProvider(code='Some code for the test', start=0, end=None)), start=0, end=None)

    Like other CodeProviders, CommandCodeProviders implement __str__ to
    return their code.
    >>> scp1 = StringCodeProvider(code=code1)
    >>> ccp1 = CommandCodeProvider(
    ...   command=Command(
    ...     code_provider=scp1))
    >>> str(ccp1)
    'Some code for the test'

    CommandCodeProviders can be compared if the CodeProviders of the
    CodeProviders of the underlying commands can be compared.
    >>> scp2 = StringCodeProvider(code=code1)
    >>> scp1.can_compare_to(scp2)
    True
    >>> ccp2 = CommandCodeProvider(
    ...   command=Command(
    ...     code_provider=scp2))
    >>> ccp1.can_compare_to(ccp2)
    True

    If the underlying CodeProviders can't be compared, neither can the
    CommandCodeProviders.
    >>> code2 = "Some other code for the test"
    >>> scp3 = StringCodeProvider(code=code2)
    >>> scp1.can_compare_to(scp3)
    False
    >>> scp3.can_compare_to(scp1)
    False
    >>> ccp3 = CommandCodeProvider(
    ...   command=Command(
    ...     code_provider=scp3))
    >>> ccp1.can_compare_to(ccp3)
    False
    >>> ccp3.can_compare_to(ccp1)
    False
    """
    command = attr.ib(validator=attr.validators.instance_of(Command))
    start = attr.ib(
        default=0,
        validator=lambda self, name, value:self.code[value])
    end = attr.ib(
        default=None,
        validator=attr.validators.optional(lambda self, name, value:self.code[self.start:value]))

    @property
    def code(self):
        return str(self)

    def __str__(self):
        return str(self.command.code)

    def can_compare_to(self, other):
        """
        Check if 'self' can be meaningfully compared to 'other'
        """
        return self.command.code_provider.can_compare_to(other.command.code_provider)

if __name__ == "__main__":
    import doctest
    doctest.testmod()
