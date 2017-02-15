# Python libraries
from PIL import ImageChops, ImageOps, ImageColor, Image
import StringIO
import base64
import collections
import functools
import itertools
import sys
import os
import os.path
import ntpath
import time
import operator
import platform

# Selenium libraries
import selenium
from selenium import webdriver
from selenium.common.exceptions import (
    WebDriverException,
    StaleElementReferenceException,
    NoSuchWindowException,
    NoAlertPresentException,
    UnexpectedAlertPresentException )
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities

# Vision modules
import visionscanner
import visionparser
import visionexceptions
import visionoutput

def output_file_literal(token, output):
    literal = token
    if literal.created:
        # If we need to create a file, do it
        with open(literal.abs_path, 'wb') as output_file:
            try:
                output_file.write(output)
            except Exception as e:
                print "Failed to write %s: %s" % (literal.abs_path, e)
    return True

def case_insensitive(leftside):
    return "translate(%s, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz')" % leftside

# Functions for compiling Nouns
# Default function for compiling a Noun to Python
def _compile_noun_to_xpath(self, tag='*', compare_type='label', additional_predicate="", is_toggle=False, exact_match=False, nots=(), base_axis=None, trusteds=()):
    xpaths = getattr(self, 'xpaths', [])
    trusteds = list(trusteds) + getattr(self, 'trusteds', [])
    predicate = ""
    if not xpaths:
        if self.value:
            val_comp = self.value.compile()
            exact = "normalize-space(.)=%s" % val_comp
            starts_with = "(starts-with(normalize-space(.), %s) and not(%s))" % (val_comp, exact)
            text_matcher = exact if exact_match else starts_with
            precise_text_matcher = "(%s and not(./%s::*[%s]))" % (text_matcher,(base_axis or "descendant"), text_matcher)
            if compare_type == 'label':
                labelled_by_id = "./%s::%s[@id=//label[%s]/@for]%s" % (
                    self.axis,
                    tag,
                    text_matcher,
                    additional_predicate)
                labelled_by_containment = "./%s::%s[ancestor::label[%s]]%s" % (
                    self.axis,
                    tag,
                    text_matcher,
                    additional_predicate)
                same_block_node = "./%s::node()[%s]/%s::node()/%s::%s" % (
                    self.axis,
                    precise_text_matcher,
                    "preceding-sibling" if is_toggle else "following-sibling",
                    base_axis or "descendant-or-self",
                    tag)

                same_block = "./%s::*[%s]/%s::*/%s::%s" % (
                    self.axis,
                    precise_text_matcher,
                    "preceding-sibling" if is_toggle else "following-sibling",
                    base_axis or "descendant-or-self",
                    tag)
                previous_cell = "./%s::td[%s]/following-sibling::td[1]/%s::%s%s" % (
                    self.axis,
                    text_matcher,
                    base_axis or "descendant",
                    tag,
                    additional_predicate)
                previous_row = "./%s::tr[%s]/following-sibling::tr[1]/%s::%s%s" % (
                    self.axis,
                    text_matcher,
                    base_axis or "descendant",
                    tag,
                    additional_predicate)
                legend = "./%s::legend[%s]/ancestor::table[1]/%s::%s%s" % (
                    self.axis,
                    text_matcher,
                    base_axis or "descendant",
                    tag,
                    additional_predicate)
                #previous_cell = "normalize-space(ancestor::td[1]/preceding-sibling::td[1])=%s" % val_comp
                #previous_row = "normalize-space(ancestor::tr[1]/preceding-sibling::tr[count(td)=1][1])=%s" % val_comp
                #legend = "normalize-space((ancestor::table/descendant::legend)[1]=%s" % val_comp
                #predicate = "[ %s ]" % ' or '.join((previous_cell, previous_row, legend))
                trusteds += [labelled_by_id, labelled_by_containment]
                xpaths += [same_block_node, same_block]
                if not is_toggle:
                    xpaths += [previous_cell, previous_row, legend]
            elif compare_type=='value':
                # We'll be interpreting using the value of the element,
                # so don't use it here
                xpaths += ["./%s::%s%s" % (self.axis, tag, additional_predicate)]
            elif compare_type=='link':
                xpaths += [
                    "./%s::%s[%s]%s" % (self.axis, tag, text_matcher, additional_predicate),
                    "./%s::%s[%s]%s" % (self.axis, tag, text_matcher.replace(".", "@title"), additional_predicate)
                ]
            elif compare_type=='string':
                xpaths += [
                    "./%s::%s[%s]%s" % (self.axis, tag, precise_text_matcher, additional_predicate),
                    "./%s::%s[%s]%s" % (self.axis, tag, precise_text_matcher.replace(".", "@title"), additional_predicate)
                ]
        if not xpaths:
            xpaths += ["./%s::%s%s" % (self.axis, tag, additional_predicate)]
    if self.parser.interpreter.verbose:
        print xpaths
    return (tuple(trusteds), tuple(xpaths), tuple(nots))

def compile_simple_to_xpath(self, tag, nots=(), base_axis="descendant", trusteds=()):
    patterns = ('./%s::%s' % (base_axis, tag),)
    return (tuple(trusteds), tuple(patterns), tuple(nots))

def compile_noun_to_xpath(self, *args, **kwargs):
    return map(operator.add,
        _compile_noun_to_xpath(self, exact_match=True, *args, **kwargs),
        _compile_noun_to_xpath(self, exact_match=False, *args, **kwargs))

def compile_button_to_xpath(self, nots=(), base_axis=None, trusteds=()):
    submits_trusteds, submits, submits_nots = compile_noun_to_xpath(
        self,
        tag="input[%s='submit']" % case_insensitive('@type'),
        compare_type='value',
        nots=nots,
        base_axis=base_axis,
        trusteds=trusteds)
    inp_trusteds, inp_buttons, inp_buttons_nots = compile_noun_to_xpath(
        self,
        tag="input[%s='button']" % case_insensitive('@type'),
        compare_type='value',
        nots=nots,
        base_axis=base_axis,
        trusteds=trusteds)
    buttons_trusteds, buttons, buttons_nots = compile_noun_to_xpath(
        self,
        tag='button',
        compare_type='string',
        nots=nots,
        base_axis=base_axis,
        trusteds=trusteds)
    trusteds_roles, roles, role_nots = compile_noun_to_xpath(
        self,
        tag="div[@role='button']",
        compare_type='string',
        nots=nots,
        base_axis=base_axis,
        trusteds=trusteds)
    buttons_trusteds, buttons_val, buttons_val_nots = compile_noun_to_xpath(
        self,
        tag='button',
        compare_type='value',
        nots=nots,
        base_axis=base_axis,
        trusteds=trusteds)
    od = collections.OrderedDict()
    for inp in itertools.chain(*(zip(submits_trusteds, inp_trusteds, buttons_trusteds, trusteds_roles, buttons_trusteds))):
        od[inp] = True
    trusteds = od.keys()
    od = collections.OrderedDict()
    for inp in itertools.chain(*(zip(submits, inp_buttons, buttons, roles, buttons_val))):
        od[inp] = True
    patterns = od.keys()
    od_nots = collections.OrderedDict()
    for inp in itertools.chain(*(zip(submits_nots, inp_buttons_nots, buttons_nots, role_nots, buttons_val_nots))):
        od_nots[inp] = True
    nots = od_nots.keys()
    return (tuple(trusteds), tuple(patterns), tuple(nots))

def compile_icon_button_to_xpath(self, type_attr=None, compare_type='title', nots=(), base_axis=None, trusteds=()):
    type_attr = type_attr or self.value
    predicate = ""
    if type_attr:
        if not isinstance(type_attr, tuple):
            type_attr = (type_attr,)
        predicate = "[ %s ]" % ' or '.join(
            ["@%s='%s'" % (compare_type, t) for t in type_attr])
    node_xpaths, node_nots, node_trusteds = compile_noun_to_xpath(
        self,
        tag='node()',
        additional_predicate=predicate,
        compare_type=compare_type,
        nots=nots,
        trusteds=trusteds,
        base_axis=base_axis)
    return node_xpaths, node_nots, node_trusteds

def compile_textfield_to_xpath(self, nots=(), base_axis=None, trusteds=()):
    trusteds_texts, texts, nots = compile_noun_to_xpath(
        self,
        tag="input[(not(@type) or %s='text' or %s='textarea')]" % (
            case_insensitive('@type'),
            case_insensitive('@type')),
        nots=nots,
        base_axis=base_axis,
        trusteds=trusteds)
    trusteds_passwords, passwords, nots = compile_noun_to_xpath(
        self,
        tag="input[%s='password']" % case_insensitive('@type'),
        nots=nots,
        base_axis=base_axis,
        trusteds=trusteds)
    trusteds_emails, emails, nots = compile_noun_to_xpath(
        self,
        tag="input[%s='email']" % case_insensitive('@type'),
        nots=nots,
        base_axis=base_axis,
        trusteds=trusteds)
    trusteds_tels, tels, nots = compile_noun_to_xpath(
        self,
        tag="input[%s='tel']" % case_insensitive('@type'),
        nots=nots,
        base_axis=base_axis,
        trusteds=trusteds)
    trusteds_files, files, nots = compile_noun_to_xpath(
        self,
        tag="input[%s='file']" % case_insensitive('@type'),
        nots=nots,
        base_axis=base_axis,
        trusteds=trusteds)
    od = collections.OrderedDict()
    for inp in itertools.chain(*(zip(trusteds_texts, trusteds_files, trusteds_passwords, trusteds_emails, trusteds_tels))):
        od[inp] = True
    trusteds = od.keys()
    od = collections.OrderedDict()
    for inp in itertools.chain(*(zip(texts, files, passwords, emails, tels))):
        od[inp] = True
    patterns = od.keys()
    return trusteds, patterns, nots

def compile_image_to_xpath(self, type_attr=None, compare_type='alt', nots=(), base_axis=None, trusteds=()):
    type_attr = type_attr or self.value
    predicate = ""
    if type_attr:
        if not isinstance(type_attr, tuple):
            type_attr = (type_attr,)
        predicate = "[ %s ]" % ' or '.join(
            ["@alt='%s'" % t for t in type_attr])
    return compile_noun_to_xpath(
        self,
        tag='img',
        additional_predicate=predicate,
        compare_type=compare_type,
        nots=nots,
        base_axis=base_axis,
        trusteds=trusteds)

def compile_input_to_xpath(self, type_attr=None, compare_type='label', nots=(), base_axis=None, trusteds=()):
    type_attr = type_attr or self.type
    predicate = ""
    if type_attr:
        if not isinstance(type_attr, tuple):
            type_attr = (type_attr,)
        predicate = "[ %s ]" % ' or '.join(
            ["@type='%s'" % t for t in type_attr])
    return compile_noun_to_xpath(
        self,
        tag='input',
        additional_predicate=predicate,
        compare_type=compare_type,
        nots=nots,
        base_axis=base_axis,
        trusteds=trusteds)

def compile_row_to_xpath(self, nots=(), base_axis=None, trusteds=()):
    # The predicates are designed to prevent us from selecting a row
    # that contains a child row that would match this that also has
    # sibling trs.  This should cut down on the mess our ugly nested
    # tables makes.
    base_pattern = "./%s::tr" % (base_axis or self.axis)
    trusteds, roles, nots = compile_noun_to_xpath(
        self,
        tag="div[@role='row']",
        compare_type='string',
        nots=nots,
        trusteds=trusteds)
    xpaths = (base_pattern,) + roles
    if self.value:
        val_comp = self.value.compile()
        # This next looks for the text in text elements or in
        # non-hidden inputs.  I wish it could look in selects, but xpath
        # isn't smart enough to know which elements are selected
        find_text_in_cell = "descendant::td[starts-with(normalize-space(), %s)]" % val_comp
        find_inputs_in_cell = "descendant::input[not(%s='hidden')] or descendant::textarea or descendant::select or descendant::button" % case_insensitive('@type')
        text_row_pattern = "%s[ %s and not(%s[ %s ]) ]" % (
            base_pattern,
            find_text_in_cell,
            base_pattern,
            find_text_in_cell)
        input_row_pattern = "%s[%s and not(%s)]" % (
            base_pattern,
            find_inputs_in_cell,
            find_text_in_cell)
        xpaths = (text_row_pattern,) + roles + (input_row_pattern,)
    return trusteds, xpaths, nots

def compile_box_to_xpath(self, nots=(), base_axis=None, trusteds=()):
    predicate = "[not(%s::fieldset)]" % (base_axis or "descendant")
    if self.value:
        val_comp = self.value.compile()
        predicate = "[ contains(normalize-space(%s::legend), %s) and not( %s::fieldset[contains(normalize-space(%s::fieldset/legend), %s)]) ]" % (
            base_axis or "descendant",
            val_comp,
            base_axis or "descendant",
            base_axis or "descendant",
            val_comp)
    xpath = "./%s::fieldset%s" % (self.axis, predicate)
    if self.parser.interpreter.verbose:
        print xpath
    return trusteds, (xpath,), nots

def compile_table_to_xpath(self, nots=(), base_axis=None, trusteds=()):
    predicate = ""
    if self.value:
        val_comp = self.value.compile()
        predicate = "[ contains(normalize-space(ancestor::fieldset/legend), %s) ]" % val_comp
    xpath = "./%s::table%s" % (self.axis, predicate)
    if self.parser.interpreter.verbose:
        print xpath
    return trusteds, (xpath,), nots

def interpret_selenium_command(self, interpreter, ele=None):
    subj = self.subject
    wait_time = self.wait

    if self.uses_elements:
        noun = self.subject or self.context
        if noun:
            noun_time = time.time()
            try:
                ele = interpreter.locate(
                    function=functools.partial(
                        noun.interpret,
                        interpreter=interpreter),
                    command=self,
                    maximum_wait=wait_time)
            finally:
                total = time.time() - noun_time
                noun_timing = self.timing.get(
                    noun, {
                        'total': 0,
                        'times_found': 0
                    })
                noun_timing['total'] += total
                if ele:
                    noun_timing['times_found'] += 1
        else:
            ele = interpreter.webdriver.find_element_by_xpath('/html')
        if not ele:
            return False

    # Find the module our webdriver instance is from.  Do it this way
    # because by this point we really don't know what kind of webdriver
    # we have (local or remote, if local, what browser)
    webdriver_module = sys.modules[sys.modules[type(interpreter.webdriver).__module__].__package__]

    # if we aren't dealing with a file input, we don't want to upload
    # files.  Selenium folks made the bizaar design descision to defalut
    # the other way
    start = time.time()
    try:
        file_detector = webdriver_module.file_detector.LocalFileDetector if (subj and subj.type == 'file input') else webdriver_module.file_detector.UselessFileDetector
    except AttributeError as ae:
        # We're using a webdriver module that doesn't do file detection,
        # so we don't need to set up the context
        ret = self.verb.interpret(interpreter=interpreter, ele=ele)
    else:
        # We do filedection, set up the context
        with interpreter.webdriver.file_detector_context(file_detector):
            ret = self.verb.interpret(interpreter=interpreter, ele=ele)
    finally:
        total = time.time() - start
        verb_timing = self.timing.get(self.verb, {
            'total': 0
        })
        verb_timing['total'] += total
        self.timing[self.verb] = verb_timing

    return ret

def interpret_existence_check(self, interpreter, ele=None, expected=True):
    # Existence checks look for the element as the verb
    subj = self.command.subject
    wait_time = self.command.wait
    try:
        ele = interpreter.locate(
            function=functools.partial(
                subj.interpret,
                interpreter=interpreter),
            command=self.command,
            maximum_wait=wait_time)
    except visionexceptions.UnfoundElementError as uee:
        if not expected:
            # We didn't expect to find it, and we didn't, return True
            return True
        else:
            raise
    try:
        if ele:
            ele.tag_name
            return expected
        else:
            return not expected
    except StaleElementReferenceException as sere:
        return not expected

def interpret_existence_check_in_alert(self, interpreter, ele=None, expected=True):
    if ele.text.startswith(str(self.value)) or not expected:
        return True
    else:
        raise Exception( "Condition NOT met" )

def interpret_checked_check(self, interpreter, ele=None, expected=True):
    return interpreter.webdriver.execute_script(
        "return (arguments[0] && arguments[1].checked) || (!arguments[0] && !arguments[1].checked) ;",
        expected,
        ele)

def locator_func(noun, func, finds, nots, filters=None, ordinal=None, replace_id=True, trusteds=()):
    # Here's a js function to find unique elements in set a that are not
    # in set b

    # Make sure there's a place to store timing information for this
    # noun
    noun.command.timing[noun] = noun.command.timing.get(
        noun, {
            'total': 0,
            'times_found': 0
        })
    try:
        js_func = (
            "var seen = [];\n"
            "var matches = arguments[0];\n"
            "var dont_want = arguments[1];\n"
            "return matches.filter(function(el){\n"
            "    if(seen.filter(function(x){return x === el;}).length != 0 || dont_want.filter(function(x){return x === el;}).length != 0) {\n"
            "        return false;\n"
            "    } else {\n"
            "        seen.push(el);\n"
            "        return true;\n"
            "    }\n"
            "});\n")

        filters = filters or [lambda el, noun: True]
        trusted = []
        possibles = []
        ordinal = ordinal or noun.ordinal
        ele = None

        locator_info = {}
        found_elements = {}

        # If there is no ordinal, look for trusted matches
        if not noun.has_ordinal():
            def trusted_generator():
                for xpath in trusteds:
                    if xpath in locator_info:
                        # We've already checked this in the loop, skip it
                        continue
                    xpath_start = time.time()
                    new_possibles = func(xpath)
                    xpath_end = time.time()
                    locator_info[xpath] = {
                        'locator': "%s=%s" % (func.im_func.func_name.rsplit("_", 1)[-1], xpath),
                        'elements': new_possibles,
                        'total': (xpath_end - xpath_start)}
                    for possible in new_possibles:
                        possible.locator = xpath
                        found_elements[possible] = xpath
                        yield possible

            correct_start = time.time()
            elements = trusted_generator()
            for filt in filters:
                elements = itertools.ifilter(functools.partial(filter_timing, filt=filt, noun=noun), elements)

            ele = None
            try:
                # Return first element that we find that can meet the
                # filters
                while True:
                    try:
                        el = next(elements)

                        if not getattr(noun, 'id', None):
                            noun.id = None
                            if replace_id:
                                try:
                                    noun.id = el.get_attribute('id')
                                except WebDriverException, wde:
                                    pass
                        noun.element = el
                        return el
                    except StaleElementReferenceException as sere:
                        # if it's stale, we don't want this one
                        pass
            except StopIteration as si:
                pass

        if not ele:
            # Get all possible matches
            for xpath in finds:
                if xpath in locator_info:
                    # We've already checked this in the loop, skip it
                    continue
                xpath_start = time.time()
                new_possibles = []
                try:
                    new_possibles = func(xpath)
                finally:
                    xpath_end = time.time()
                    locator_info[xpath] = {
                        'locator': "%s=%s" % (func.im_func.func_name.rsplit("_", 1)[-1], xpath),
                        'elements': new_possibles,
                        'total': (xpath_end - xpath_start)}
                new_possibles = [el for el in new_possibles if el in set(new_possibles) - set(possibles)]
                possibles += new_possibles
                for possible in new_possibles:
                    found_elements[possible] = xpath
                    possible.locator = xpath

            if len(possibles) < (ordinal or noun.ordinal):
                # There are not enough possible matches, fail
                return None

            # Get all elements that we know we DON'T want
            filter_elements = []
            filter_dict = {}
            for xpath in nots:
                if xpath in filter_dict:
                    # We've already checked this in the loop, skip it
                    continue
                filter_dict[xpath] = True
                xpath_start = time.time()
                try:
                    new_filters = func(xpath)
                    new_filters = [el for el in new_filters if el in set(new_filters) - set(filter_elements)]
                    filter_elements += new_filters
                    for filter_element in new_filters:
                        found_elements[filter_element] = xpath
                finally:
                    xpath_end = time.time()
                    locator_info[xpath] = locator_info.get(xpath, {
                        'locator': "%s=%s" % (func.im_func.func_name.rsplit("_", 1)[-1], xpath),
                        'elements': new_filters,
                        'total': 0})
                    locator_info[xpath]['total'] += (xpath_end - xpath_start)

            # 'elements' will have all visible elements that meet our criteria.
            # It is determined like this:
            # 1) Get all the elements that match any of the xpaths we're given.
            # 2) Get all the elements that we know we DON'T want, even if they match the xpaths.
            # 3) On the browser side, get unique members of 1 that are not members of 2
            #    We do this on the browser side because it saves us expensive
            #    round trips comparing WebElements for identity
            # 4) run the result of 3 through any filters provided, in order.
            #    This is done lazily, because the filters might be expensive,
            #    performance-wise
            elements = (el for el in noun.parser.interpreter.webdriver.execute_script(js_func, possibles, filter_elements))
            for filt in filters:
                elements = itertools.ifilter(functools.partial(filter_timing, filt=filt, noun=noun), elements)

            i = 0
            el = None

            # Look at elements until we find one that meets criteria or we run
            # out.  Ignore stale elements
            while i < ordinal:
                try:
                    ele = next(elements)
                    i += 1
                except StaleElementReferenceException, sere:
                    # If the element is stale, continue on
                    pass
                except StopIteration, si:
                    # We don't have enough that meet the filter, return None
                    return None

        if ele:
            # We found a match!  Yay!
            el = ele
            for element, locator in found_elements.items():
                if element == el:
                    # This is the element, note the locator that found
                    # it
                    el.locator = locator
                    break

        if not getattr(noun, 'id', None):
            noun.id = None
            if replace_id:
                try:
                    noun.id = el.get_attribute('id')
                except WebDriverException, wde:
                    pass
        noun.element = el
        return el
    finally:
        command_timing = noun.parser.children[-1].timing
        noun_timing = command_timing.get(noun, {})
        if getattr(noun, 'element', None):
            noun_timing['times_found'] = noun_timing.get('times_found', 0) + 1
            noun_timing['locator'] = noun.element.locator
            noun_timing['correct_element'] = sum(info['total'] for locator, info in locator_info.items() if locator == noun.element.locator)
            noun_timing['other_elements_total'] = sum(info['total'] for locator, info in locator_info.items() if locator != noun.element.locator)
        else:
            noun_timing['times_found'] = 0
            noun_timing['locator'] = None
            noun_timing['other_elements_total'] = sum(info['total'] for locator, info in locator_info.items())
        command_timing[noun] = noun_timing

def interpret_noun(self, interpreter, context_element=None, requesting_command=None, locator_func=locator_func):
    context_element = context_element or interpreter.webdriver
    requesting_command = requesting_command or self.command
    xpath = None
    if getattr(self, 'id', None):
        requesting_command.timing[self]['locator'] = 'id=%s' % self.id
        locator = functools.partial(
            locator_func,
            filters=[_displayed_filter] + self.filters + (self.command.verb.filters if self is next(self.command.subject.window_context_nouns) else []),
            noun=self,
            func=context_element.find_elements_by_id,
            finds=[self.id],
            nots=())
    else:
        trusted, xpaths, nots = self.compile()
        requesting_command.timing[self]['locator'] = 'xpath=%s' % xpath
        locator = functools.partial(
            locator_func,
            filters=[_displayed_filter] + self.filters  + (self.command.verb.filters if self is next(self.command.subject.window_context_nouns) else []),
            noun=self,
            func=context_element.find_elements_by_xpath,
            finds=xpaths,
            nots=nots,
            trusteds=trusted)
    try:
        el = locator()
        if el:
            try:
                selenium.webdriver.common.action_chains.ActionChains(interpreter.webdriver).move_to_element_with_offset(el, -1, -1).move_to_element(el).perform()
            except:
                pass
        else:
            raise visionexceptions.UnfoundElementError(self)
        return el
    except StopIteration, si:
        # We didn't find enough things; pass
        pass

def interpret_cell(self, interpreter, context_element, *args, **kwargs):
    header_possibilities = (
        context_element.find_elements_by_xpath(
            './ancestor::table/descendant::th[starts-with(normalize-space(.),%s) and not(starts-with(normalize-space(descendant::th),%s))]' % ((self.value.compile(),) * 2)) +
        context_element.find_elements_by_xpath(
            './ancestor::table/descendant::th[starts-with(normalize-space(.), %s) and not(starts-with(normalize-space(descendant::th), %s))]' % ((self.value.compile(),) * 2)))
    if not header_possibilities:
        raise visionexceptions.UnfoundElementError(self)

    header = None
    for (i, th) in enumerate(header_possibilities, 1):
        if i == self.ordinal:
            header = th
            break
    else:
        raise visionexceptions.VisionException("Cannot find the header cell!")

    if not header:
        raise visionexceptions.UnfoundElementError(self)

    interpreter.center_element(header)
    column_bound = self.parser.interpreter.webdriver.execute_script(
        "return arguments[0].getBoundingClientRect();",
        header)

    # We don't want to center the row horizontally
    interpreter.center_element(context_element, horizontal=False)

    cell_iter = None
    if self.parser.interpreter.webdriver.execute_script("return document.elementsFromPoint;"):
        row_bound = self.parser.interpreter.webdriver.execute_script(
            "return arguments[0].getBoundingClientRect();",
            context_element)
        elements_in_cell = self.parser.interpreter.webdriver.execute_script(
            "return document.elementsFromPoint(arguments[0], arguments[1]);",
            (column_bound['left'] + column_bound['right'])/2,
            (row_bound['top'] + row_bound['bottom'])/2)
        if not elements_in_cell:
            raise visionexceptions.UnfoundElementError(self)

        cell_iter = iter(reversed(filter(
            lambda x: x.tag_name.lower() == 'td',
            itertools.takewhile(
                lambda x, row=context_element:x != row,
                elements_in_cell))))
    else:
        cell_iter = (td for td in
            context_element.find_elements_by_xpath('./td') if
            self.parser.interpreter.webdriver.execute_script("""
                var bounding = arguments[0].getBoundingClientRect();
                return bounding['left'] < arguments[1] && arguments[1] < bounding['right'];""",
                td, (column_bound['left'] + column_bound['right']) / 2))

    i = 0
    cell = None
    while i < self.ordinal:
        try:
            cl = next(cell_iter)
            if cl.is_displayed():
                i += 1
                cell = cl
        except StopIteration as si:
            break
    if not cell:
        raise visionexceptions.UnfoundElementError(self)

    return cell

def interpret_attribute_noun(self, interpreter, context_element=None, requesting_command=None, locator_func=locator_func):
    el = interpret_noun(
        self,
        interpreter,
        context_element,
        requesting_command,
        locator_func)
    return el

def interpret_alert(self, interpreter, *args, **kwargs):
    message = str(self.value) if self.value else None

    try:
        alert = selenium.webdriver.common.alert.Alert(interpreter.webdriver)
        alert.noun = self
        self.element = alert
        text = alert.text
        if message and message not in text:
            raise UnexpectedAlertPresentException(msg="Did not find '%s' alert, found '%s' alert" % (message, text))
        else:
            return alert
    except NoAlertPresentException, nape:
        return None

# Function for interpreting a Subject to a webelement
def interpret_subject(self, interpreter):
    # Get the nouns that are not cached and don't have ids
    nounpath = []
    context = interpreter.webdriver
    for noun in self.window_context_nouns:
        if noun.cached:
            # We've found a noun that's cached, stop looking
            context = noun.element
            break
        else:
            if hasattr(noun, 'element'):
                # there's no good cache, but we have an element.  That's
                # not right, remove it
                del noun.element

            if hasattr(noun, 'id'):
                # We have an id for this noun, kill it
                del noun.id
        nounpath.insert(0, noun)

    for noun in nounpath:
        self.command.timing[noun] = self.command.timing.get(
            noun,
            {'total': 0, 'format': '(%f seconds)'})
        start = time.time()
        try:
            context = noun.interpret(interpreter, context)
        finally:
            end = time.time()
            self.command.timing[noun]['total'] += (end - start)

    return context

# Functions for interpretting Verbs
# Default function for compiling a Verb to Python
def interpret_verb(self, interpreter, ele):
    return True

def interpret_accept(self, interpreter, ele):
    ele.accept()
    return True

def interpret_dismiss(self, interpreter, ele):
    ele.dismiss()
    return True

def interpret_authenticate(self, interpreter, ele):
    uname, passwd = str(self.value).split("/")
    ele.authenticate(uname, passwd)
    return True

def interpret_capture(self, interpreter, ele):
    location = getattr(ele, 'location', {'x': 0, 'y': 0})
    scrollY = location['y']
    if ele:
        if hasattr(ele, 'noun') and not getattr(ele.noun, 'hover_on_capture', None):
            try:
                selenium.webdriver.common.action_chains.ActionChains(interpreter.webdriver).move_to_element_with_offset(ele, -1, -1)
            except:
                pass

    interpreter.webdriver.execute_script(
        "window.scrollTo(0, arguments[0]);", scrollY)

    image = Image.open(StringIO.StringIO(base64.decodestring(interpreter.webdriver.get_screenshot_as_base64()))).convert('RGB')

    if isinstance(ele, selenium.webdriver.remote.webdriver.WebElement) and ele.tag_name.lower() != 'html':
        top = location['y'] - interpreter.webdriver.execute_script("return window.scrollY;")
        size = ele.size
        coordinates = {
            'left': location['x'],
            'top': top,
            'right': location['x'] + size['width'],
            'bottom': top + size['height']}

        # crop and save the picture
        image=image.crop([coordinates[side] for side in ['left', 'top', 'right', 'bottom']])

    self.command.capture = image
    return True

def interpret_clear(self, interpreter, ele):
    ele.clear()
    ele.click()
    return True

def interpret_click(self, interpreter, ele):
    ws_style = False
    try:
        ele.click()
    except WebDriverException as wde:
        # Get around Selenium bug where links that are split over lines
        # can't be clicked.
        if ele.noun.type=='link' and 'unexpected alert open' not in str(wde):
            interpreter.webdriver.execute_script(
                "arguments[0].click();",
                ele)
    return True

def interpret_close(self, interpreter, ele):
    noun = getattr(ele, 'noun', None) if ele else None
    if noun and noun.type.lower() == 'window' and noun.value:
        # We're being told to close a window by name
        interpret_switch_to_window(self, interpreter, ele, resize=False)
    if len(interpreter.webdriver.window_handles) <= 1:
        # We aren't going to close the last window, because then we'd be
        # screwed
        raise visionexceptions.VisionException("Cannot close the last window!")
    try:
        interpreter.webdriver.close()
    except NoSuchWindowException as nswe:
        raise visionexceptions.WindowNotFoundError(command=self.command)
    handles = interpreter.webdriver.window_handles
    if handles:
        interpreter.webdriver.switch_to_window(handles[0])
    return True

def interpret_close_alert(self, interpreter, ele):
    ele.dismiss()
    return True

def interpret_contains(self, interpreter, ele, expected=True, exact=False):
    val = " ".join(str(self.value).split())
    content = " ".join((ele.noun.content if hasattr(ele, 'noun') else ele.text).split())
    if exact:
        return val == content
    else:
        return (expected and val in content) or (not expected and val not in content)

def interpret_contains_dropdown(self, interpreter, ele, expected=True, exact=False):
    val = [" ".join(str(val).split()) for val in self.values]
    content = [" ".join(option.text.split()) for option in ele.noun.content]
    if exact:
        return val == content
    else:
        return (expected and set(val).intersection(set(content))) or (not expected and not set(val).intersection(set(content)))

def interpret_enter_file(self, interpreter, ele):
    file_str = str(self.value)
    if interpreter.webdriver.capabilities['browserName'] == 'chrome':
        interpreter.webdriver.execute_script("arguments[0].visibility = 'visible';", ele) # Chrome won't let you edit file inputs via js, but this seems to circumvent it
    path = self.value.abs_path
    path = os.path.normpath(path)
    keys = ele.send_keys(path)
    print path
    return True

def interpret_load_test(self, interpreter, ele, running=True):
    # Get the absolute path in DOS format; we do this because we
    # assume paths are given in DOS, since that is where the
    # interpreter will run
    if self.value:
        # We were told to load a file
        try:
            interpreter.parser.scanner = interpreter.parser.scanners[str(self.value)]
        except KeyError as key:
            filename = str(self.value)
            abs = ntpath.abspath(filename)
            if os.name != 'nt':
                # We're not running on nt, split and join the path
                abs = os.sep.join(abs.split(ntpath.sep))
            try:
                with open(abs, 'rb') as testfile:
                    interpreter.parser.scanner = interpreter.parser.file_scanner_class(
                        filename=filename,
                        filish=testfile,
                        scanner=visionscanner.BasicTokenizer(commandtype=visionparser.InterpreterCommand),
                        parser=interpreter.parser)
            except IOError, ioe:
                print "There was a problem loading the file '%s'" % abs
        if not running:
            # We don't want to RUN the test, just load it
            interpreter.parser.scanner = interpreter.parser.interactive_scanner
    else:
        # We were not given a value, use the latest file_tokenizer
        interpreter.parser.scanner = interpreter.parser.file_scanner

    return True

def interpret_break(self, interpreter, ele):
    breakpoint_info = str(self.value).split(':')
    breakpoint_line = breakpoint_info.pop()
    breakpoint_filename = breakpoint_info.pop() if breakpoint_info else None
    try:
        scanner = interpreter.parser.scanners[breakpoint_filename] if breakpoint_filename else interpreter.parser.file_scanner

        try:
            breakpoint_line = int(breakpoint_line)

            if len(scanner.lines) >= breakpoint_line:
                scanner.toggle_breakpoint(breakpoint_line)
            else:
                raise visionexceptions.VisionException(
                    command=self.command,
                    message="There are fewer than %d lines in %s" % (
                        breakpoint_line,
                        scanner.name))
        except ValueError as ve:
            # This is a string, try and set a breakpoint on all tokens
            scanner.toggle_token_breakpoint(breakpoint_line.lower())
    except KeyError as ke:
        raise visionexceptions.VisionException(
            command=self.command,
            message="The test%s is not loaded" % (' ' + (breakpoint_filename or '')) )

    return True

def interpret_next_command(self, interpreter, ele):
    scanner=interpreter.parser.file_scanner

    if scanner:
        try:
            interpreter.parser.scanner = scanner

            # Make sure there's a breakpoint after the next line
            scanner.lines[scanner.position + 1]['breakpoint'] = True
        except IndexError as ie:
            pass
    return True

def interpret_step_into_python(self, interpreter, ele):
    scanner = interpreter.parser.file_scanner
    if self.value:
        scanner = interpreter.parser.scanners[str(self.value)]
    if not scanner:
        print "There is no appropriate scanner to step into."
    else:
        interpreter.step = True
        interpreter.parser.scanner = scanner
    return True

def interpret_interactive(self, interpreter, ele):
    interpreter.parser.scanner = interpreter.parser.interactive_scanner
    return True

def interpret_navigate(self, interpreter, ele):
    url = ""
    if self.value:
        url = str(self.value)
    elif ele.tag_name == 'a':
        url = ele.get_attribute('href')
    if url.startswith("?"):
        # if the url we were given starts with a query string, replace
        # query string of the current url, if any, with it
        spliturl = interpreter.webdriver.current_url.split("?")
        if spliturl:
            url = spliturl[0] + url
    url = "https://" + url if not (url.startswith("https://") or url.startswith("http://"))else url
    interpreter.webdriver.get(url)
    return True

def interpret_nothing(self, interpreter, ele):
    return True

def interpret_save_test(self, interpreter, ele):
    indent = ['    ']
    scope_level = 0
    output_list = []
    lines = []

    for command in self.parser.children:
        if (command.usable and not command.error) and command.verb.type not in ('end test', 'end require') and command.scanner.name != interpreter.parser.subcommand_scanner_name:
            lines.append(
                ''.join(indent * scope_level +
                [command.code]))
        scope_level += command.scopechange

    # Get the absolute path in DOS format; we do this because we
    # assume paths are given in DOS, since that is where the
    # interpreter will run
    abs = ntpath.abspath(str(self.value) if self.value else interpreter.default_output_file)
    if os.name != 'nt':
        # We're not running on nt, split and join the path
        abs = os.sep.join(abs.split(ntpath.sep))

    with open(abs, 'wb+') as filish:
        filish.write('\n'.join(lines))
        filish.flush()
        os.fsync(filish.fileno())
    return True

def interpret_finish(self, interpreter, ele):
    interpreter.interactivity_enabled = False
    return True

def interpret_select(self, interpreter, ele):
    from selenium.webdriver.support.ui import Select
    select = Select(ele)
    val = str(self.value)
    numfound = 0
    for el in select.options:
        if not val or el.text.strip().lower().startswith(val.strip().lower()):
            numfound += 1
        if numfound == self.ordinal:
            select.select_by_index(el.get_attribute('index'))
            return True

def interpret_show_test(self, interpreter, ele, getall):
    scanner = interpreter.parser.file_scanner
    if self.value:
        try:
            scanner = interpreter.parser.scanners[str(self.value)]
        except KeyError as ke:
            raise visionexceptions.VisionException(
                command=self.command,
                message="The test%s is not loaded" % (' ' + (breakpoint_filename or '')) )

    if scanner:
        field_width = len(str(len(scanner.lines))) + 1
        for i, line in enumerate(scanner.lines[scanner.position:], scanner.position):
            breakpoint, code = line['breakpoint'], line['code']
            print ("%s% " + str(field_width) + "d| %s") % (("B " if breakpoint else "  "), i + 1, code.rstrip())
    return True

def interpret_show_input(self, interpreter, ele, getall):
    lines = []
    scope_level = 0
    line_number_width = len(str(len(self.parser.children)))
    test_name_width = max([len(command.scanner.name) for command in self.parser.children])
    for (i, command) in enumerate(self.parser.children):
        status = ""
        suffix = ""
        if isinstance(command.verb, visionparser.InterpreterVerb):
            status += "I"
        else:
            status += " "
        if command.removed:
            status += "-"
        else:
            status += " "
        if command.error:
            status += "E"
        elif command.skip or [scope for scope in command.scopes if scope.skip]:
            status += "S"
        else:
            status += " "
        if command.error:
            suffix += "\n\tError: %s" % command.error.message
        for warning in command.warnings:
            suffix += "\n\tWARNING: %s" % "\n\t\t".join(warning)
        else:
            status += "    "
        if (command.usable and not command.error and command.verb.type not in ('end test', 'end require') and command.scanner.name != interpreter.parser.subcommand_scanner_name) or getall:
            lines.append(
                ("%s % " + str(test_name_width) + "s:%s|%s%s%s") % (
                    status,
                    command.filename,
                    ('%%%fd' % line_number_width) % (i + 1),
                    ''.join(['    '] * scope_level),
                    command.code,
                    suffix))
        scope_level += command.scopechange
    print '\n'.join(lines)

    return True

def interpret_skip(self, interpreter, ele):
    skip_lines = 1
    if self.value:
        skip_lines = int(str(self.value))
    scanner = interpreter.parser.file_scanner
    if scanner:
        skip_target = scanner.position + skip_lines
        if skip_target <= len(scanner.lines):
            # The furthest we can skip is to just after the last line.
            scanner.advance(lines=skip_lines, honor_breakpoints=False)
        else:
            raise visionexceptions.VisionException(
                command=self.command,
                message="Cannot skip to line %d in %s, there are only %d lines left" % (
                    skip_target,
                    scanner.name,
                    len(scanner.lines) - scanner.position))
    else:
        # There's no filescanner, we can't skip anything
        raise visionexceptions.VisionException(
            command=self.command,
            message="There are no files loaded")
    return True

def interpret_switch_to_default(self, interpreter, ele=None):
    try:
        interpreter.webdriver.switch_to_default_content()
        return True
    except:
        return False

def interpret_switch_to_window(self, interpreter, ele=None, resize=True):
    def get_window(driver, title, current_handle):
        # We're switching the window, so blow away our OS handle
        interpreter._handle = None
        current_is_right = False
        for handle in driver.window_handles:
            if current_handle != handle:
                driver.switch_to_window(handle)
                if driver.title.startswith(title) or (
                    driver.current_url.endswith(title) and title.startswith("?")):
                    return handle
                    return handle
        else:
            driver.switch_to_window(current_handle)
            if driver.title.startswith(title):
                return current_handle

    noun = getattr(ele, 'noun', None) if ele else None
    locator = str(noun.value if noun and noun.type.lower() == 'window' else next(self.command.subject.window_context_nouns).value)
    current_handle = None
    try:
        current_handle = interpreter.webdriver.current_window_handle
    except NoSuchWindowException as nswe:
        pass

    new_handle = get_window(
        driver=interpreter.webdriver,
        title=locator,
        current_handle=current_handle)

    if not new_handle:
        return False

    if resize:
        size_dir = interpreter.webdriver.get_window_size()
        if size_dir != {'width': 1024, 'height': 768}:
            # Need to resize the window
            interpreter.webdriver.set_window_size(1024, 768)
    return True

def interpret_switch_to_frame(self, interpreter, ele=None):
    def get_frame(driver, identifier):
        try:
            driver.switch_to_frame(identifier)
            return True
        except:
            return False

    # Switch
    noun = next(self.command.subject.window_context_nouns)
    return get_frame(
        driver=interpreter.webdriver,
        identifier=str(noun.value) if noun.value else noun.ordinal-1)

def interpret_push(self, interpreter, ele, value=None):
    value = value or str(self.value)
    keys = []
    for k in value.split("-"):
        if len(k) > 1:
            try:
                k = getattr(Keys, k)
            except AttributeError as ae:
                try:
                    k = getattr(Keys, k.upper())
                except AttributeError as ae2:
                    raise ae
        else:
            # We assume lower case for letters
            k = k.lower()
        keys.append(k)
    if value.endswith("-"):
        # Add a - to the keys.  this what someone can do "Push 'CTRL--'"
        # to push Control chorded with minus
        keys.append("-")
    key = ''.join(keys)
    ele.send_keys(key)
    return True

def interpret_replace(self, interpreter, ele):
    elval = ele.noun.content
    found = 0
    values = list(str(v) for v in self.values)
    for i in range(len(elval) - len(values[0]) + 1):
        if elval[i:].startswith(values[0]):
            found += 1
            if found == self.ordinal:
                # We found the match to replace
                ele.clear()
                ele.send_keys(elval[:i] + values[1] + elval[i + len(values[0]):])
                ele.send_keys(Keys.TAB)
                break
    else:
        raise visionexceptions.VisionException("Unable to find %d ocurrence(s) in the textfield" % self.ordinal)
    return True

def interpret_type(self, interpreter, ele, tab=True):
    value = str(self.value)
    ele.clear()
    ele.click()
    ele.send_keys(value)
    if tab:
        ele.send_keys(Keys.TAB)
    return True

def interpret_type_alert(self, interpreter, ele):
    keys = ele.send_keys(str(self.value))
    return True

def interpret_set(self, interpreter, ele=None):
    val = str(self.value)
    if val not in interpreter.flags:
        interpreter.flags[val] = True
    return True

def interpret_require(self, interpreter, ele=None):
    name = self.value.identifier.strip("'\"")
    if name not in interpreter.flags:
        interpreter.parser.subcommand_scanner.addline([
            'Set "%s"' % name.rsplit('.', 1)[0],
            'Load test <%s>' % name ])
        self.command.url = interpreter.webdriver.current_url
        interpreter.parser.scanner = interpreter.parser.subcommand_scanner
    else:
        # The requirement was already met
        if interpreter.parser.scanner is interpreter.parser.interactive_scanner:
            # We don't want to do anything here, this is an error
            raise Exception( "The requirement is already met" )
        self.command.skip = "The requirement is already met"
    return True

def interpret_go_back(self, interpreter, ele):
    interpreter.webdriver.back()
    return True

def interpret_quit(self, interpreter, ele):
    try:
        interpreter.quit()
    except:
        pass
    print "\n" + "Goodbye!"
    sys.exit()
    return True

def interpret_wait(self, interpreter, ele):
    import time
    time.sleep(int(str(self.value)))
    return True

def command_action(self):
    added_tokens = []
    if self.verb:
        if self.verb.type in ('require', 'test', 'validate'):
            # if this command is for a scope, we need to do some extra
            # housekeeping
            if not self.verb.value and self.subject:
                # The scope has no value, use the value of the first
                # noun.  If there aren't any nouns, or the first doesn't
                # have a value, then there are UnmetTokenRequirements,
                #and that'll get yelled at later
                val = str(self.subject.nouns[0].value) if self.subject.nouns[0].value else (self.subject.code[0].capitalize() + self.subject.code[1:])

                # I didn't actually design the parser with this sort of
                # injection in mind.  This is a really good place for
                # there to be a bug... WATCH CAREFULLY to make sure the
                # stream doesn't get jacked up here
                self.verb.consume(visionparser.Literal(
                    identifier=str(val),
                    start=self.verb.start + len(self.verb.code) + 1))

            if not self.variable and self.subject:
                # This command does not have an explicit Variable, and
                # it needs one
                # Put Variable and the Literal that is the Variables name on the
                # stream
                added_tokens.extend([
                    visionparser.Variable(
                        identifier='as',
                        start=self.start),
                    visionparser.Literal(
                        identifier=str(self.verb.value),
                        start=self.start)])
        if self.verb.type == 'navigate' and not (self.verb.value or self.subject.type == 'link'):
            raise visionexceptions.UnmetTokenRequirements(
                parser=self,
                token=self,
                message="'Navigate' requires either a URL or a link")
    return added_tokens

def interpreter_verb_action(self):
    # Commands with an interpreter verb are of type 'interpreter'
    self.command.type = 'interpreter'
    self.command.uses_elements = False
    self.command.check_readyState = False
    return []

def test_action(self):
    # Tests have to have either a value, or a noun so that we can name
    # them
    self.command.scopechange = 1
    if not self.value:
        # We don't have a value.  Get the first noun, and use its value
        # to make one of our own
        if visionparser.Noun not in self.command.number_of_tokens:
            # The command has to have a Noun, so if it doesn't have one
            # already, add it to the must have dict
            self.command.must_have[visionparser.Noun] = self.command.must_have.get(visionparser.Noun, 1)
    return []

def skip_action(self):
    # Skipped commands must have a comment, if it doesn't yet, mark that
    # it has to have one
    if not self.command.comment:
        self.command.must_have[visionparser.Comment] = 1

    return []

def structure_commands_action(self, remove):
    # Get the lines to remove
    lineset = set([])
    for spread in str(self.value).split(','):
        ends = list(int(n.strip()) for n in spread.split('-'))
        if ends:
            if len(ends) == 1:
                # We don't have a range, but a single line
                # Make it into a range
                ends.append(ends[0] + 1)
            lineset |= set(range(*ends))
    lines = sorted(list(lineno for lineno in lineset if lineno >= 0))

    # Remove the lines
    for lineno in lines:
        try:
            self.parser.children[lineno].removed = remove
        except IndexError, ie:
            pass
    return []

def switch_action(self):
    # Commands with a switch verb are of type 'change focus'
    self.command.uses_elements = False
    self.command.type = 'change focus'
    return []

def existence_action(self):
    # Commands with should (not) exist verb ar of type 'existence'
    self.command.uses_elements = False
    self.command.type = 'existence'
    return []

def window_action(self):
    # We're dealing with windows, we're not looking for elements
    self.command.uses_elements = False
    self.command.check_readyState = False
    return []

def alert_action(self):
    # If we're working with alerts, we don't care if this window is ready
    self.command.check_readyState = False
    return []

def frame_action(self):
    self.command.uses_elements = False
    return []

def end_scope_action(self, matching_type):
    # Commands with a end test verb are of type 'scope'
    self.command.type = 'scope'
    self.command.check_readyState = False
    self.command.uses_elements = False

    # Handle closing scope
    interpreter = self.command.parser.interpreter
    closers = []
    change = 0
    min_change = 0
    close_url = None
    try:
        for scope in self.command.scope_iter:
            change -= scope.scopechange
            if change < min_change:
                min_change = change
                if scope.verb.type == matching_type:
                    if not self.value or str(scope.verb.value) == str(self.value):
                        # We're ending the most recent scope, or we've
                        # found a specific scope to end
                        if not scope.skip:
                            close_url = getattr(scope, 'url', None)
                        break
        else:
            # We're trying to close a scope that was never opened
            raise visionexceptions.UnmatchedEndScopeError(self.command)
    finally:
        if change:
            self.command.scopechange = change
    if close_url and (not interpreter.errorfound or interpreter.interactivity_enabled):
        # We need to close back to where we started this
        interpreter.webdriver.get(close_url)
    return []

def noun_ready(self, interpreter, ele):
    try:
        return True
    except AttributeError as ae:
        return True
    except:
        return False

def filter_timing(el, filt, noun):
    # Handle profiling information for filters
    filter_start=time.time()
    try:
        return filt(el, noun=noun)
    finally:
        noun.command.timing[noun][filt.__name__ if hasattr(filt, '__name__') else filt.func.__name__] = time.time() - filter_start

def _displayed_filter(e, noun):
    result = e.is_displayed()
    return result

def _exact_filter(e, noun, attribute):
    # verify the widget has the right value
    if not noun.value:
        result = True
    else:
        elval = e.get_attribute(attribute) or e.text
        result = not noun.value or elval == str(noun.value)
    return result

def _starts_with_filter(e, noun, attribute):
    # Verify the widget starts with the right value
    if not noun.value:
        result = True
    else:
        elval = e.get_attribute(attribute) or e.text
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

class InteractiveParser(visionparser.VisionParser):
    subcommand_scanner_name = '<subcommand>'
    interactive_scanner_name = '<interactive>'

    def __init__(self, scanners=None, interactive_scanner_class=visionscanner.InteractiveVisionScanner, file_scanner_class=visionscanner.VisionFileScanner, interpreter=None, maximum_wait=15, allowable_time=3, interactive_maximum_time=5, interactive_allowable_time=3):
        self.interactive_scanner_class=interactive_scanner_class
        self.file_scanner_class=file_scanner_class
        self.interpreter=interpreter
        interpreter.parser=self

        self.interactive_times = {
            'maximum_time': interactive_maximum_time,
            'allowable_time': interactive_allowable_time
        }
        self.normal_times = {
            'maximum_time': maximum_wait,
            'allowable_time': allowable_time
        }

        scanners = scanners if scanners else []

        if not isinstance(scanners, list):
            scanners = [scanners]

        self._subcommand_scanner = interactive_scanner_class(
            name=self.subcommand_scanner_name,
            tokenizer=visionscanner.InteractiveTokenizer(commandtype=visionparser.InterpreterCommand),
            subcommand=True,
            parser=self)
        interactive_scanner = interactive_scanner_class(
            name=self.interactive_scanner_name,
            tokenizer=visionscanner.InteractiveTokenizer(commandtype=visionparser.InterpreterCommand),
            parser=self)
        scanners = [self._subcommand_scanner, interactive_scanner] + scanners
        self.scanners = collections.OrderedDict()

        # Put every scanner in
        for s in scanners:
            self.scanner = s

        interpreter.numlines = len(self.scanner.lines)
        # We'll end up putting the last scanner in again, but that's ok
        super(InteractiveParser, self).__init__(scanners[-1])

    @property
    def interactive_scanner(self):
        try:
            return self.scanners[self.interactive_scanner_name]
        except KeyError, ke:
            return None

    @property
    def subcommand_scanner(self):
        try:
            return self.scanners[self.subcommand_scanner_name]
        except KeyError, ke:
            return None

    @property
    def file_scanner(self):
        scanners = reversed(self.scanners.values())
        for scanner in scanners:
            if isinstance(scanner, visionscanner.VisionFileScanner):
                return scanner
        else:
            return None

    @file_scanner.deleter
    def file_scanner(self):
        for key, scanner in self.scanners.items():
            if isinstance(scanner, visionscanner.VisionFileScanner):
                del self.scanners[key]
        return None

    @property
    def scanner(self):
        new_scanner = None
        for (scanner_name, scanner) in reversed(self.scanners.items()):
            if scanner == self.interactive_scanner:
                if self.interpreter.interactivity_enabled:
                    return scanner
            else:
                return scanner
        return new_scanner

    @scanner.setter
    def scanner(self, scanner):
        old_scanner = self.scanner
        if scanner:
            if scanner.name in self.scanners:
                # We're setting the scanner to one we already have.  Pop it
                # from the dictionary and put it back in, so that it is the
                # most recent
                self.scanners[scanner.name] = self.scanners.pop(scanner.name)
            else:
                # New scanner
                self.scanners[scanner.name] = scanner
            if old_scanner is self._subcommand_scanner and scanner is not self._subcommand_scanner and self.scanners.keys()[0] != self._subcommand_scanner.name:
                # the subcommand scanner is always last, unless it is the
                # current scanner.  If we replace it, we need to make a new
                # dictionary, so it can go in first and be at the bottom of
                # the stack
                scanners = collections.OrderedDict()
                del self.scanners[self._subcommand_scanner.name]
                scanners[self._subcommand_scanner.name] = self._subcommand_scanner
                for name, scanner in self.scanners.items():
                    scanners[name] = scanner
                self.scanners = scanners

        # Remove any breakpoints on the first line of the file if we're
        # switching from the interactive_scanner
        if isinstance(scanner, visionscanner.VisionFileScanner) and old_scanner is self.interactive_scanner:
            try:
                scanner.lines[scanner.position]['breakpoint'] = False
            except IndexError as ie:
                # Either there is no file or the scanner does not support
                # breakpoints, so we can ignore this
                pass

        return scanner

    def next(self):
        if not self.scanner:
            # If there's no scanner, raise StopIteration
            raise StopIteration()
        try:
            next_command = super(InteractiveParser, self).next()
            return next_command
        except StopIteration, si:
            # We may have exhausted the scanner, or we may
            # just need to change scanners
            if isinstance(self.scanner, visionscanner.VisionFileScanner) and not self.scanner.done:
                # We've hit a breakpoint.
                if self.interpreter.interactivity_enabled:
                    # Set the scanner to interactive
                    self.scanner = self.interactive_scanner
            elif self.scanner.done:
                if self.scanner is self.subcommand_scanner:
                    # This is the subcommand scanner, go back to the
                    # origin
                    self.scanner = self.children[-1].origin_scanner
                if self.scanner is not self.interactive_scanner and self.scanner.done:
                    for name, scanner in reversed(self.scanners.items()):
                        if scanner.done:
                            # We've exhausted the scanner
                            if isinstance(scanner, visionscanner.VisionFileScanner):
                                # It's a file, remove it
                                del self.scanners[name]
                        else:
                            self.scanner = scanner
                            break
                    else:
                        # All file scanners were exhausted
                        if self.interpreter.interactivity_enabled:
                            # We allow interactive mode, switch scanner
                            self.scanner = self.interactive_scanner
                        else:
                            # no scanner we can use, reraise
                            raise
            if not self.scanner or (self.scanner is self.subcommand_scanner and self.scanner.done):
                # We're not able to get a new main scanner
                raise
            return self.next()

    @property
    def number_of_lines(self):
        # We don't count subcommands as lines
        return len([c for c in self.children if c.scanner.name != self.subcommand_scanner_name])

class BasicVisionOutput(visionoutput.VisionOutput):
    """
    Output handling for a command in a Vision session.  This output is
    for printing to the console, code for outputting to logfiles should
    be done in another class.
    """
    def setup_outputs(self, outputs):
        super(BasicVisionOutput, self).setup_outputs(outputs)
        outputs['file_literal'] = output_file_literal

def browser_unsupported(browser_options):
    raise visionexceptions.VisionException(
        message="The browser requested is not supported: %s" %
        browser_options['type'])

def browser_chrome(browser_options):
    browser = browser_options.pop('type')
    remote = browser_options.pop('remote')
    p = webdriver.ChromeOptions()

    # Chrome always has native events
    # p.native_events_enabled = False
    p.add_experimental_option("prefs", browser_options)
    if remote:
        # Make a remote webdriver
        return webdriver.Remote(
            command_executor=remote,
            desired_capabilities=p.to_capabilities())
    else:
        return webdriver.Chrome(chrome_options=p)

def browser_firefox(browser_options):
    browser = browser_options.pop('type')
    remote = browser_options.pop('remote')
    p = webdriver.firefox.firefox_profile.FirefoxProfile()
    p.native_events_enabled = False
    for key, value in browser_options.items():
        p.set_preference(key, value)
    if remote:
        # Make a remote webdriver
        return webdriver.Remote(
            command_executor=remote,
            desired_capabilities=DesiredCapabilities.FIREFOX.copy(),
            browser_profile=p)
    else:
        return webdriver.Firefox(
            firefox_profile=p,
            firefox_binary=webdriver.firefox.firefox_binary.FirefoxBinary(
                firefox_path=None))

def browser_internetexplorer(browser_options):
    browser = browser_options.pop('type')
    remote = browser_options.pop('remote')
    if remote:
        # Make a remote webdriver
        return webdriver.Remote(
            command_executor=remote,
            desired_capabilities=DesiredCapabilities.INTERNETEXPLORER.copy())
    else:
        return webdriver.Ie()

class VisionInterpreter(object):
    """
    This sets up the compilation functions that turn the parse tree into
    xpaths, which are used by Selenium to find elements on the page.
    It also sets up functions that handle interpreting, by actually calling
    selenium API.

    It is an iterator.  Each iteration will interpret one parsed Command.

    This should not know ANYTHING about the language used for input, that
    should be contained to the scanner.  I have a feeling this last rule is
    broken in some places...  This is an opportunity for improvement.
    """

    # The callables the interpreter will use for the various activities
    # on various tokens.  Since updating a Typed class also updates its
    # subclasses, it's important that one order this from most general
    # to most specific
    defaults = collections.OrderedDict([
        (visionparser.Command, {
            'actions': command_action,
        }),
        (visionparser.InterpreterCommand, {
            'interprets': interpret_selenium_command,
        }),
        (visionparser.Subject, {
            'interprets': interpret_subject,
        }),
        (visionparser.Noun, {
            'compiles': compile_noun_to_xpath,
            'interprets': interpret_noun,
            'readies': noun_ready,
            'contents': lambda noun:noun.element.text,
        }),
        (visionparser.AttributeNoun, {
            'interprets': interpret_attribute_noun,
        }),
        (visionparser.Verb, {
            'interprets': interpret_verb,
        }),
        (visionparser.InterpreterVerb, {
            'actions': interpreter_verb_action,
        }),
    ])

    callables = collections.OrderedDict([
        (visionparser.Noun, {
            # post-parse actions
            'actions': {
                'window': window_action,
                'alert': alert_action,
                'frame': frame_action,
            },
            # compile Nouns to XPath
            'compiles': {
                'box': compile_box_to_xpath,
                'button': compile_button_to_xpath,
                'icon button': compile_icon_button_to_xpath,
                'link': functools.partial(compile_noun_to_xpath, tag='a', compare_type='link'),
                'row': compile_row_to_xpath,
                'table': compile_table_to_xpath,
                'table body': functools.partial(compile_simple_to_xpath, tag='tbody'),
                'table header': functools.partial(compile_simple_to_xpath, tag='thead'),
                'table footer': functools.partial(compile_simple_to_xpath, tag='tfoot'),
                'dropdown': functools.partial(compile_noun_to_xpath, tag='select'),
                'radio button': functools.partial(compile_noun_to_xpath, tag='input[%s="radio"]' % case_insensitive("@type"), is_toggle=True),
                'checkbox': functools.partial(compile_noun_to_xpath, tag='input[%s="checkbox"]' % case_insensitive("@type"), is_toggle=True),
                'textarea': functools.partial(compile_noun_to_xpath, tag='textarea'),
                'textfield': compile_textfield_to_xpath,
                'image': compile_image_to_xpath,
                'text': functools.partial(compile_noun_to_xpath, compare_type='string'),
                'file input': functools.partial(compile_noun_to_xpath, tag='input[%s="file"]' % case_insensitive("@type")),
            },
            # interpret via selenium to get WebElement
            'interprets': {
                'alert': interpret_alert,
                'cell': interpret_cell,
            },
            # verify the element is ready after getting it
            'readies': {
            },
            # verify the contents of an element
            'contents': {
                'button': lambda noun: noun.element.get_attribute('value') or noun.element.text,
                'dropdown': lambda noun: selenium.webdriver.support.ui.Select(noun.element).all_selected_options,
                'textfield': lambda noun: noun.element.get_attribute('value') or noun.element.get_attribute('placeholder'),
                'textarea': lambda noun: noun.element.get_attribute('value') or noun.element.get_attribute('placeholder'),
            },
        }),
        (visionparser.Verb, {
            'actions': {
                'switch': switch_action,
                'test': test_action,
                'require': test_action,
                'should exist': existence_action,
                'should not exist': existence_action,
            },
            'interprets': {
                'accept': collections.defaultdict( lambda: interpret_accept ),
                'dismiss': collections.defaultdict( lambda: interpret_dismiss ),
                'authenticate': collections.defaultdict( lambda: interpret_authenticate ),
                'capture': collections.defaultdict( lambda: interpret_capture ),
                'click': collections.defaultdict( lambda: interpret_click ),
                'hover over': collections.defaultdict( lambda: functools.partial(
                    interpret_existence_check,
                    expected=True)),
                'clear': collections.defaultdict( lambda: interpret_clear ),
                'close': collections.defaultdict(
                    lambda: interpret_close, {
                        'alert': interpret_close_alert,
                    }),
                'push': collections.defaultdict( lambda: interpret_push ),
                'replace': collections.defaultdict( lambda: interpret_replace ),
                'enter file': collections.defaultdict( lambda: interpret_enter_file ),
                'should contain': collections.defaultdict( 
                    lambda: interpret_contains, {
                        'dropdown': interpret_contains_dropdown,
                    }),
                'should contain exactly': collections.defaultdict(
                    lambda: functools.partial(interpret_contains, exact=True), {
                        'dropdown': functools.partial(interpret_contains_dropdown, exact=True),
                    }),
                'should not contain': collections.defaultdict(
                    lambda: functools.partial(interpret_contains, expected=False), {
                        'dropdown': functools.partial(interpret_contains_dropdown, expected=False),
                    }),
                'require': collections.defaultdict( lambda: interpret_require ),
                'navigate': collections.defaultdict( lambda: interpret_navigate ),
                'nothing': collections.defaultdict( lambda: interpret_nothing ),
                'select': collections.defaultdict( lambda: interpret_select ),
                'switch': collections.defaultdict(
                    lambda: interpret_switch_to_default, {
                        'default': interpret_switch_to_default,
                        'frame': interpret_switch_to_frame,
                        'window': interpret_switch_to_window,
                    }),
                'test': collections.defaultdict( lambda: interpret_verb ),
                'type': collections.defaultdict( lambda: interpret_type ),
                'wait': collections.defaultdict( lambda: interpret_wait ),
                'should exist': collections.defaultdict( lambda: functools.partial(
                    interpret_existence_check,
                    expected=True), {
                        'alert': functools.partial(interpret_existence_check_in_alert, expected=True),
                    }),
                'should not exist': collections.defaultdict( lambda: functools.partial(
                    interpret_existence_check,
                    expected=False), {
                        'alert': functools.partial(interpret_existence_check_in_alert, expected=True),
                    }),
                'should be checked': collections.defaultdict( lambda: functools.partial(
                    interpret_checked_check,
                    expected=True)),
                'should not be checked': collections.defaultdict( lambda: functools.partial(
                    interpret_checked_check,
                    expected=False)),
                'go back': collections.defaultdict( lambda: interpret_go_back ),
            },
        }),
        (visionparser.InterpreterVerb, {
            'actions': {
                'end test': functools.partial(end_scope_action, matching_type='test'),
                'end require': functools.partial(end_scope_action, matching_type='require'),
            },
            'interprets': {
                'set': collections.defaultdict( lambda: interpret_set ),
                'end test': collections.defaultdict( lambda: interpret_verb ),
                'end require': collections.defaultdict( lambda: interpret_verb ),
                'load test': collections.defaultdict( lambda: functools.partial(interpret_load_test, running=False)),
                'run test': collections.defaultdict( lambda: interpret_load_test ),
                'next command': collections.defaultdict( lambda: interpret_next_command ),
                'break': collections.defaultdict( lambda: interpret_break ),
                'step into python': collections.defaultdict( lambda: interpret_step_into_python ),
                'interactive': collections.defaultdict( lambda: interpret_interactive ),
                'save test': collections.defaultdict( lambda: interpret_save_test ),
                'finish': collections.defaultdict( lambda: interpret_finish ),
                'show test': collections.defaultdict( lambda: functools.partial(interpret_show_test, getall=False) ),
                'show input': collections.defaultdict( lambda: functools.partial(interpret_show_input, getall=False) ),
                'show all input': collections.defaultdict( lambda: functools.partial(interpret_show_input, getall=True) ),
                'skip': collections.defaultdict( lambda: functools.partial(interpret_skip) ),
                'quit': collections.defaultdict( lambda: interpret_quit ),
            },
        }),
        (visionparser.Skip, {
            'actions': {
                'is skipped': skip_action,
            },
        }),
    ])

    tokens = {
        # These tokens go into all variants of the language
        visionscanner.BasicTokenizer: {
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
            'button': [visionparser.Noun, {'filters': [
                functools.partial(_exact_filter, attribute='value'),
                functools.partial(_starts_with_filter, attribute='value')]}],
            'icon_button': [visionparser.Noun, {'filters': [
                functools.partial(_exact_filter, attribute='title'),
                functools.partial(_starts_with_filter, attribute='title')]}],
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
        },
    }

    browsers = {
        'firefox': browser_firefox,
        'chrome': browser_chrome,
#        'android': browser_unsupported,
#        'edge': browser_unsupported,
#        'htmlunit': browser_unsupported,
#        'htmlunitwithjs': browser_unsupported,
        'internetexplorer': browser_internetexplorer,
#        'ipad': browser_unsupported,
#        'iphone': browser_unsupported,
#        'opera': browser_unsupported,
#        'phantomjs': browser_unsupported,
#        'safari': browser_safari,
    }

    browser_profile = {
        'dom.max_chrome_script_run_time': 60,
        'browser.download.folderList': 2,
        'browser.download.manager.showWhenStarting': False,
        'webdriver_accept_untrusted_certs': True,
        'webdriver_assume_untrusted_issuer': False,
        'browser.download.dir': '.',
        'browser.helperApps.neverAsk.saveToDisk': 'application/csv;application/octet-stream',
    }

    def __init__(self, verbose=False, acceptable_wait=3, maximum_wait=15, default_output_file='', outputters=None, browser_options=None):
        self.setup()
        if not browser_options:
            browser_options = {}
        browser_options['type'] = browser_options.get('type', 'firefox')
        browser_options['remote'] = browser_options.get('remote', None)
        self.step = False
        self.acceptable_wait = acceptable_wait
        self.interactivity_enabled = True
        self.maximum_wait = maximum_wait
        self.default_output_file=default_output_file
        self.outputters = outputters or [BasicVisionOutput(self)]
        self.verbose = verbose
        self.errorfound = False
        self._handle = None
        self.browser_options = browser_options
        if not self.flags:
            self.flags = collections.OrderedDict()

    def __iter__(self):
        return self

    def locate(self, function, command, acceptable_wait=None, maximum_wait=None, expected=True):
        maximum_wait = maximum_wait or command.wait
        acceptable_wait = acceptable_wait or self.acceptable_wait
        ele = None

        def ele_is_ready(driver):
            el = function()
            if el and (not hasattr(el, 'noun') or el.noun.ready):
                return el
            else:
                return False

        ele = ele_is_ready(self.webdriver) if expected else not ele_is_ready(self.webdriver)
        return ele

    def handle_interpret_command_exception(self, ex, command):
        command.error = ex
        import traceback
        command.trace = traceback.format_exc()
        self.errorfound = True
        self.executed = True
        return False

    def focus_on_browser(self):
        # Make sure the OS is focused on our browser, so that
        # focus/blur events work.
        # This is Windows specific, but we'll fix that later, if need be
        if platform.system() == "Windows":
            alert = selenium.webdriver.common.alert.Alert(self.webdriver)
            try:
                alert.text
                # There's an alert if we get here, so we can't get the
                # webdriver title
            except NoAlertPresentException as nape:
                # there wasn't an alert, that means we can focus on the
                # app

                import pywintypes
                import win32gui
                import win32con
                try:
                    if not self._handle:
                        top_windows = []
                        win32gui.EnumWindows(
                            lambda hwnd,
                            top_windows:top_windows.append((hwnd, win32gui.GetWindowText(hwnd))), top_windows)
                        windows = [win[0] for win in top_windows if str(self.webdriver.title) in win[1]]
                        self._handle = windows[0]

                    if win32gui.GetForegroundWindow() != self._handle:
                        win32gui.ShowWindow(self._handle,win32con.SW_SHOW)
                        win32gui.SetForegroundWindow(self._handle)
                except pywintypes.error as pwte:
                    pass

    @property
    def webdriver(self):
        if not getattr( self, '_webdriver', None ):
            profile_options = self.browser_profile.copy()
            profile_options.update(self.browser_options)
            self._webdriver=self.browsers[profile_options['type']](profile_options)
        return self._webdriver

    def compile(self):
        return '\n'.join(l for l in self)

    def handle_parse(self):
        command = None
        try:
            command = self.parser.next()
        except StopIteration:
            # We don't want to catch StopIterations
            raise
        except Exception as e:
            command = getattr(e, 'command', None)
            self.errorfound = True
            if not isinstance(e, visionexceptions.VisionException):
                e = visionexceptions.GarbageInputError(
                    command=command,
                    start=0,
                    message="This is not valid Vision.")
            if command:
                command.error = e
        if command:
            command.executed = False
        return command

    def check_page_ready(self, command):
        return self.webdriver.execute_script("return document.readyState == 'complete' || document.readyState == 'interactive';")

    def handle_interpret(self, command):
        ele = None

        command.executed = True
        try:
            if command.check_readyState:
                # If this is a command that cares whether we are ready,
                # then verify that
                check_start = time.time()
                try:
                    ready = self.check_page_ready(command)
                    if ready:
                        command.window_handle = self.webdriver.current_window_handle
                    else:
                        # Tell the wait loop to wait and try again
                        return False
                finally:
                    command.timing['check_readyState'] = command.timing.get('check_readyState', 0) + time.time() - check_start
            return command.interpret(interpreter=self, ele=ele)
        except UnexpectedAlertPresentException as uape:
            raise
        except WebDriverException as wde:
            # We have a webdriverexception, so return false so we
            # try again
            return False
        except visionexceptions.UnfoundElementError as uee:
            # We couldn't find an element, so return false so we
            # try again
            return False
        except Exception as e:
            raise

    def next(self):
        stepped = False
        if self.step and self.parser.file_scanner:
            # We're supposed to step into python
            stepped = True
            self.parser.scanner = self.parser.file_scanner
            self.step = False

        start = time.time()
        command = None
        try:
            command = self.handle_parse()

            start = time.time()
            skipscope = [scope for scope in command.scopes if scope.skip]
            errored_or_skipping = command.error or (self.errorfound and not self.interactivity_enabled) or (command.skip or skipscope)
            is_to_the_interpreter = self.interactivity_enabled and not (command.error or command.skip) and isinstance(command.verb, visionparser.InterpreterVerb)
            if not errored_or_skipping or is_to_the_interpreter:
                try:
                    # We parsed successfully and we are still executing commands
                    if is_to_the_interpreter or not command.verb.timed:
                        # We don't want to time interpreter commands
                        self.handle_interpret(command)
                    else:
                        WebDriverWait(command, command.wait).until(self.handle_interpret)
                except Exception as e:
                    self.handle_interpret_command_exception(e, command)
        except StopIteration as si:
            # We want stop iterations to propagate to the main loop
            raise
        except Exception as e:
            command = getattr(e, 'command', None)
        finally:
            if command:
                # We can only figure out how long it took to run the
                # command if we're able to tokenize and parse the
                # command
                finish = time.time()

                time_format = '(%f seconds)'
                if stepped:
                    # Change the time format to indicate the timing might not be
                    # reliable
                    time_format += '; code was debugged, timing information might not be accurate'

                    if not isinstance(command.scanner, visionscanner.VisionFileScanner):
                        # We inserted a step before a command that caused
                        # subcommands to be added, so we need to keep stepping
                        self.step = True
                    elif not command.subcommands:
                        # Finish a step in interactive mode if we don't have
                        # subcommands
                        self.parser.scanner = self.parser.interactive_scanner

                command_total = finish - start
                command.timing[command] = {
                    'format': time_format,
                    'total': command_total
                }

                if command_total > self.acceptable_wait:
                    warning = {
                        'title': "Took %f seconds, expected no more than %f" % (command_total, self.acceptable_wait),
                        'subwarnings': []
                    }
                    if command.check_readyState:
                        warning['subwarnings'].append(
                            "Time spent waiting for the page to be ready: %f seconds" % (
                                command.timing.get('check_readyState', 0)))
                    if command.uses_elements and command.subject:
                        for noun in command.subject.nouns:
                            if noun in command.timing:
                                if 'times_found' not in command.timing[noun]:
                                    # This noun doesn't support timing
                                    # information, continue
                                    warning['subwarnings'].append(
                                        "Noun '%s': took a total of %f seconds to find element" % (
                                            noun.code,
                                            command.timing[noun]['total']))
                                    warning['subwarnings'].append(
                                        "This noun does not provide detailed timing information")
                                elif command.timing[noun]['times_found']:
                                    warning['subwarnings'].append(
                                        "Noun '%s': took a total of %f seconds and %d searches to find element" % (
                                            noun.code,
                                            command.timing[noun]['total'],
                                            command.timing[noun]['times_found']))
                                    warning['subwarnings'].append(
                                        "Time to find matching element: %f seconds" % command.timing[noun]['correct_element'])
                                    warning['subwarnings'].append(
                                        "Time to find rejected elements: %f seconds" % command.timing[noun]['other_elements_total'])
                                    for name, total in ((filter_name, filter_total) for filter_name, filter_total in command.timing[noun].items() if "_filter" in filter_name):
                                        warning['subwarnings'].append(
                                            "Time to filter elements with %s: %f seconds" % (name, total))
                                else:
                                    warning['subwarnings'].append(
                                        "'%s': was not found after %f seconds" % (
                                            noun.code,
                                            command.timing[noun]['total']))
                    if command.verb in command.timing:
                        warning['subwarnings'].append(
                            "Verb '%s': took %f seconds to complete" % (
                                command.verb.code,
                                command.timing[command.verb]['total']))
                    else:
                        warning['subwarnings'].append(
                            "'%s': Was never executed" % command.verb.code)
                    command.warnings.append(warning)

        return command

    def output(self, out):
        for outputter in self.outputters:
            outputter.output(out)

    def handle_output(self, command):
        try:
            self.output(command)

            # Rewind interpreter errors when interactivity is enabled and the scanner can be rewound
            if command.error and self.interactivity_enabled:
                supercommand = None
                if command.origin_scanner is not command.scanner:
                    try:
                        supercommand = next(com for com in command.previous_commands_iter if com.scanner is com.origin_scanner)
                    except StopIteration as si:
                        # There's no supercommand
                        pass
                if command.executed and hasattr(command.origin_scanner, 'rewind') and (not supercommand or not supercommand.error):
                    # We rewind the origin scanner, so that errors found
                    # in generated subcommands can be recovered
                    command.origin_scanner.rewind()
                    command.origin_scanner.toggle_breakpoint()
                if supercommand and supercommand.subcommands:
                    # the most recent command from our origin
                    # has subcommands.  This means that it's our
                    # supercommand, rather than us having been
                    # created by the parser (like because of a
                    # dedention) It gets to have our error, too
                    supercommand.error = command.error
        except KeyboardInterrupt as ki:
            self.quit()
        except Exception as e:
            if command:
                self.handle_interpret_command_exception(e, command)
            else:
                raise

    def quit(self):
        self.parser.scanner = self.parser.interactive_scanner
        self.interactivity_enabled = False

        # Close off all the leftover scopes
        commands = self.parser.children or []
        scope = sum(command.scopechange for command in commands if command.usable)

        # At this point, the only scanner we care about is the
        # subcommand
        self.parser.scanner = self.parser.subcommand_scanner

        # Delete file scanners
        for scannername, scanner in self.parser.scanners.items():
            if scanner.name not in ('<interactive>', '<subcommand>'):
                del self.parser.scanners[scannername]

        # If there are scopes open, close them
        if scope:
            self.parser.subcommand_scanner.addline([
                "End %s" % command.verb.type for command in reversed(commands[-1].scopes)])
            self.handle_commands()

    def handle_commands(self):
        code = ''
        for command in self:
            if command:
                self.handle_output(command)
        else:
            self.parser.scanner = self.parser.interactive_scanner

    def run(self):
        exception = None
        try:
            first = True
            while first or self.interactivity_enabled:
                first = False
                self.handle_commands()
        except (Exception, KeyboardInterrupt) as e:
            import traceback
            print traceback.format_exc()
        finally:
            self.quit()

    def setup(self):
        """
        Sets up the callables for the different parser classes, based
        on the defaults and callables dicts in the class.
        """

        for mycls in reversed(type(self).__mro__):
            if issubclass(mycls, VisionInterpreter):
                # Set up tokens
                for tokenizer, tokens in getattr(mycls, 'tokens', {}).items():
                    if not hasattr(tokenizer, 'tokens'):
                        tokenizer.tokens = {}
                    tokenizer.tokens.update(tokens)

                # Set up default_factories
                for cls, factories in getattr(mycls, 'defaults', {}).items():
                    for callable_type, default in factories.items():
                        cls.set_default(callable_type, default)

                # Set up callables
                for cls, callables in getattr(mycls, 'callables', {}).items():
                    for callable_type, activities in callables.items():
                        cls.add_callables(callable_type, activities)

    def scroll(self, x=0, y=0, ele=None):
        """
        Scroll the given element to put its upper left at the given
        coord, in its coordinate system.  If ele tests False, scroll the
        current window.
        """
        x = max(x, 0)
        y = max(y, 0)
        if not ele:
            self.webdriver.execute_script("window.scroll(arguments[0], arguments[1]);", x, y)
        else:
            self.webdriver.execute_script("""
                arguments[0].scrollLeft = arguments[1];
                arguments[0].scrollTop = arguments[2];""",
                ele, x, y)

    @property
    def viewport(self):
        return self.webdriver.execute_script("return {'width': window.innerWidth, 'height': window.innerHeight};")

    def center_element(self, el, parent_el=None, horizontal=True, vertical=True):
        """
        If given a webdriver element, arrange for it to be centered on
        the screen.  There are horizontal and vertical flags that
        indicate which axis on which to center.

        If the element has ancestor elements that are scrollable, it
        will do this recursively.

        el - the WebElement to center
        parent_el - the parent WebElement in which to center el.  If
        this is None, we find all ancestors, if False, we center inside
        the window itself
        """
        if parent_el is None:
            # We weren't given a parent, so we need to get all parents
            # that have scrollbars
            scroll_parents = self.webdriver.execute_script("""
                var parent = arguments[0].parentNode;
                var parents = [];
                while(typeof(parent) !== 'undefined' && parent !== null && parent.tagName.toLowerCase() !== 'body' && parent.tagName.toLowerCase() !== 'html'){
                    if(
                    typeof(parent.scrollHeight) !== 'undefined' &&
                        typeof(parent.scrollWidth) !== 'undefined' &&
                        typeof(parent.clientHeight) !== 'undefined' &&
                        typeof(parent.clientWidth) !== 'undefined'){
                        // This node might have scrollbars
                        var overflow_x = window.getComputedStyle(parent).getPropertyValue('overflow-y');
                        var overflow_y = window.getComputedStyle(parent).getPropertyValue('overflow-x');
                        if((overflow_x !== 'visible' && overflow_x !== 'hidden' && parent.scrollWidth > parent.clientWidth) ||
                           (overflow_y !== 'visible' && overflow_y !== 'hidden' && parent.scrollHeight > parent.clientHeight))
                        {
                            // It does have scrollbars, keep it.
                            parents.unshift(parent);
                        }
                    }
                    parent = parent.parentNode;
                }
                return parents;""", el)
            for parent, child in zip([False] + scroll_parents, scroll_parents + [el]):
                self.center_element(child, parent, horizontal=horizontal, vertical=vertical)
        else:
            # Center inside the window
            viewport = parent_el.size if parent_el else self.viewport
            viewport_location = parent_el.location if parent_el else {'x': 0, 'y': 0}
            middle = [el.location['x'] + el.size['width'] / 2 - viewport_location['x'], el.location['y'] + el.size['height'] / 2 - viewport_location['y']]
            points = [max(0, middle[0] - viewport['width'] / 2), max(0, middle[1] - viewport['height'] / 2)]
            self.scroll(
                x=points[0] if horizontal else self.webdriver.execute_script("return arguments[0].scrollLeft;", parent_el) if parent_el else self.webdriver.execute_script("return window.scrollX;"),
                y=points[1] if vertical else self.webdriver.execute_script("return arguments[0].scrollTop;", parent_el) if parent_el else self.webdriver.execute_script("return window.scrollY;"),
                ele=parent_el)

        return el

    @property
    def flags(self):
        self.flags = getattr(self, '_flags', collections.OrderedDict())
        return self._flags

    @flags.setter
    def flags(self, flags):
        self._flags = flags

    @property
    def upload_dir(self):
        return os.path.abs_path('upload')

if __name__ == "__main__":
    interpreter = VisionInterpreter(
        verbose=False,
        scope_after_error=False,
        maximum_wait=15,
        acceptable_wait=3)
    parser=InteractiveParser(interpreter=interpreter)
    interpreter.run()

