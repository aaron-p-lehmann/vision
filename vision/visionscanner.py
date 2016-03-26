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

# Function for interpreting a Noun to a webelement
def _exact_value_filter(e, noun):
    if not noun.value:
        result = True
    else:
        elval = e.get_attribute('value') or e.text
        result = not noun.value or elval == str(noun.value)
    return result

def _starts_with_value_filter(e, noun):
    if not noun.value:
        result = True
    else:
        elval = e.get_attribute('value') or e.text
        result = elval.startswith(str(noun.value))
    return result

def _widget_value_filter(e, noun):
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

class SubjectPartStart(visionparser.InputPhrase):
    expected = [visionparser.Literal, visionparser.Ordinal, visionparser.Noun, visionparser.Context]
    children=(visionparser.Literal,visionparser.Ordinal)
    cant_have = {
        visionparser.Literal:2,
        visionparser.Ordinal:2,
        visionparser.Noun:2,
        visionparser.Context:2 }
    must_have = {
        visionparser.Noun:1,
        visionparser.Context:1}

    def parse(self, *args):
        return super(SubjectPartStart, self).parse(*args)

    def consume(self, token):
        # If token is a Noun, push it, and any children we've gotten,
        # back on to the stream and change it's phrase_start to the
        # start of this token.
        # The next time around, this'll fail the requirement of not
        # getting more than 1 Noun, and it will return parsing control
        # to the Command
        if isinstance(token, (visionparser.Noun, visionparser.Context)):
            del self.must_have[visionparser.Context]
            del self.must_have[visionparser.Noun]
            self.tokenstream = itertools.chain(
                [token] + self.children,
                self.tokenstream)
            token.phrase_start = self.start
            return self.tokenstream
        return super(SubjectPartStart, self).consume(token)

# Set up how to take the parse tree back to Vision, for error printing
class VisionTokenizer(object):
    """
    Iterable tokenizer

    This is created with an iterable file-like object and a dictionary
    of additional keywords used.

    When the tokenizer is iterated over, it reads through the filish
    object line by line, tokenizes the line and does some rudimentary
    preparsing, and gives the tokens one at a time.
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

    def __init__(self, filish, name, parser=None):
        self.parser = parser
        self.lines = filish.readlines()
        self.name = name
        self.position = 0

    def __iter__(self):
        return self

    def __bool__(self):
        return True
    # Python 2 compatibility
    __nonzero__ = __bool__

    def addline(self, newlines):
        newlines = [{'code': line, 'breakpoint': False} for line in newlines]
        self.lines.extend(newlines)

    def insertline(self, newlines):
        newlines = [{'code': line, 'breakpoint': False} for line in newlines]
        self.lines = self.lines[:self.position] + newlines + self.lines[self.position:]

    def format_line(self, line):
        mod_line = '    '.join(line.split('\t')).rstrip()
        return mod_line

    def next(self):
        token_list = []
        command = None
        line_iter = iter(self.lines[self.position:])
        line = ''
        while not line:
            # read until there's a non-blank line
            # or we run out of lines
            line = self.format_line(next(line_iter)['code'])
            command = self.commandtype(
                scanner=self,
                lineno=self.position + 1)
            command.parser = self.parser
            exception = None
            try:
                if line:
                    # We have a string, tokenize it
                    tokens = []
                    tokens = self.scanline(line, command)
                    token_list = [command] + tokens
            except StopIteration as si:
                exception = si
                raise
            except Exception as e:
                exception = e
                import traceback
                trace = traceback.format_exc()
                print trace
                e.command = getattr(e, 'command', command)
                if not e.command:
                    e.command = command
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

    def scanline(self, line, command):
        """
        Takes a line of Vision and returns a line of tokens
        """

        tokens, remainder = self.scanline_with_remainder(line)
        if remainder:
            # We have a remainder, this is an error
            start = len(line) - len(remainder)
            msg = "Parse failure at line %d, starting at character %d: " % (self.position, start + 1)
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
        return tokens

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
                    self.token_match_action(token, line[:start])
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
                    **arguments)
            start = end
            if to_emit:
                tokens.append(to_emit)

            remainder = line[start:]
        return (tokens,remainder)

    def token_match_action(self, token, scanned_line):
        # This is a hook for other scanners
        pass

    @property
    def done(self):
        return self.position == len(self.lines)

    @property
    def ignore(self):
        return self.sugar + self.seperators

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

    def get_regexps(self):
        regexps = getattr(
            super(VisionTokenizer, self),
            'get_regexps',
            lambda: {})()

        # This maps token types to the regexps that recognize them
        regexps.update({
            'attributenoun': """(?P<attributenoun>{([^}]|\\\\})+})""",
            'literal': """(?P<literal>"[^"]*"|'[^']*')""",
            'fileliteral': r"""(?P<fileliteral><.+>)""",
            'punctuation': r"(?P<punctuation>([^\w'<>]|_))",
            'whitespace': r"(?P<whitespace>[ ]+)",
            'ordinalnumber': "(?P<ordinalnumber>%s)" % visionparser.Ordinal.regexp,
        })

        return regexps

    @property
    def regexps(self):
        return self.get_regexps()

    def get_token_mapper(self):
        # This tells what to do when we get particular kinds of tokens
        # Indicates which of a sequence of matching Nouns to use in an
        # XPath
        tokens = {}
        tokens['ordinalnumber'] = [visionparser.Ordinal, {}]

        # Indicates the start of phrases
        tokens['the'] = [SubjectPartStart, {}]

        # Verbs for verifying things
        tokens['should_exist'] = [visionparser.Verb, {}]
        tokens['should_not_exist'] = [visionparser.Verb, {}]
        tokens['should_be_checked'] = [visionparser.Verb, {}]
        tokens['should_not_be_checked'] =[visionparser.Verb, {}]

        # things to do with the widgets
        tokens['capture'] = [visionparser.Verb, {}]
        tokens['clear'] = [visionparser.Verb, {'cant_have':(visionparser.Literal,)}]
        tokens['click'] = [visionparser.Verb, {'cant_have':(visionparser.Literal,)}]
        tokens['hover_over'] = [visionparser.Verb, {'cant_have':(visionparser.Literal,)}]
        tokens['close'] = [visionparser.Verb, {}]
        tokens['enter_file'] = [visionparser.Verb, {'must_have':(visionparser.FileLiteral,)}]
        tokens['should_contain'] = [visionparser.Verb, {'must_have':(visionparser.Literal,)}]
        tokens['should_contain_exactly'] = [visionparser.Verb, {'must_have':(visionparser.Literal,)}]
        tokens['should_not_contain'] = [visionparser.Verb, {'must_have':(visionparser.Literal,)}]
        tokens['navigate'] = [visionparser.Verb, {}]
        tokens['select'] = [visionparser.OrdinalVerb, {'cant_have':{visionparser.Literal:3, visionparser.Ordinal:2}, 'must_have':(visionparser.Literal,)}]
        tokens['switch'] = [visionparser.Verb, {'cant_have':(visionparser.Literal,)}]
        tokens['type'] = [visionparser.Verb, {'must_have':(visionparser.Literal,)}]
        tokens['nothing'] = [visionparser.Noop, {}]
        tokens['test'] = [visionparser.Verb, {}]
        tokens['accept'] = [visionparser.Verb, {'cant_have':(visionparser.Literal,)}]
        tokens['dismiss'] = [visionparser.Verb, {'cant_have':(visionparser.Literal,)}]
        tokens['authenticate'] = [visionparser.Verb, {'must_have':(visionparser.Literal,)}]
        tokens['wait'] = [visionparser.Verb, {'must_have':(visionparser.Literal,)}]
        tokens['require'] = [visionparser.Verb, {'must_have':(visionparser.Literal,)}]
        tokens['go_back'] = [visionparser.Verb, {'cant_have':(visionparser.Literal,)}]
        tokens['push'] = [visionparser.Verb, {'must_have':(visionparser.Literal,)}]
        tokens['replace'] = [visionparser.OrdinalVerb, {'must_have':{visionparser.Literal: 2}, 'cant_have':{visionparser.Literal: 3, visionparser.Ordinal: 2}}]

        # comments
        tokens['because'] = [visionparser.Comment, {'must_have': [visionparser.Literal]}]
        tokens['so_that'] = [visionparser.Comment, {'must_have': [visionparser.Literal]}]

        # within
        tokens['within'] = [visionparser.Wait, {'must_have': [visionparser.Literal]}]

        # skip
        tokens['is_skipped']  = [visionparser.Skip, {}]

        # Add variable to scope
        tokens['as'] = [visionparser.Variable, {'must_have':(visionparser.Literal,), 'cant_have':(visionparser.ValueObject,)}]

        # widgets on the page
        tokens['alert'] = [visionparser.Noun, {'use_parent_context_for_interpretation': False}]
        tokens['button'] = [visionparser.Noun, {'filters': [_exact_value_filter, _starts_with_value_filter]}]
        tokens['box'] = [visionparser.Noun, {}]
        tokens['next_button'] = [visionparser.Noun, {'cant_have': [visionparser.Literal]}]
        tokens['checkbox'] = [visionparser.Noun, {}]
        tokens['dropdown'] = [visionparser.Noun, {}]
        tokens['file_input'] = [visionparser.Noun, {}]
        tokens['image'] = [visionparser.Noun, {}]
        tokens['link'] = [visionparser.Noun, {}]
        tokens['radio_button'] = [visionparser.Noun, {}]
        tokens['text'] = [visionparser.Noun, {}]
        tokens['textarea'] = [visionparser.Noun, {}]
        tokens['textfield'] = [visionparser.Noun, {}]
        tokens['default'] = [visionparser.Noun, {'cant_have': [visionparser.Literal]}]
        tokens['frame'] = [visionparser.Noun, {}]
        tokens['window'] = [visionparser.Noun, {}]
        tokens['table_body'] = [visionparser.Noun, {}]
        tokens['table_header'] = [visionparser.Noun, {}]
        tokens['table_footer'] = [visionparser.Noun, {}]
        tokens['cell'] = [visionparser.Noun, {}]
        tokens['row'] = [visionparser.Noun, {'filters': [_widget_value_filter]}]
        tokens['section'] = [visionparser.Noun, {}]
        tokens['table'] = [visionparser.Noun, {}]
        tokens['context'] = [visionparser.Context, {}]
        tokens['literal'] = [visionparser.Literal, {}]
        tokens['attributenoun'] = [visionparser.AttributeNoun, {}]
        tokens['fileliteral'] = [visionparser.FileLiteral, {}]

        # Positons
        tokens['after'] = [visionparser.RelativePosition, {}]
        tokens['before'] = [visionparser.RelativePosition, {}]

        return tokens

    @property
    def token_mapper(self):
        return self.get_token_mapper()

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

# Set up custom grammar stuff
visionparser.Command.expected = visionparser.Command.expected + (SubjectPartStart,)

if __name__ == "__main__":
    program = sys.argv[-1]
    testy=VisionTokenizer(
        keywords=keywords,
#        filish=StringIO.StringIO("Click the '-' in the 'PENICILLINS' row"))
        filish=open(program))
    testy=visionparser.VisionParser(scanner=testy)
    for command in testy:
        print command.compile()
