import collections

class VisionOutput(object):
    """
    A class for outputting side effects from commands, such as status
    messages, debugging info, and other things that aren't important to
    the command's function.  This is NOT for output that is central to
    the command.

    For example:
        1) Timing information from a 'click' command is incindental to
        the command's function, and should be displayed here.
        2) Writing out a file that a user created for a FileLiteral
        inline is incidental to the command (which only cares about the
        data), and should be handled here.
        3) Writing out a png of a screenshot is incindental to the
        command (because it only cares about diffing the screenshot),
        and should be done here.
        4) Printing out the program listing because of a 'show test' is
        essencial to the command, and should be handled in
        interpretation, NOT HERE.
    """

    def __init__(self, interpreter, verbose=False):
        self.interpreter = interpreter
        self.outstream = []
        self.verbose = verbose
        self.output_functions = collections.defaultdict(lambda: lambda token, *args, **kwargs: True)

        # The default output command is to do nothing, successfully
        self.setup_outputs(self.output_functions)

    def get_command_tokens(self, outputcommand):
        return [outputcommand] + getattr(outputcommand, 'tokens', [])

    def output(self, outputcommand):
        for token in self.get_command_tokens(outputcommand):
            self.output_functions[getattr(token, 'type', None)](
                token=token,
                output=self)
        return True

    def setup_outputs(self, outputs):
        # Set up the functions for handling output
        outputs['selenium'] = self.output_command
        outputs['existence'] = self.output_command
        outputs['change focus'] = self.output_command
        outputs[None] = self.output_unparsed_command

    def print_command(self, command, code="", success=None):
        scope_level = sum(c.scopechange for c in command.parser.children)
        if getattr(command.verb, 'type', None) in ('require', 'test', 'validate'):
            scope_level = max(0, scope_level - 1)
        indent = "".join(["    "] * scope_level)
        self.print_command_text(
            text=indent + command.code,
            code=code,
            success=success)
        for warning in command.warnings:
            self.print_warning_section(
                warning=warning,
                indent=indent,
                success=success)

    def output_command(self, token, output):
        command = token
        code = "NOT EXECUTED"
        if command.executed:
            code = command.timing[command]['format'] % command.timing[command]['total']
        output.print_command(
            command=command,
            code=code,
            success=None if command.error is None else not bool(command.error))
        if command.error:
            output.print_comment('\n'.join((
                "Line failed:",
                "    %s" % command.code)))
            output.print_comment(command.trace)
            if command.executed:
                output.print_comment(str(command.error))
                if command.scanner.name not in ('<interactive>', '<subcommand>') and output.interpreter.interactivity_enabled:
                    output.print_subcomment("Get things into position that it will work, and type 'Run test' to resume.")
            else:
                output.print_comment(str(command.error))
        return True

    def output_unparsed_command(self, token, output):
        command = token
        code = "ERROR"
        self.print_command_text(
            text=output.interpreter.parser.scanner.lines[-1],
            code="FAILED TO PARSE",
            success=False)
        return True

    def print_command_text(self, text, code, success=None):
        print text + " - " + code

    def print_comment(self, comment, indent=""):
        print '    ' + indent + comment

    def print_subcomment(self, subcomment, indent=""):
        print '        ' + indent + subcomment

    def print_warning_section(self, warning, indent="", success=None):
        title = warning['title']
        subwarnings = warning['subwarnings']
        self.print_comment("Timing Information - " + title, indent=indent)
        for warning in subwarnings:
            self.print_subcomment(warning, indent=indent)

