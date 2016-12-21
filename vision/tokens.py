"""
This implements the parser and the token types.
"""

import os
import attr
import errno
import abc
import collections

@attr.s(slots=True)
class CodeProvider(object):
    """
    CodeProviders abstract away different ways for tokens to access the
    Vision code they're based on.  This just provides a root class for
    type checking.
    """
    pass

@attr.s(slots=True)
class ParseUnit(object):
    """
    This represents anything the tokenizer recognizes.  It has the information
    necessary to find the raw code in its command's scanner, and methods to
    output a cleaned up version.

    First, make a ParseUnit.  We'll use a StringCodeProvider for testing
    purposes.
    >>> 
    """

    code_provider=attr.ib(
        validator=attr.validators.instance_of(CodeProvider),
        repr=True)
    definition=attr.ib(
        default=None,
        repr=False)
    tokens=attr.ib(
        default=attr.Factory(list),
        validator=attr.validators.instance_of(collections.MutableSequence),
        init=False,
        repr=False)
    children=attr.ib(
        default=attr.Factory(list),
        validator=attr.validators.instance_of(collections.MutableSequence),
        init=False,
        repr=False)

    def __str__(self):
        """
        Gets the proper string representaion of the token.
        """
        def get_proper_tokens(self):
            found_first_keyword = False
            for token in self.tokens:
                if not found_first_keyword and isinstance(token, ParseUnit):
                    # This is the first ParseUnit in the Command
                    found_first_keyword = True
                    clean = token.get_clean_code()
                    yield clean.capitalize() if clean[0] != clean[0].caplitalize() else clean
                else:
                    yield token.get_clean_code()
        return "".join(get_proper_tokens())

    @property
    def code(self):
        """
        Returns the segment of the code that resulted in this unit and
        its children.
        """
        return str(self.code_provider)

    @property
    def raw_string(self):
        """
        Gets the part of the code that is responsible for this token and
        all it's children.  This is the raw code, so extra Sugar and
        Seperators will be included here, when they would be removed
        from the normal string representation.  Use this for error
        messages.
        """
        return self.command.raw_string[self.tokens[0].code_provider.start:self.tokens[-1].code_provider.end]

    def token(self):
        """
        Returns the part of the line that is the token
        """
        return self.command.scanner[self.command.line][self.start:self.end]

@attr.s(slots=True)
class Noun(ParseUnit):
    """
    This represents a Noun, a thing for Vision to interact with such as
    a frame or a button.  This class is not materially different from
    many of the other ParseUnit classes, but it is used to type check while
    parsing.
    """
    pass

@attr.s(slots=True)
class AttributeNoun(Noun):
    """
    Represents a Noun that was described by HTML attribute or XPATH
    """

@attr.s(slots=True)
class Verb(ParseUnit):
    """
    This represents a Verb, a thing for Vision to do, such as clicking
    or typing.  This class is not materially different from many of the
    other ParseUnit classes, but it is used to type check while parsing.
    """
    pass

@attr.s(slots=True)
class CommandModifier(ParseUnit):
    """
    This represents a CommandModifier, which changes how Vision treats a
    Command, such as adding a comment, or skipping a line that is known
    not to work, but should.  This class is not materially different from
    many of the other ParseUnit classes, but it is used to type check while
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
class RelativePostion(ParseUnit):
    """
    This represents a RelativePostion, which indicates where a Noun is
    in relation to it's context in the DOM, such as before it or inside
    it.  This class is not materially different from many of the other
    ParseUnit classes, but it is used to type check while parsing.
    """
    pass

@attr.s(slots=True)
class StreamReorderer(ParseUnit):
    """
    This represents a StreamReorderer, which rearranges the token stream
    for parsing purposes.  The only example in basic Vision is 'the',
    which allows a Noun to come after its modifiers.  This class is not
    materially different from many of the other ParseUnit classes, but it is
    used to type check while parsing.
    """
    pass

@attr.s(slots=True)
class ScopeChange(ParseUnit):
    """
    This is a ScopeChange, which marks how many scopelevels a Command
    runs .  In basic Vision, 4 spaces before any other kinds of tokens
    are a scopechange.  This is not materially any different from other
    ParseUnits, it's just here for filtering.
    """
    pass

@attr.s(slots=True)
class Seperator(ParseUnit):
    """
    This is a Seperator, which comes between tokens.  In basic Vision,
    tabs and spaces that are not at the beginning of the line and most
    kinds of punctuation are Seperators.  This is not materially any
    different from other ParseUnits, it's just here for filtering.
    """
    pass

@attr.s(slots=True)
class Ordinal(ParseUnit):
    """
    This is an Ordinal (1st, 2nd, 3rd, etc).  This is not materially any
    different from other ParseUnits, it's just here for filtering.
    """
    pass

@attr.s(slots=True)
class Literal(ParseUnit):
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

@attr.s(slots=True)
class Command(ParseUnit):
    """
    This represents a line of Vision code.  It contains a reference to
    the scanner that scanned this line and the line in the scanner this
    command came from.  It also has any meta-information from processing
    its tokens.
    """

# CodeProviders
@attr.s(
    slots=True,
    these={
        'command': attr.ib(
            validator=attr.validators.instance_of(Command)),
        'code': attr.ib(init=False)})
class CommandCodeProvider(CodeProvider):
    """
    CodeProviders abstract away different ways for tokens to access the
    Vision code they're based on.
    This provides the line of code for a ParseUnit from a command.
    """

    @property
    def code(self):
        return str(self)

    def __str__(self):
        return str(command)

@attr.s(slots=True)
class StringCodeProvider(CodeProvider):
    """
    CodeProviders abstract away different ways for tokens to access the
    Vision code they're based on.
    This provides the line of code for a ParseUnit from a string.  It's
    intended for testing.
    """
    code = attr.ib(
        validator=attr.validators.instance_of(str),
        repr=True)
    start=attr.ib(
        default=0,
        validator=lambda self, name, value: self._validate_start(name, value),
        repr=True)
    end=attr.ib(
        default=-1,
        validator=lambda self, name, value: self._validate_end(name, value),
        repr=True)

    def _validate_end(self, name, value):
        if value < -1:
            raise IndexError(
                "ScannerCodeProvider.end must be 0 <= ScannerCodeProvider.end < %d or ScannerCodeProvider.end == -1: Got %d" % (
                    len(str(self.command)), value))
        return True

    def _validate_start(self, name, value):
        if value < 0:
            raise IndexError(
                "ScannerCodeProvider.start must be 0 <= ScannerCodeProvider.start < %d: Got %d" % (
                    len(str(self.command)), value))
        return True

    def __str__(self):
        return self.code[self.start:self.end]

