import visioninterpreter
import argparse
import os
import os.path
import sys

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
    if hasattr(arguments, 'root_test_directory'):
        # this is the second pass
        parser.add_argument(
            '--upload-directory',
            help='The directory where files to be uploaded will be found.  This is relative to %s.  If it does not exist, it will be created.' % arguments.root_test_directory,
            default='upload')
        parser.add_argument(
            '--test-directory',
            help='The directory where files to be test files will be found.  This is relative to %s.  If it does not exist, it will be created.' % arguments.root_test_directory,
            default='tests')
        parser.add_argument(
            '--results-directory',
            help='The directory where result files will be written.  This is relative to %s.  If it does not exist, it will be created.' % arguments.root_test_directory,
            default='results')
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

def main(interpreter_type=visioninterpreter.VisionInterpreter, parser_type=visioninterpreter.InteractiveParser):
    # Get the arguments, in three passes
    arguments = get_args()
    arguments = get_args(arguments)
    arguments = get_args(arguments)

    # Make the necessary directories, if they don't exist
    interpreter = interpreter_type(
        verbose=False,
        debug=arguments.debug,
        timing=arguments.timing,
        maximum_wait=arguments.maximum_time,
        acceptable_wait=arguments.acceptable_time,
        tests_dir=os.path.join(
            arguments.root_test_directory,
            arguments.test_directory),
        upload_dir=os.path.join(
            arguments.root_test_directory,
            arguments.upload_directory),
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
    try:
        interpreter.run()
    finally:
        interpreter.quit()
