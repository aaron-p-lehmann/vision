class VisionException(Exception):
    def __init__(self, code=None, start=None, command=None, message=""):
        self.command=command
        super(VisionException, self).__init__(message)

class GarbageInputError(VisionException):
    pass

class UnmatchedEndScopeError(VisionException):
    def __init__(self, token):
        super(UnmatchedEndScopeError, self).__init__(
            code=token.command.code,
            start=0,
            command=token.command,
            message="Unmatched end of scope")

class UndeclaredContextError(VisionException):
    def __init__(self, command):
        super(UndeclaredContextError, self).__init__(
            command=command,
            code=command.code,
            start=0)
        self.commands = set((command,) + command.scopes)
        self.addCommand(command)

    def addCommand(self, command):
        self.commands.add(command)

    def __str__(self):
        out = super(UndeclaredContextError, self).__str__()
        cmds = sorted(self.commands, key=lambda command:command.lineno)
        ret = "\n".join(
            ['Context "%s" was not defined before use "%s" on line %d' % (
                self.command.context.code,
                self.command.code.strip(),
                self.command.lineno)] + 
            ['Maybe you made a typo?  The following variables were defined by %d' % self.command.lineno] +
            ['\t"%s" is "%s"' % (key, s.compile('vision')) for (key, s) in self.command.variables_in_scope.items()])
        return ret

class ElementError(VisionException):
    def __init__(self, element, message):
        self.element = element
        super(ElementError, self).__init__(
            command=element.command,
            message=message)

    def __str__(self):
        return self.message % self.element

class UnfoundElementError(ElementError):
    def __init__(self, element):
        super(UnfoundElementError, self).__init__(
            element=element,
            message='Unable to find element "%s"' % element.code)

class ElementNotReadyException(ElementError):
    def __init__(self, element):
        super(ElementNotReadyException, self).__init__(
            element=element,
            message='Element not ready "%s"')

class ParserException(VisionException):
    def __init__(self, parser, token, tokenstream, message=""):
        self.token=token
        self.tokenstream = tokenstream
        self.parser=parser
        message = message if message else "\n".join([
            self.token.command.code,
            " " * self.token.start + "^"])
        super(ParserException, self).__init__(
            command=parser.command,
            code=self.token.command.code,
            start=self.token.start,
            message=message)

class TooManyTokens(ParserException):
    def __init__(self, command, tokenstream):
        super(TooManyTokens, self).__init__(
            parser=command,
            token=command,
            tokenstream=tokenstream,
            message="There are unconsumed tokens")

class UnexpectedToken(ParserException):
    def __init__(self, parser, token, tokenstream):
        message = "\n".join([
            super(UnexpectedToken, self).__str__(),
            "Unexpected token type '%s'" % type(token).__name__]
            )
        super(UnexpectedToken, self).__init__(parser, token, tokenstream, message=message)

class UnmetTokenRequirements(ParserException):
    def __init__(self, parser, token, tokenstream, message=None):
        if not message:
            message="Token '%s' requires (%s)" % (
                type(parser).__name__,
                ", ".join(t.__name__ for t in parser.unmet_requirements))
        super(UnmetTokenRequirements, self).__init__(parser, token, tokenstream, message=message)

class WindowNotFoundError(VisionException):
    pass
