# Python Libraries
import attr
import platform
if platform.system() in ["Darwin"]:
    # Mac OS is dumb and uses netbsd's readline, so we need to import a
    # different lib
    import gnureadline as readline
else:
    import readline

# Vision Libraries
import parser

readline.parse_and_bind("tab: complete")
history_path = os.path.expanduser("~/.vision_history")
try:
    readline.read_history_file(history_path)
except IOError as ioe:
    if ioe.errno == 2:
        # The file wasn't there, make it and try again
        open(history_path, 'w+').write('')
        readline.read_history_file(history_path)

@attr.s
class PositionError(Exception):
    command = attr.ib()
    attempted_position = attr.ib()
    bound = attr.ib()

    def __init__(self, attempted_position, bound, command):
        self.attempted_position = attempted_position
        self.bound = bound
        self.message = "%s: Tried to scan line %d, range is from 1 to %d" % (self, self.attempted_position + 1, self.bound )
        self.command = command

@attr.s(slots=True)
class Scanner(object):
    """
    This takes the lines of a test, turns them into commands, and allows
    them to be iterated back and forth over them
    """

    name = attr.ib()
    lines = attr.ib(default=attr.Factory(list))
    position = attr.ib(default=0)
    command_type = attr.ib(default=attr.Factory(lambda: parser.Command))

    def __init__(self, name, lines, command_type=parser.Command):
        self.name = name
        self.lines = list(
            self.command_type(code=line, position=i, scanner=self) for (i, line) in enumerate(lines))
        self.command_type = command_type

    def __iter__(self):
        return self

    def next(self):
        try:
            return self.lines[self.advance()]
        except PositionError as pe:
            raise StopIteration

    def advance(self, lines=1):
        if len(self.lines) <= self.position + lines:
            raise PositionError(
                self.position + lines,
                len(self.lines) + 1)
        else:
            self.position += lines
        return self.position

    def rewind(self, lines=1):
        if 0 > self.position - lines:
            raise PositionError(
                self.position - lines,
                0)
        else:
            self.position -= lines
        return self.position

@attr.s(slots=True)
class InteractiveScanner(Scanner):
    """
    This scanner 
    """
    name = attr.ib(default="<interactive>")
    parser = attr.ib(default=None)

    def rewind(self, lines=1):
        """
        This doesn't support rewinding, silently do nothing.
        """
        return self.position

    def next(self):
        try:
            return self.lines[self.advance()]
        except PositionError as pe:
            self.lines.append(raw_input( "<%s>:%s|%s:  " % (
                self.parser.file_scanner.name,
                self.parser.file_scanner.position + 1 if self.parser.file_scanner.position + 1 < len(self.parser.file_scanner.lines) else "EOF",
                self.parser.scope)))
            return self.lines[self.advance()]

