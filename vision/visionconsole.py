import visioninterpreter
import argparse
import os
import os.path
import sys
import pkg_resources
import selenium
import time
import urlparse

def get_args(arguments=None, parse_help=True):
    parser = argparse.ArgumentParser(
        description="An interpreted language for writing Selenium tests in English.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        add_help=parse_help)
    parser.add_argument(
        'testfiles',
        help='The files to be loaded, in order.  These will be relative to %s.' % os.getcwd(),
        nargs='*')
    parser.add_argument(
        '--browser',
        default="chrome",
        choices=visioninterpreter.VisionInterpreter.browsers.keys(),
        type=str.lower,
        help=("The type of browser to use.  Firefox has support built in"
            "to webdriver, and thus requires no downloads beyond the browser"
            "itself.  Other browsers require third-party helper programs."))
    parser.add_argument(
        '--remote',
        help=(
            "The url of the remote webdriver hub, if a remote is to be "
            "used.  This will default to using port 4444 and a path of "
            "/wd/hub, because that is the path Selenium hubs run on.  It "
            "will ALWAYS use http as the protocol, because webdrivers don't "
            "support anything else."))
    parser.add_argument(
        '--start-url',
        help='The url from which to start the test.',
        default="")
    if hasattr(arguments, 'testfiles'):
        parser.add_argument(
            '--breakpoint',
            help=(
                'Sets breakpoints in files to be loaded.  The format is '
                '"[filename:]number or keyword".  If filename is provided, '
                'breakpoints are set in that filename.  If it is not, the '
                'breakpoints are set in the first file given on the command '
                'line.  If a number is given, the breakpoint is set at that '
                'line number of the file.  If a keyword is given, breakpoints '
                'are set at every line in that file that use that keyword.  '
                'This argument is only available if testfiles are provided.  '
                'This arguments can be given multiple times to set more than '
                'one set of breakpoints.  The files available to have '
                'breakpoints placed are: %s' % arguments.testfiles),
            action='append')
    parser.add_argument(
        '--debug',
        help='Sets vision to print tracebacks when commands fail',
        action='store_true',
        default=False)
    parser.add_argument(
        '--timing',
        help='Sets vision to print timing information when a command takes longer than acceptable-time',
        action='store_true',
        default=False)
    parser.add_argument(
        '--warning-time',
        type=float,
        help='If a command takes longer than this (in seconds) to run, a warning is generated',
        default=3)
    parser.add_argument(
        '--maximum-time',
        type=float,
        help='If a command takes longer than this (in seconds) to run, the command fails',
        default=15)
    parser.add_argument(
        '--interactive-warning-time',
        type=float,
        help='If a command takes longer than this (in seconds) to run in interactive mode, a warning is generated',
        default=1)
    parser.add_argument(
        '--interactive-maximum-time',
        type=float,
        help='If a command takes longer than this (in seconds) to run in interactive, the command fails',
        default=5)

    arguments, remainder = parser.parse_known_args()
    if arguments.remote:
        # provide proper default protocol and path for connecting to a
        # selenium hub
        try:
            protocol, url = arguments.remote.split("://", 1)
        except ValueError as ve:
            # there is not protocol provided, use 'http'
            protocol, url = 'http', arguments.remote
        finally:
            # Selenium doesn't support any protocol except for http
            protocol = "http"
        try:
            server, path = url.split("/", 1)
        except ValueError as ve:
            # there's no path, use '/wd/hub'
            server, path = url, '/wd/hub'
        try:
            server, port = server.split(":")
        except ValueError as ve:
            # there's no port, use '4444'
            server, port = server, "4444"
        try:
            filepath, querystring = path.split("?", 1)
        except ValueError as ve:
            # there's no querystring, use ''
            filepath, querystring = path, ""
        arguments.remote = urlparse.urlunparse([protocol, server + ":" + port, path] + ([""] * 3))

    return arguments

def main(interpreter_type=visioninterpreter.VisionInterpreter, parser_type=visioninterpreter.InteractiveParser, programs=("vision",)):
    # Print the version
    for program in programs:
        dist_info = pkg_resources.get_distribution(program.lower())
        print '-'.join([program, dist_info.version])

    # Get the arguments, in five passes
    arguments = get_args(parse_help=False)
    arguments = get_args(arguments)

    # Make the necessary directories, if they don't exist
    interpreter = interpreter_type(
        verbose=False,
        debug=arguments.debug,
        timing=arguments.timing,
        base_url=arguments.start_url,
        browser_options={
            'remote': arguments.remote,
            'type': arguments.browser})
    parser=parser_type(
        interpreter=interpreter,
        interactive_maximum_time=arguments.interactive_maximum_time,
        interactive_allowable_time=arguments.interactive_warning_time,
        maximum_time=arguments.maximum_time,
        allowable_time=arguments.warning_time)

    try:
        # Try to make the webdriver, and catch failures with a vague
        # message, then exit.  Later, we'll figure out how to make the
        # message more informative.
        found_node = False
        while not found_node:
            try:
                if arguments.remote:
                    print (
                        "Starting a driver on a remote node.  If we "
                        "can't connect to the address you gave (%s), we'll "
                        "wait indefinitely for one to be available there") % arguments.remote
                interpreter.webdriver
                found_node = True
            except selenium.common.exceptions.WebDriverException as wde:
                timeout_msg = "Error forwarding the new session"
                if arguments.remote and timeout_msg in str(wde):
                    # if we failed due to timeout 
                    # sleep for 5 seconds, then try again
                    time.sleep(5)
                else:
                    # It's some other kind of exception, raise it
                    raise
    except Exception as e:
        msg = ("Something went wrong with setting up the Selenium "
            "webdriver.  Make sure you have the right version of the browser "
            "you chose (%s), and the driver program (%s).") % (
                arguments.browser, {
                    "chrome": "chromedriver",
                    "firefox": "geckodriver",
                    "internetexplorer": "iedriver"})
        if arguments.debug:
            print msg
            raise
        else:
            sys.exit(msg)

    parser.interactive_scanner.addline([
        'Load test "%s"' % test for test in reversed(arguments.testfiles)])
    if arguments.testfiles:
        if getattr(arguments, 'breakpoint', None):
            # Make sure every breakpoint has a filename.  If none was
            # provided, then use the most recent file
            breakpoints_dict = {}
            for breakpoint in arguments.breakpoint:
                filename, breakpoint = breakpoint.split(':', 1) if len(breakpoint.split(':', 1)) > 1 else (arguments.testfiles[0], breakpoint)
                filename = filename if filename.endswith(".vision") else filename + ".vision"
                breakpoints_dict[filename] = breakpoints_dict.get(filename, set([]))
                breakpoints_dict[filename].update([breakpoint])

            # Now add the commands to add the breakpoints.
            for filename, breakpoints in breakpoints_dict.items():
                parser.interactive_scanner.addline([
                    'Break "%s"' % ":".join([filename, breakpoint]) for
                    breakpoint in breakpoints])
        else:
            # There are no breakpoints, add a finish to the scanner
            # the test will run to completion
            parser.interactive_scanner.addline(["Finish"])

    if arguments.start_url:
        parser.subcommand_scanner.addline([
            'Navigate to "%s"' % arguments.start_url])
        parser.scanner=parser.subcommand_scanner
    try:
        interpreter.run()
    finally:
        interpreter.quit()

if __name__ == "__main__":
    main()
