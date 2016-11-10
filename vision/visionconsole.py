import visioninterpreter
import argparse
import os
import os.path
import sys
import pkg_resources

def get_args(arguments=None):
    argv = [arg for arg in sys.argv[1:] if arg not in ('-h', '--help')]

    parser = argparse.ArgumentParser(
        description="An interpreted language for writing Selenium tests in English.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument(
        '--remote',
        help="The url of the remote webdriver hub, if a remote is to be used")
    parser.add_argument(
        '--browser',
        default="chrome",
        choices=visioninterpreter.VisionInterpreter.browsers.keys(),
        type=str.lower,
        help=("The type of browser to use.  Firefox has support built in"
            "to webdriver, and thus requires no downloads beyond the browser"
            "itself.  Other browsers require third-party helper programs."))
    parser.add_argument(
        '--debug',
        help='Sets vision to print tracebacks when commands fail',
        action='store_true',
        default=False)
    parser.add_argument(
        '--acceptable-time',
        type=float,
        help='If a command takes longer than this (in seconds) to run, a warning is generated',
        default=3)
    parser.add_argument(
        '--maximum-time',
        type=float,
        help='If a command takes longer than this (in seconds) to run, the command fails',
        default=15)
    parser.add_argument(
        '--timing',
        help='Sets vision to print timing information when a command takes longer than acceptable-time',
        action='store_true',
        default=False)
    parser.add_argument(
        '--root-test-directory',
        help='The directory in which all the tests and asset directories exist',
        default=os.path.abspath(os.getcwd()))
    parser.add_argument(
        '--root-url',
        help='The base url from which to start the test.',
        default="")
    if hasattr(arguments, 'testfiles'):
        parser.add_argument(
            '--stop-at',
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
    if hasattr(arguments, 'root_test_directory'):
        # this is the second pass
        parser.add_argument(
            '--upload-directory',
            help='The directory where files to be uploaded will be found.  This is relative to %s.  If it does not exist, it will be created.' % arguments.root_test_directory,
            default='')
        parser.add_argument(
            '--test-directory',
            help='The directory where files to be test files will be found.  This is relative to %s.  If it does not exist, it will be created.' % arguments.root_test_directory,
            default='')
        parser.add_argument(
            '--results-directory',
            help='The directory where result files will be written.  This is relative to %s.  If it does not exist, it will be created.' % arguments.root_test_directory,
            default='')
    if hasattr(arguments, 'results_directory'):
        parser.add_argument(
            '--screenshot-directory',
            help='The directory where screenshots files will be written.  This is relative to %s.  If it does not exist, it will be created.' % arguments.results_directory,
            default='')
    if hasattr(arguments, 'test_directory'):
        # this is the third pass
        argv = sys.argv[1:]

        parser.add_argument(
            'testfiles',
            help='The files to be loaded, in order.  These will be relative to %s.' % os.path.join(arguments.root_test_directory, arguments.test_directory),
            nargs='*')

    arguments, remainder = parser.parse_known_args(argv)
    arguments.root_test_directory = os.path.expanduser(
        arguments.root_test_directory)
    return arguments

def main(interpreter_type=visioninterpreter.VisionInterpreter, parser_type=visioninterpreter.InteractiveParser,program="vision"):
    # Print the version
    print "%s %s" % (
        program.capitalize(),
        pkg_resources.get_distribution(program.lower()))

    # Get the arguments, in four passes
    arguments = get_args()
    arguments = get_args(arguments)
    arguments = get_args(arguments)
    arguments = get_args(arguments)

    # Make the necessary directories, if they don't exist
    interpreter = interpreter_type(
        verbose=False,
        debug=arguments.debug,
        timing=arguments.timing,
        maximum_wait=arguments.maximum_time,
        acceptable_wait=arguments.acceptable_time,
        base_url=arguments.root_url,
        tests_dir=os.path.join(
            arguments.root_test_directory,
            arguments.test_directory),
        upload_dir=os.path.join(
            arguments.root_test_directory,
            arguments.upload_directory),
        screenshot_dir=os.path.join(
            arguments.root_test_directory,
            arguments.results_directory,
            arguments.screenshot_directory),
        results_dir=os.path.join(
            arguments.root_test_directory,
            arguments.results_directory),
        browser_options={
            'remote': arguments.remote,
            'type': arguments.browser})
    parser=parser_type(
        interpreter=interpreter)

    try:
        # Try to make the webdriver, and catch failures with a vague
        # message, then exit.  Later, we'll figure out how to make the
        # message more informative.
        interpreter.webdriver
    except Exception as e:
        sys.exit("Something went wrong with setting up the Selenium "
            "webdriver.  Make sure you have the right version of the browser "
            "you chose (%s), and the driver program (%s)." % (
                arguments.browser, {
                    "chrome": "chromedriver",
                    "firefox": "geckodriver",
                    "internetexplorer": "iedriver"}))
    parser.interactive_scanner.addline([
        'Load test "%s"' % test for test in reversed(arguments.testfiles)])
    if getattr(arguments, 'stop_at', None):
        # Make sure every breakpoint has a filename.  If none was
        # provided, then use the most recent file
        breakpoints_dict = {}
        for breakpoint in arguments.stop_at:
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

    if arguments.root_url:
        parser.subcommand_scanner.addline([
            'Navigate to "%s"' % arguments.root_url])
        parser.scanner=parser.subcommand_scanner
    try:
        interpreter.run()
    finally:
        interpreter.quit()

if __name__ == "__main__":
    main()
