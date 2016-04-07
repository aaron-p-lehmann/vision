# Python libraries
import sys
import re
import itertools
import copy
import types
import StringIO
import collections
import time

# MIE libraries
import visionparser
import visionexceptions

"""
Vision Scanner

This defines the keywords, seperators, scope indicators, etc of the
Vision language.  It takes a filish input which iterates over its input
by lines seperated by newline characters.

It is an iterator that produces a token each iteration.  A token is
defined as either a Command (which represents the start of a line), a
ScopeChange (in this case, four spaces '    '), a Literal (a string
of arbitrary characters surrounded by single quotes, with option escaped
single quotes inside), or a ParserObject (one of the keywords of the
language).
"""

def _exact_value_filter(e, noun):
    # verify teh widget has the right value
    if not noun.value:
        result = True
    else:
        elval = e.get_attribute('value') or e.text
        result = not noun.value or elval == str(noun.value)
    return result

def _starts_with_value_filter(e, noun):
    # Verify the widget starts with the right value
    if not noun.value:
        result = True
    else:
        elval = e.get_attribute('value') or e.text
        result = elval.startswith(str(noun.value))
    return result

def _widget_value_filter(e, noun):
    # Verify the row has a widget that starts with the right value
    if noun.value and not [el for el in e.find_elements_by_xpath("./descendant::td[starts-with(normalize-space(), %s)]" % noun.value.compile()) if el.is_displayed()]:
        # There are no cells in this row that start with the right
        # value, we'll need to check widgets
        for inp in e.find_elements_by_xpath("./descendant::td/descendant::input[not(@type='hidden')]"):
            if (inp.get_attribute('value') or inp.get_attribute('placeholder')).strip().startswith(str(noun.value)) and inp.is_displayed():
                # We've got an input that matches, return true
                return True
        for textarea in e.find_elements_by_xpath("./descendant::td/descendant::textarea"):
            if (textarea.get_attribute('value') or textarea.get_attribute('placeholder')).strip().startswith(str(noun.value)) and textarea.is_displayed():
                # We've got an input that matches, return true
                return True
        for button in e.find_elements_by_xpath("./descendant::td/descendant::button"):
            if button.get_attribute('value').strip().startswith(str(noun.value)) and button.is_displayed():
                # We've got an input that matches, return true
                return True
        from selenium.webdriver.support.ui import Select
        for select in e.find_elements_by_xpath("./descendant::td/descendant::select"):
            if select.is_displayed():
                select = Select(select)
                if select.first_selected_option.text.strip().startswith(str(noun.value)):
                    # We've got an input that matches, return true
                    return True
        # No matches, return false
        return False
    else:
        return True

def _center_filter(e, noun, horizontal=True, vertical=True):
    # Center the element
    noun.parser.interpreter.center_element(e, horizontal=horizontal, vertical=vertical)
    return True

class BasicTokenizer(object):
    """
    Splits a line into tokens.
    """

    # Tokens that are there to let the user write English, not Caveman
    sugar = (
        'to',
        'in',
        'for',
        'with',
        'new',
        'item',
        'from',
        'on',
        'into',
        'it',
        'and_get',
    )

    # These things seperate one token from another
    seperators = (
        'punctuation',
        'whitespace'
    )

    # These tokens are searched for before keywords
    before_keywords = ('literal',)

    # These tokens are searched for after keywords
    after_keywords = ()

    tokens = {
        # This tells what to do when we get particular kinds of tokens
        'ordinalnumber': [visionparser.Ordinal, {}],

        # Indicates the start of phrases
        'the': [visionparser.SubjectPartStart, {}],

        # Verbs for verifying things
        'should_exist': [visionparser.Verb, {'filters': [_center_filter]}],
        'should_not_exist': [visionparser.Verb, {}],
        'should_be_checked': [visionparser.Verb, {'filters': [_center_filter]}],
        'should_not_be_checked': [visionparser.Verb, {'filters': [_center_filter]}],

        # things to do with the widgets
        'capture': [visionparser.Verb, {}],
        'clear': [visionparser.Verb, {'cant_have':(visionparser.Literal,),'filters': [_center_filter]}],
        'click': [visionparser.Verb, {'cant_have':(visionparser.Literal,),'filters': [_center_filter]}],
        'hover_over': [visionparser.Verb, {'cant_have':(visionparser.Literal,),'filters': [_center_filter]}],
        'close': [visionparser.Verb, {'filters': [_center_filter]}],
        'enter_file': [visionparser.Verb, {'must_have':(visionparser.FileLiteral,),'filters': [_center_filter]}],
        'should_contain': [visionparser.Verb, {'must_have':(visionparser.Literal,),'filters': [_center_filter]}],
        'should_contain_exactly': [visionparser.Verb, {'must_have':(visionparser.Literal,),'filters': [_center_filter]}],
        'should_not_contain': [visionparser.Verb, {'must_have':(visionparser.Literal,),'filters': [_center_filter]}],
        'navigate': [visionparser.Verb, {}],
        'select': [visionparser.OrdinalVerb, {'cant_have':{visionparser.Literal:3, visionparser.Ordinal:2}, 'must_have':(visionparser.Literal,),'filters': [_center_filter]}],
        'switch': [visionparser.Verb, {'cant_have':(visionparser.Literal,)}],
        'type': [visionparser.Verb, {'must_have':(visionparser.Literal,),'filters': [_center_filter]}],
        'nothing': [visionparser.Noop, {}],
        'test': [visionparser.Verb, {'filters': [_center_filter]}],
        'accept': [visionparser.Verb, {'cant_have':(visionparser.Literal,)}],
        'dismiss': [visionparser.Verb, {'cant_have':(visionparser.Literal,)}],
        'authenticate': [visionparser.Verb, {'must_have':(visionparser.Literal,)}],
        'wait': [visionparser.Verb, {'must_have':(visionparser.Literal,)}],
        'require': [visionparser.Verb, {'must_have':(visionparser.Literal,)}],
        'go_back': [visionparser.Verb, {'cant_have':(visionparser.Literal,)}],
        'push': [visionparser.Verb, {'must_have':(visionparser.Literal,),'filters': [_center_filter]}],
        'replace': [visionparser.OrdinalVerb, {'must_have':{visionparser.Literal: 2}, 'cant_have':{visionparser.Literal: 3, visionparser.Ordinal: 2},'filters': [_center_filter]}],

        # template stuff
        'template_section': [visionparser.Verb, {'cant_have': (visionparser.Noun, visionparser.Ordinal, visionparser.TemplateInjector)}],
        'template': [visionparser.TemplateInjector, {'must_have': (visionparser.FileLiteral,), 'cant_have': {visionparser.Literal: 2}}],
        'data_section': [visionparser.Verb, {'cant_have': {visionparser.Noun:1, visionparser.Ordinal:1}, 'must_have': {visionparser.TemplateInjector:1, visionparser.Literal:1}}],
        'data': [visionparser.TemplateInjector, {'must_have': (visionparser.FileLiteral,), 'cant_have': {visionparser.Literal:3}}],

        # comments
        'because': [visionparser.Comment, {'must_have': [visionparser.Literal]}],
        'so_that': [visionparser.Comment, {'must_have': [visionparser.Literal]}],

        # within
        'within': [visionparser.Wait, {'must_have': [visionparser.Literal]}],

        # skip
        'is_skipped': [visionparser.Skip, {}],

        # Add variable to scope
        'as': [visionparser.Variable, {'must_have':(visionparser.Literal,), 'cant_have':(visionparser.ValueObject,)}],

        # widgets on the page
        'alert': [visionparser.Noun, {'use_parent_context_for_interpretation': False}],
        'button': [visionparser.Noun, {'filters': [_exact_value_filter, _starts_with_value_filter]}],
        'box': [visionparser.Noun, {}],
        'next_button': [visionparser.Noun, {'cant_have': [visionparser.Literal]}],
        'checkbox': [visionparser.Noun, {}],
        'dropdown': [visionparser.Noun, {}],
        'file_input': [visionparser.Noun, {}],
        'image': [visionparser.Noun, {}],
        'link': [visionparser.Noun, {}],
        'radio_button': [visionparser.Noun, {}],
        'text': [visionparser.Noun, {}],
        'textarea': [visionparser.Noun, {}],
        'textfield': [visionparser.Noun, {}],
        'default': [visionparser.Noun, {'cant_have': [visionparser.Literal]}],
        'frame': [visionparser.Noun, {}],
        'window': [visionparser.Noun, {}],
        'table_body': [visionparser.Noun, {}],
        'table_header': [visionparser.Noun, {}],
        'table_footer': [visionparser.Noun, {}],
        'cell': [visionparser.Noun, {}],
        'row': [visionparser.Noun, {'filters': [_widget_value_filter]}],
        'section': [visionparser.Noun, {}],
        'table': [visionparser.Noun, {}],
        'context': [visionparser.Context, {}],
        'literal': [visionparser.Literal, {}],
        'attributenoun': [visionparser.AttributeNoun, {}],
        'fileliteral': [visionparser.FileLiteral, {}],

        # Positons
        'after': [visionparser.RelativePosition, {}],
        'before': [visionparser.RelativePosition, {}],
    }

    REs = {
        'attributenoun': """(?P<attributenoun>{([^}]|\\\\})+})""",
        'literal': """(?P<literal>"[^"]*"|'[^']*')""",
        'fileliteral': r"""(?P<fileliteral><.+>)""",
        'punctuation': r"(?P<punctuation>([^\w'<>]|_))",
        'whitespace': r"(?P<whitespace>[ ]+)",
        'ordinalnumber': "(?P<ordinalnumber>%s)" % visionparser.Ordinal.regexp,
    }

    # These functions will be applied to the tokenmapper just before it
    # is returned
    token_transforms = ()

    def __init__(self, scanner=None, commandtype=None):
        self.scanner = scanner
        self.commandtype = commandtype

    def scanline(self, line, position):
        """
        Takes a line of Vision and returns a line of tokens
        """

        command = self.commandtype(
            scanner=self.scanner,
            lineno=position)
        try:
            tokens, remainder = self.scanline_with_remainder(line)
            if remainder:
                # We have a remainder, this is an error
                start = len(line) - len(remainder)
                msg = "Parse failure at line %d, starting at character %d: " % (command.lineno, start + 1)
                compiled_regex = re.compile(self.regexps['whitespace'], re.IGNORECASE)
                newpos = start + 1
                while newpos < len(line):
                    if compiled_regex.match(line[newpos:]):
                        break
                    newpos += 1
                msg += '"%s" was not recognized' % line[start:newpos]
                raise visionexceptions.GarbageInputError(
                    code=line,
                    command=command,
                    start=start,
                    message=msg)
            return [command] + tokens
        except Exception as e:
            e.command = command
            raise

    def scanline_with_remainder(self, line):
        """
        Takes a line of Vision and returns a line of tokens and a string
        that is the part that could not be tokenized
        """

        start=0
        tokens = []

        # We're going to save the lines after stripping leading
        # whitespace, we need to get the ammount of offset that'll be so
        # we can tell the tokens their proper start/end postions
        offset = len(line) - len(line.lstrip())
        compiled_regexes = [re.compile(regex, re.IGNORECASE) for regex in self.regexes]
        remainder = line
        while start < len(line):
            token_type = None
            token = None
            for regex in compiled_regexes:
                token_match = regex.match(line[start:])
                try:
                    match_dict = token_match.groupdict()
                    token_type = next(itertools.dropwhile(
                        lambda token_type: not match_dict.get(token_type, None),
                        self.token_order))
                    token = match_dict[token_type]

                    # We found a match, call the action and break this loop
                    self.scanner.token_match_action(token, line[:start])
                    break
                except visionexceptions.GarbageInputError, gie:
                    # if we got garbage here, reraise
                    raise
                except:
                    # There were no matches, eat this so we can try the
                    # next one
                    pass
            else:
                # We never found a match, this is the remainder
                break

            # We always update our postion in the line
            end = start + len(token)
            to_emit = None
            if token_type not in self.ignore:
                emitter, arguments = self.token_mapper[token_type]
                to_emit = emitter(
                    identifier=token,
                    start=start - offset,
                    scanner_args=arguments)
            start = end
            if to_emit:
                tokens.append(to_emit)

            remainder = line[start:]
        return (tokens,remainder)

    @property
    def regexes(self):
        if not hasattr(self, '_regexes'):
            self._regexes = []
            current = []
            for i, token in enumerate(self.token_order):
                regex = self.regexps.get(
                    token,
                    "(?P<%s>%s)" % (token, token.replace('_', ' ')))
                if i and not(100 % i):
                    # We need another regex, we can only group so many
                    # at a time
                    self._regexes.append('|'.join(current))
                    current = []
                current.append(regex)
            self._regexes.append('|'.join(current))
        return self._regexes

    @property
    def ignore(self):
        return self.sugar + self.seperators

    def get_regexps(self):
        return copy.deepcopy(BasicTokenizer.REs)

    @property
    def regexps(self):
        regexps = self.get_regexps()
        regexps.update(
            self.scanner.get_regexps() if self.scanner else {})
        return regexps

    def get_token_mapper(self):
        return copy.deepcopy(BasicTokenizer.tokens)

    @property
    def token_mapper(self):
        token_mapper = self.get_token_mapper()
        token_mapper.update(
            self.scanner.get_token_mapper() if self.scanner else {})
        for transform in self.token_transforms:
            transform(token_mapper)
        return token_mapper

    @property
    def token_order(self):
        """
        This is the order in which we need to look for tokens
        """

        if not hasattr(self, '_token_order'):
            _token_order = collections.OrderedDict()
            tokens_tuple = (
                self.before_keywords,
                tuple(self.regexps),
                tuple(self.token_mapper),
                self.after_keywords,
                self.sugar)
            for t in itertools.chain.from_iterable(
              [sorted(toks, key=len, reverse=True) for toks in tokens_tuple]):
                _token_order[t] = True
            self._token_order = tuple(_token_order)
        return self._token_order

class VisionScanner(object):
    """
    Iterable scanner

    This is basic class for Scanners.  All it needs is a name and a
    tokenizer, although giving it a parts is a good idea.
    """

    def __init__(self, name, tokenizer, parser=None):
        self.parser = parser
        self.name = name
        self.tokenizer = tokenizer
        self.lines = []
        self.position = 0
        tokenizer.scanner = self

    def __iter__(self):
        return self

    def __bool__(self):
        return True
    # Python 2 compatibility
    __nonzero__ = __bool__

    def addline(self, newlines):
        self.lines.extend(newlines)

    def format_line(self, line):
        mod_line = '    '.join(line.split('\t')).rstrip()
        return mod_line

    def get_regexps(self):
        # something for subclasses to extend
        return {}

    def get_token_mapper(self):
        # something for subclasses to extend
        return {}

    def scanline(self, line, position):
        """
        This method provides a hook that subscanners can override if
        they need to provide special handling for lines.
        """
        return self.tokenizer.scanline(line, position + 1)

    def next(self):
        token_list = []
        command = None
        line_iter = iter(self.lines[self.position:])
        line = ''
        exception = None
        while not line:
            # read until there's a non-blank line
            # or we run out of lines
            line = self.format_line(next(line_iter))
            exception = None
            try:
                if line:
                    # We have a string, tokenize it
                    token_list = self.scanline(line, self.position)
                    command = token_list[0]
            except StopIteration as si:
                exception = si
                raise
            except Exception as e:
                import traceback
                exception = e
                trace = traceback.format_exc()
                print trace
                e.command.trace = trace
                e.command.error = e
                raise
            finally:
                if not isinstance(exception, StopIteration):
                    # We'll put this in when we want to start keeping
                    # unparsed commands around
                    # self.parser.adopt(command)

                    self.advance()
        return token_list

    def advance(self, lines=1):
        self.position += lines

    def token_match_action(self, token, scanned_line):
        # This is a hook for other scanners
        pass

    @property
    def done(self):
        return self.position == len(self.lines)

class VisionFileScanner(VisionScanner):
    """
    This is a VisionScanner for the version of Vision that is loaded
    from a file.
    """

    # Set up the special regexps
    commandtype = visionparser.InterpreterCommand

    tokens = {
        'scope_change': [visionparser.ScopeChange, {}],
        'interactive': [visionparser.InterpreterVerb, {'cant_have':(visionparser.Literal,)}],
    }

    REs = {
        'scope_change': '(?P<scope_change>    )',
        'whitespace': '(?P<whitespace>[ \n])',
    }

    def __init__(self, filish, tokenizer, filename=None, subcommand=False, parser=None):
        file_name = filename or filish.name
        super(VisionFileScanner, self).__init__(
            name=file_name,
            parser=parser,
            tokenizer=tokenizer)
        self.addline(filish)

    def get_regexps(self):
        regexps = super(VisionFileScanner, self).get_regexps()
        regexps.update(copy.deepcopy(VisionFileScanner.REs))
        return regexps

    def get_token_mapper(self):
        tokens = super(VisionFileScanner, self).get_token_mapper()
        tokens.update(copy.deepcopy(VisionFileScanner.tokens))
        return tokens

    def scanline(self, line, position):
        """
        This handles indention scoping
        """
        tokens = super(VisionFileScanner, self).scanline(line, position)
        command, tokens = tokens[0], tokens[1:]

        # Handle all the indentation stuff
        # Count the number of ScopeChanges at the front
        scope_level = len(list(itertools.takewhile(
            lambda tok:isinstance(tok, visionparser.ScopeChange),
            tokens)))

        scopes = command.scopes
        if scope_level > len(scopes):
            # We've indented too far
            raise visionexceptions.GarbageInputError(
                code=line,
                start=0,
                message="Too many indents on line")

        # Filter out any remaining ScopeChanges
        tokens = [t for t in tokens if not isinstance(t, visionparser.ScopeChange)]
        if scope_level < len([scope for scope in scopes if scope.scanner is self]) and scope_level < len(scopes):
            # This line is dedented from the rest of the file it's from
            # and we haven't done and "end" command via interactive prompt
            # add the appropriate "end command"

            # Now we'll put a line ending the scope in the
            # test that matches the indentation level of the line
            scope = scopes[scope_level + (len(scopes) - len([scope for scope in scopes if scope.scanner is self]))]

            label, scope_type = str(scope.verb.value), scope.verb.type
            literal_marker = "'" if "'" not in label else '"'
            line = "End %s %s%s%s" % (scope_type, literal_marker, label, literal_marker)
            self.parser.subcommand_scanner.addline(StringIO.StringIO(line))
            self.parser.scanner = self.parser.subcommand_scanner

            # raise StopIteration so that the parser can pull from
            # the subcommand scanner
            raise StopIteration()

        return [command] + tokens

    def addline(self, newlines):
        super(VisionFileScanner, self).addline(
            {'breakpoint': False, 'code': line} for line in newlines)

    def insertline(self, newlines):
        newlines = [{'code': line, 'breakpoint': False} for line in newlines]
        self.lines = self.lines[:self.position] + newlines + self.lines[self.position:]

    def get_line(self):
        line = tokens = None
        while not tokens:
            # read lines until we get one that isn't empty
            # or just indents
            line = super(VisionFileScanner, self).get_line()['code']
            tokens = line.strip()

        return line

    def advance(self, lines=1, honor_breakpoints=True):
        for x in range(lines):
            self.lines[self.position]['breakpoint'] = False
            self.position += 1

    def rewind(self, lines=1):
        self.position -= lines

    def format_line(self, line):
        if self.lines[self.position]['breakpoint'] and self.parser.interpreter.interactivity_enabled:
            # We're moving to the next line and the interpreter supports interactive mode
            self.lines[self.position]['breakpoint'] = False
            raise StopIteration()
        return super(VisionFileScanner, self).format_line(line['code'])

    def toggle_breakpoint(self, number=None):
        number = (number - 1) if number else self.position
        self.lines[number]['breakpoint'] = not self.lines[number]['breakpoint']

    def toggle_token_breakpoint(self, token_type):
        found = False
        if "_".join(token_type.split()) in self.get_token_mapper():
            # Toggle the breakpoint for each line with
            # this kind of token, if there are any lines
            for (i, line) in itertools.dropwhile(lambda pair, start=self.position: pair[0] < start, enumerate(self.lines)):
                tokens, remainder = self.scanline_with_remainder(line['code'])
                if not remainder and [tok for tok in tokens if tok.type == token_type]:
                    self.toggle_breakpoint(i + 1)
                    found = True
            if not found:
                raise visionexceptions.VisionException(
                    message="'%s' does not contain token type '%s' after line %d" % (
                        self.name,
                        token_type,
                        self.position))
        else:
            raise visionexceptions.VisionException(
                message="'%s' is not an accepted token type in '%s'" % (
                    token_type,
                    self.name))

    def token_match_action(self, token, line):
        if not line.strip():
            # Have't seen anything but spaces/tabs
            if token == ' ':
                # We've got bad indentation, raise GarbageInputError
                raise visionexceptions.GarbageInputError(
                    code=line,
                    start=0,
                    message="Improper indentation")
        return True

    @property
    def scope_level(self):
        for command in reversed(self.parser.children):
            if command.usable and (command.scanner is self):
                return len(list(itertools.takewhile(
                    lambda tok:isinstance(tok, visionparser.ScopeChange),
                    self.scanline(self.lines[command.lineno - 1], command.lineno))))
        else:
            return 0

class InteractiveTokenizer(BasicTokenizer):
    """
    This is a tokenizer that knows how to handle tokens specific to
    the interactive prompt.
    """

    tokens = {
        'end_test': [visionparser.InterpreterVerb, {}],
        'end_require': [visionparser.InterpreterVerb, {}],
        'set': [visionparser.InterpreterVerb, {'must_have': (visionparser.Literal,)}],
        'load_test': [visionparser.InterpreterVerb, {}],
        'run_test': [visionparser.InterpreterVerb, {}],
        'save_test': [visionparser.InterpreterVerb, {'must_have': (visionparser.Literal,)}],
        'show_test': [visionparser.InterpreterVerb, {}],
        'show_input': [visionparser.InterpreterVerb, {}],
        'show_all_input': [visionparser.InterpreterVerb, {}],
        'skip': [visionparser.InterpreterVerb, {}],
        'next_command': [visionparser.InterpreterVerb, {'cant_have': (visionparser.Literal,)}],
        'break': [visionparser.InterpreterVerb, {'must_have': (visionparser.Literal,)}],
        'step_into_python': [visionparser.InterpreterVerb, {'cant_have': (visionparser.Literal,)}],
        'quit': [visionparser.InterpreterVerb, {}],
        'finish': [visionparser.InterpreterVerb, {'cant_have':[visionparser.Literal]}],
    }

    def get_token_mapper(self):
        tokens = super(InteractiveTokenizer, self).get_token_mapper()
        tokens.update(copy.deepcopy(InteractiveTokenizer.tokens))

        return tokens

class InteractiveVisionScanner(VisionScanner):
    """
    This is a VisionScanner for the version of Vision that is intended
    to be used interactively.
    """
    # We use InterpreterCommands
    commandtype = visionparser.InterpreterCommand

    def __init__(self, name, tokenizer, subcommand=False, parser=None):
        super(InteractiveVisionScanner, self).__init__(
            name=name,
            tokenizer=tokenizer,
            parser=parser)
        self.subcommand = subcommand

    def next(self):
        try:
            tokens = super(InteractiveVisionScanner, self).next()
            if self is self.parser.subcommand_scanner and self.parser.children:
                # This is a subcommand, set the origin scanner to be the
                # one from the previous command that has a Verb that is
                # not an InterpreterVerb or is End, if there is one
                try:
                    tokens[0].origin_scanner = next(
                        com.origin_scanner
                        for com in reversed(self.parser.children)
                        if com.verb and not isinstance(com.verb, visionparser.InterpreterVerb))
                except StopIteration as si:
                    # there wasn't a previous command.
                    pass
        except StopIteration, si:
            if not self.subcommand:
                try:
                    scopes = ['global']
                    try:
                        command = next(com for com in reversed(self.parser.children) if com.parsed and not com.error)
                        scopes.extend(str(com.verb.value) for com in command.scopes)
                        if command.scopechange > 0:
                            # The most recent command opened a scope,
                            # include it in the list
                            scopes.append(str(command.verb.value))
                        elif command.scopechange < 0:
                            # The most recent command closed a scope,
                            # cut the end of the scope list
                            scopes = scopes[:command.scopechange]
                    except StopIteration as si:
                        pass
                    inp = raw_input( "%s:%d:  " % (
                        scopes[-1],
                        self.parser.number_of_lines + 1))
                except Exception, e:
                    inp = 'quit'
                self.addline(StringIO.StringIO(inp))
                tokens = super(InteractiveVisionScanner, self).next()
            else:
                # If it's a subcommand, when we're done, we're done
                raise
        return tokens

