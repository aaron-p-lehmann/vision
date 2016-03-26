import os.path
import sys
import visioninterpreter

def main():
    interpreter = visioninterpreter.InteractiveInterpreter(
        verbose=False,
        maximum_wait=15,
        acceptable_wait=3)
    parser=visioninterpreter.InteractiveParser(interpreter=interpreter)
    interpreter.run()
