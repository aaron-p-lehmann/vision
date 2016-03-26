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
        essenscial to the command, and should be handled in
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
        pass

    def print_command(self, command, code="", success=None):
        print command + " - " + code

    def print_comment(self, comment):
        print comment

    def print_subcomment(self, subcomment):
        print '\t' + subcomment
