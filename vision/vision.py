import visioninterpreter
import argparse

def main():
    parser = argparse.ArgumentParser(
        description="An interpreted language for writing Selenium tests in English.")
    parser.add_argument(
        '--remote',
        help="The url of the remote webdriver hub, if a remote is to be used")
    parser.add_argument(
        '--browser',
        default="firefox",
        choices=visioninterpreter.VisionInterpreter.browsers.keys(),
        type=str.lower,
        help=("The type of browser to use.  Firefox has support built in"
            "to webdriver, and thus requires no downloads beyond the browser"
            "itself.  Other browsers require third-party helper programs."))
    arguments = parser.parse_args()

    interpreter = visioninterpreter.VisionInterpreter(
        verbose=False,
        maximum_wait=15,
        acceptable_wait=3,
        browser_options={
            'remote': arguments.remote,
            'type': arguments.browser})
    parser=visioninterpreter.InteractiveParser(interpreter=interpreter)
    try:
        interpreter.run()
    finally:
        interpreter.quit()
