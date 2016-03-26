Vision is an interpreted programming language that allows one to specify selenium tests using a subset of English.

# FAQ

## Why should I write my tests in Vision, rather than with one of the Selenium bindings?

* Vision tests are easier to read, since they are in English.  Those that do not know programming language can still read a Vision test.  While it is possible to make a Vision test hard for a non-programmer, it is also straightforward to make them easy to read.
* Vision tests are easier to write and maintain.  The interactive interpreter allows for the test author to see if the command will do what he intended as he is writing it, rather than running the test and finding out then.
* Vision tests are better documentation.

## Why should I write my tests in Python, rather than with Vision?

Vision does not support looping, functions, logical branching, or the general variable manipulation abilities of most programming languages.  This is intended, as a test should not have to alter behavior based on situations.  They should be step by step instructions.

# Installation

Vision requires Python 2.7 and pip.  I suggest using at least 2.7.9, so that you don't have to install pip yourself, but get it for free with Python.  Once you've installed Python and pip, run the following command:

	pip install vision

That will install Vision and its dependancies and make a binary in your path so you can treat Vision like any other program.	
# Language Grammar and Important Concepts 

This section will cover the grammar of the language and explain the various types of keywords.  There are six major types of keywords: Verbs, Nouns, Ordinals, Positionals, Sugar, and Variables.  Nouns and Verbs can be modified with Literals, Ordinals, and Positionals.  These are all organized into Commands.

## Commands

A command is one line of Vision.  It has one and only one Verb, any number of Nouns, and an optional Variable.  It may or may not have Literals, Ordinals, or Positionals, depending on the Nouns, Verbs, and Variables involved.

## Literals

A literal is plain text.  They are used in labels.  For example, in the following code, "Save" is a literal.

    Click the "Save" button

Literals can be surrounded by single quotes ('), double quotes ("), and angle brackets (<>).  Single and double quotes are equivalent, but angle brackets are different, and denote a file literal.

### File Literals

A file literal is a literal that is loaded from a file that is named by the string within the angle brackets.  This is useful to provide multiline literals.  This string can be alphanumeric characters, the underscore (_), and the period (.).  The file is searched for in the uploads directory of the current working directory.

In the following line, the label of the button would be pulled from the 'save_file' file, in the current working directory.

    Click the <save_file> button

If the file doesn't exist, and Vision does not allow interactive mode (such as after typing the 'Finish' command), this is will be recorded as an error.  If the file doesn't exist and Vision is allowing interactive mode, then the user is allowed to create the file inline, or accept the error.  Follows are some examples of use, on a Windows machine that was running in the Y:\prj\tutorial.  First, we'll accept the error.

    global:1:  Navigate to <navigate_url_file>
    In 'Navigate to <navigate_url_file>', could not read <Y:\prj\tutorial\upload\navigate_url_file>
    You can:
        (C)reate the file
        or (A)ccept the error.
    (C)reate or (A)ccept? A
    Navigate to <navigate_url_file> - ERROR (1.565000 seconds)
    [Errno 2] No such file or directory: 'Y:\\prj\\tutorial\\upload\\navigate_url_file'

Since Vision is in interactive mode, we get a chance to fix it.  This time, we'll create the file.

    global:2:  Navigate to <navigate_url_file>
    In 'Navigate to <navigate_url_file>', could not read <Y:\prj\tutorial\upload\navigate_url_file>
    You can:
        (C)reate the file
        or (A)ccept the error.
    (C)reate or (A)ccept?C
    Line 1 of <Y:\prj\tutorial\upload\navigate_url_file>, type <End of navigate_url_file> to stop input:    http://www.google.com
    Line 2 of <Y:\prj\tutorial\upload\navigate_url_file>, type <End of navigate_url_file> to stop input:    <End of navigate_url_file>

When we typed '`<End of navigate_url_file>`', Vision stopped prompting for input, wrote the file, and passed the contents on.

## Ordinal

An Ordinal is something like 1st, 2nd, and so forth.  They can be used with all Nouns and some Verbs as a sort of "escape hatch".  When there is no better way to uniquely identify a widget on the screen or an option in a dropdown, you can use an ordinal to have vision count through the context.  These should be used sparingly, as using them too often can make a test very hard to read unless one is staring at the browser.  The following is an example:

    Click the 2nd "Yes" radio button

## Positional

Like Ordinals, Positionals are a sort of escape hatch for when the obvious label for a widget has no relationship in the DOM to it.  This is poor form, in my opinion.  If you did this, you should fix it.  These are actually pretty flaky, so they should be avoided.  I've included them here for completeness.

    Select "Amoxicillin" from the "Medicine" dropdown after the "Prescriptions" text

## Verb

Verbs represent actions taken on the browser (e.g. clicking with the 'Click' verb), on the result file (creating a collapsible section with the 'Test' verb), or the test itself (saving the test with the 'Save test' verb).  Depending on the Verb, it might take a Literal or an Ordinal.  If it does, they must appear after the Verb, and before anything else.

## Noun

Nouns represent widgets on the web page.  They can take Literals, Ordinals, or Positionals.  If they do, they must come after the Noun, and before anything else, unless the special word "the" is used.  If "the" is used, they must come after the "the", and before the Noun.  For example, the following two lines are equivalent.

    Click the "Save" button
    Click button "Save"

### Chaining Nouns

More than one Noun can be chained together in a command.  If they are, each Noun is assumed to contain the one before it.  For example, the following code will first find the "Login" table, then find the "Username" textfield inside that table, then type "selenium" into the textfield.

    Type "selenium" in the "Username" textfield in the "Login" table

In many cases, that will be equivalent to the following line, but if there are many "Username" textfields on the page, it will be more precise and (possibly) faster.

    Type "selenium" in the "Username" textfield

### Scopes

Noun chains are inherited inside of a test scope.  The following will find the "Login" table, then look inside it to find the "Username" textfield and type "selenium" in it.  Then it will look in the table for the "Password" textfield and type "selenium" in it.

    Test the "Login" table
        Type "selenium" in the "Username" textfield
        Type "selenium" in the "Password" textfield

Note that the "Login" table is only found once.  This could give the test a speed boost, and will definitely make it easier to read, at least to those who have done some programming before.  Strangely, non-programmers have sometimes had difficulty with the concept of context, before.  Know your audience.

### Finding Nouns

Nouns are found on the page using some pretty complex logic which varies based on what kind of Noun is desired.  Unless specified elsewhere, the order of searching is:

* The label is in the same block
* The label is in a previous cell on the row
* The label is on the previous row
* The label is in the legend of a containing table

In the case of nested cells, rows, etc.  The search will take place in the most specific first.  This search order will first be applied looking for strings that are exact matches, then applied again looking for strings that begin with the literal the search is based on.  This means that if a page has the a button marked `Save me` on it followed by a button marked `Save`, the phrase `the 1st "Save" button` will find the second button, since exact matches are preferred.

### Finding Nouns using html attributes or xpaths

It is possible to specify a noun using html attributes or xpaths, using the following syntax:

    {id=blah}
    {xpath=//a[text()='Blah']}

These nouns have access to basic commands, but not commands that are noun-specific, since Vision doesn't know what type of Noun it's dealing with.  Also, if Ordinals are a dirty escape hatch, this is trebly so.  If you find yourself having to do this to get to something on your page, you should REALLY consider rewriting your page, or adding keywords to Vision and submitting pull requests.

### Timing

Vision will search for a noun for a specific amount of time before giving up.  By default, that amount of time is 15 seconds.  This can be changed by using the `within` keyword.  For example, the following code will search for 30 seconds before giving up.

    Click the "Submit" button within "30"

== Variable ==

It is possible to label a command to allow the Noun part of it to be found later using the 'context' keyword. A variable is defined using the 'as' keyword.  So a Variable defined by this:

    The "Layout Manager" table should exist as "Layout Manager table"

Could be used later like this:

    Click the "Edit" link in the "SELENIUM" row in the "Layout Manager table" context

In those examples, the "Layout Manager" table would only be found once.  This can be handy for readability, if you want to interact with a widget outside of your current scope (e.g. you've clicked a button in a table that causes changes outside the table, and you want to verify it). 

    Test the "Users" table
		Click the "Delete" button in the "Fred" row
		The "Fred" row should not exist
		The "Deleted user 'Fred'" text should exist in the "global" context

It can also be helpful if the test is inside a context, and does something that opens up a new window that it needs to interact with.  The new window will not be in any pre-existing contexts, after all.

	Test the "Users" table
		Click the "Edit" button in the "Ethyl" row
		Switch to the "Edit User: Ethyl" window
		Test the "User Info" box in the "global" context
			Type "E" in the "Middle Initial" textfield
			Type "Mertz" in the "Last Name" textfield
		Close the "Edit User: Ethyl" window
		Switch to the "Base Window" window
		The "Mertz" text should exist in the "Last Name" cell in the "Ethyl" row
					
This can also be nice if you know you are going to be switching back and forth on the same page a lot, because Vision caches the id of a noun, once it's been found.  This means that after you've found something on a page once, you can "bookmark" it for use later rather than having to refind it.

## Sugar

Sugar is words, whitespace, and puctuation that is allowed by Vision so that tests can read like English.  Vision will completely disregard sugar, which means it can appear anywhere outside of a Literal, as many times as necessary.  The following things are considered Sugar.

* to
* in
* for
* with
* new
* item
* from
* on
* into
* it
* and get
* spaces and tabs other than indents (a group of 4 spaces at the beginning)
* any character other than alphanumeric, underscore, single and double quotes, and angle brackets

## Indentation

If Vision is reading a test from a file, it uses indentation to indicate what scope it is in.  Each use of the "Test" keyword requires another layer of indentation.  De-denting indicates the closing of scopes.  An indentation is 4 spaces.  Indentations go at the beginning of the the line, anywhere else in the line they are sugar, and are ignored.

# Keyword reference

Vision supports extensions to the keyword set, but this documentation will only cover.

## Nouns

A noun represents a widget on the page.

### Alert

This is a popup generated by the browser or by JavaScript.  It can be used with the `accept`, `dismiss`, `should exist`, and `should not exist` Verbs, and takes an optional Literal argument.  If provided, the Alert's message will be expected to start with the Literal.  Here are some examples of use:

    Accept the "Could not find ActiveX control" alert
    Dismiss the alert
    The alert should exist
    The alert should not exist

It is important to realize that if an alert is open, no other widgets can be found, so if your test causes one to be generated, you must accept the alert with Vision (not manually).

### Box

This is an html fieldset, identified by the text in its label.  It's mainly intended to be used as the context for a 'Test' or as the context of another noun in the command

### Button

This is a button element, and input of type 'button' or 'submit', or a submit element.  It can be used with the 'click', 'capture', 'should exist', and 'should not exist' Verbs, and takes an optional Literal and optional Ordinal argument.  If provided, the Button's value will be expected to begin with the Literal.  Here are some examples of use.

    Click the button
    Click the 2nd button
    Click the "Save" button
    Click the 2nd "Save" button
    Capture the button
    The button should not exist
    The button should exist

### Context

This matches whatever element is marked by the context given by the passed Literal.  Contexts are set up with the "As" keyword.  There is a special built-in "global" context, which refers to the whole page.

    Capture the "global" context

### Checkbox

A checkbox is an input of type 'checkbox'.  It can be used with the 'click', 'capture', 'should exist', 'should not exist', 'should be checked', and 'should not be checked' Verbs, and it takes an optional Literal and an optional Ordinal.  If provided, the checkbox will be expected to have a label that starts with the label.  A checkbox's label is found by looking in the following places, in this order:

* The checkbox's html label.
* The text to the checkbox's immediate left.
* The table cell preceding the table cell in which the checkbox is in, if the checkbox is in a cell.  If the checkbox is in multiple nested cells, they are searched closest first.
* The legend of the textbox's fieldset, if any.  If the checkbox is a part of multiple fieldsets, they are searched closest first.

In each case, and exact match to the Literal given (if any) is preferred.  If an Ordinal is given, all of the matches are found, and the ordinal is used to determine which to select.  Here are some examples:

    Click the checkbox
    Click the 2nd checkbox
    Click the "Red" checkbox
    Click the 2nd "Red" checkbox
    Capture the "Blue" checkbox

### Dropdown

A dropdown is a select widget.  It can be used with the 'select', 'capture', 'should exist', 'should not exist', 'should contain', 'should contain exactly', and 'should not contain' Verbs, and takes an optional Literal and an optional Ordinal.  If a Literal is provided, the label of the dropdown will be expected to begin with the Literal.  Here are some examples.

    Select "Fred" from the dropdown
    Capture the dropdown

### Image

An Image is an <img> widget. It can be used with the 'click', 'capture', 'should exist' and 'should not exist' Verbs, and takes an optional Literal and an optional Ordinal. If a Literal is provided, the alt of the image will be expected to begin with the Literal.
Here are some examples.

    Click the 'Help' image
    The 'Logo' image should exist

### Link

A link is an a tag.  It can be used with the 'click', 'capture', 'should exist', 'should not exist', 'should contain', 'should contain exactly', and 'should not contain' Verbs, and takes an optional Literal arguments and an optional Ordinal arguments.  If a Literal is provided, the text of the link is expected to begin with the Literal.  Here are some examples.

    Click the "Next" link
    The "Next" link should exist

### Radio button

A radio button is an input of type 'radio'.  It can be used with the 'click', 'capture', 'should exist', 'should not exist', 'should be checked', and 'should not be checked' Verbs, and takes an optional Literal argument and an optional Ordinal argument.  If an ordinal argument is provided, the radio button is expected to be labeled with a string starting with the literal.  A radio button's label is found by looking in the following places, in this order:

* The html label of the radio button.
* The text to the radio button's immediate right.
* The table cell preceding the table cell in which the radio button is in, if the radio button is in a cell.  If the radio button is in multiple nested cells, they are searched closest first.
* The legend of the radio button's fieldset, if any.  If the radio button is a part of multiple fieldsets, they are searched closest first.

In each case, and exact match to the Literal given (if any) is preferred.  If an Ordinal is given, all of the matches are found, and the ordinal is used to determine which to select.  Here are some examples.

    Click the 2nd radio button
    Click the "Red" radio button
    The radio button should exist

### Text

A text is a block on the page that begins with the given literal.  It can be used with the 'click', 'capture', 'should exist', 'should not exist', 'should contain', 'should contain exactly', and 'should not contain' Verbs, and takes a mandatory Literal and an optional Ordinal arguments.  It is most often used to verify messages saying that something has succeeded, although it is occasionally used when someone has made his own link by adding an onclick to a span.  Here are some examples.

    The "Setting modified successfully" text should exist
    Click the "Visits" text
    
If you are using br tags to break up your text, not only are you a bad person who should feel bad, you won't be able to test for text after the br tags.

### Textarea

This is a textarea widget.  It can be used with the 'clear', 'click', 'type', 'capture', 'replace', 'should exist', 'should not exist', 'should contain', 'should contain exactly', and 'should not contain' Verbs, and takes an optional Literal and an optional Ordinal.  If a Literal is provided, its label is expected to begin with the Literal.  It will be frequently used with file literals, as they are how one uses multi-line literals.   Here are some examples.

    Type <layout_file> in the "Layout Editor" textarea
    Type "Single line of text" in the "Comment" textarea
    Clear the "Comment" textarea

### Textfield

A textfield is an input widget without a type or with the 'text', 'password', or 'email' types.  It can be used with the 'clear', 'type', 'capture', 'replace', 'should exist', 'should not exist', 'should contain', 'should contain exactly', and 'should not contain' Verbs, and takes an optional Literal arguments and an optional Ordinal argument.  If a literal is provided, its label is expected to begin with the Literal.  Here are some examples.

    Type "Aaron is great" in the textfield
    Type "Aaron is great" in the "What do you think about Aaron" textfield
    Clear the textfield

### Frame

A frame is a frame (or iframe) in the browser.  It can be used with the 'switch' Verb, and takes a Literal or an ordinal.  It is used in tests to switch focus to a frame so that Vision can find elements within that frame.  Here is an example.

    Switch to the "mainwindow" frame
    Switch to the 2nd frame

### Window

A window is a browser window.  It can be used with the 'switch' or 'close' Verb.  It is used in tests to switch focus to a different browser window so that Vision can work with it.  Here is an example.

    Switch to the "WebChart: Orders" window
    Close the window

### Cell

A cell is a td in a table.  It can be used with the 'capture', 'should exist', 'should not exist', 'should contain', 'should contain exactly', 'should not contain', and 'test' Verbs, and takes an optional Literal argument and an optional Ordinal argument.  If a Literal is provided, it is expected to exist in the text of the th element for the column this cell is in.  This noun MUST be followed in noun context by a 'row'. Here is an example.

    The "Age" cell in the "MIE-10019" row should contain exactly "71"
    
This will find the first row with a cell that starts with "MIE-10019" or has an input with visible text starting with "MIE-10019", then find the th element in the table that starts with "Age", then find the most precise td element underneath the point on the browser that is horizontally centered on the th and vertically centered in the row.

### Row

A row is a tr in a table.  It can be used with the 'capture', 'should exist', 'should not exist', 'should contain', 'should contain exactly', 'should not contain', and 'test' Verbs, and takes an optional Literal argument and an optional Ordinal argument.  If a Literal is provided, it is expected to either be the start of one of the cells, or be in a widget in one of the cells.  This Noun is often used to narrow the scope of searching for other nouns.  Here is an example.

    Click the "Edit" link in the "MIE-10019" row

### Table

This is a table.  It can be used with the 'capture', 'should exist', 'should not exist', 'should contain', 'should contain exactly', 'should not contain', and 'test' Verbs, and takes an optional Literal argument and an optional Ordinal argument.  If a Literal is provided, it is expected that the legend of the table starts with the Literal.  Tables are often used as the scope for test sections.  Here is an example.

    Test the "Layout Manager" table

### File input

This is an input for uploading files.  It is intended to be used with the 'enter file' verb.

    Enter file <myfile> in the "File uploader" file input

#### Selenium Verbs

These are the verbs of the basic Vision language that are a part of tests.  There is a seperate section for verbs that are directed at the interpreter.

### Should contain

This verb tests that the Literal provided exists in the Noun.  If the widget has a "value" attribute, the verb checks there.  Otherwise, it checks for text.  Here is an example.

    The "Quick View" link should contain "View"

### Should contain exactly

This verb tests that the Literal provided is a precise match for the Noun.  If the widget has a "value" attribute, the verb checks there.  Otherwise, it checks for text.  

This will fail, because it isn't a precise match.

    The "Quick View" link should contain exactly "View"

This would work, though.

    The "Quick View" link should contain exactly "Quick View"

### Should not contain

This verb tests that the Literal provided does not exist in the widget.  If the widget has a "value" attribute, the verb checks there.  Otherwise, it checks for text.  Here is an example.

    The "Quick View" link should not contain "racecar"

### Should exist

This verb tests for the existence of a widget.  This verb is used when it is important that a widget exists, but the test will not use it (often searching for text, or ensuring that an AJAX DOM change is done).  If the widget will actually be used, this test is superfluous.  Here is an example.

    The "Operation successful!" text should exist

### Should not exist

This verb tests that a widget does NOT exist.  Here is an example.

    The "Password expired" text should not exist

### Should be checked

This verb verifies that a checkbox or radio button is checked.  Here is an example.

    The "Cigarettes" radio button is checked

### Should not be checked

This verb verifies that a checkbox or a radio button is NOT checked.  Here is an example.

    The "Cigars" radio button is not checked

### Capture

In basic Vision, this is currently a no-op, and is there to speed test writing in plain Vision when making tests to be run in the extended keywordset I use at work.  In the future, I plan to give Vison the capability of making results files, and then this will take a screen capture, and crop it to only include the context the subject of this command.

### Clear

This clears a field that takes text input.  Here is an example.

    Clear the "Username" textfield

### Click

This clicks an element on the screen.  Here is an example.

    Click the "Save" button

### Close

This closes a window.  Here is an example.

    Close the window.

### Navigate

This navigates the window by entering text into the window's url field.  If the url does not begin with "http://" or "https://", it is prefaced with "https://".  If the verb is given a literal that starts with a question mark (?), then the current query string will be replaced with that.  Navigate can also be used with a link.  In that case, it enters the text in the link's href into the url.  Here are some examples.

    Navigate to "www.google.com"
    Navigate to "https://www.gmail.com"
    Navigate to the "E-Chart" link
    Navigate to "?f=layout&s=pat&module=Meaningful+Use&name=Meaningful+Use+Compliance&tabmodule=reports&t=Utilization&mu_debug=1"

### Select

This is used to select from a dropdown.  It takes a mandatory Literal and an optional Ordinal.  The text of the selected option is expected to begin with the Literal.  If an Ordinal is provided, it will be used to determine which match is selected.  Here are two examples.

    Select "Fred Mertz" from the "Flintstones and Mertzes" dropdown
    Select 2nd "Fred" from the "Flintstones and Mertzes" dropdown

### Switch

This switches the focus between different windows and different frames.  It takes a mandatory Literal, which is the start of the title of the window or id of the frame.  Here are two examples.

    Switch to the "mainwindow" frame
    Switch to the "WebChart: Encounters" window

### Type

This types text into a textfield or textarea.  Here are two examples.

    Type "You are" in the "Who is my sunshine?" textfield
    Type "You make me happy when skies are grey" in the "Why?" textarea

### Test

This starts a test scope.  It takes an optional Literal.  If a Literal is provided, that is the name of the scope.  If a Noun is used, the scope takes place within that noun.  If a Noun is provided that has a label, and no Literal is provided, than the label of the Noun is the name of the scope.  Here are some examples.

    Test "Test scope with no Noun"
        ...
    Test "Test scope with a Noun" in the "Layout Manager" table
        ...
    Test the "Layout Manager" table
        ...

### Accept

This accepts an alert window (clicks the "OK" button).  Here is an example.

    Accept the alert.

### Dismiss

This dismisses an alert window (clicks the "Cancel" button).  Here is an example.

    Dismiss the alert.

### Authenticate

This authenticates at a login alert.  Here is an example.

    Authenticate "user/password" the alert.

### Wait

This causes the interpreter to wait for the specified number of seconds.  It's a holdover from before the "within" keyword existed, and it's use is discouraged.

    Wait "60"

### Go back

This causes the interpreter to go back in the browser history.

    Go back

### Require

This tells the interpreter that another Vision script must have been run in order to continue.  It also allows a scope of code to be run in order to test that everything was successful.  For example:

    Require "somescript.vision"
        The "script is successful" text should exist

If somescript.vision has not been run, this will run it.  Then it will verify that the text exists.  Then it navigate back to whatever URL was displayed when the Require was first run.
If somescript.vision has been run and Vision is not allowing interactive commands, it is not run again, the code in the scope is not executed, and no navigation is done.  This is considered a success.
If somescript.vision has been run and Vision is allowing interactive command, this is treated as an error.

### Enter file

This inputs a file path into a file input.  It requires a FileLiteral, and will find the given file in the uploads directory.

    Enter file <myfile> in the "Upload file" file input.

### Push

This allows single keys or chords (e.g. CONTROL-A) to be entered.  It uses the labels Selenium uses, which can be found [here](http://selenium-python.readthedocs.org/en/latest/api.html#module-selenium.webdriver.common.keys).  To send a chord, join the keys with a hyphen.  If the chord needs to include a hyphen, make sure the Literal ends with a hyphen.  Letters in the chord are case insensitive and treated as lowercase, if you want to send a shift (to send Control-capital a, for example), include it.

    Push "DOWN" in the autocomplete
    Push "CONTROL-a" in the textfield
    Push "CONTROL-SHIFT-A" in the textfield

### Replace

This allows particular text to be replaced inside a textfield or textarea.  It takes two mandatory Literals and an optional Ordinal.

    Replace 2nd "a" with "c" in the "Layout" textarea

### Hover over

This causes the mouse to hover over an element.  This is actually equivalent to "should exist", since finding nouns causes them to be hovered over.

    Hover over the charttab panel

## Interpreter Verbs

These verbs are directed at the interpreter, and are not used by selenium at all.  They will not be saved to test files, and are intended to be used in interactive mode.

### End test

This is used to tell the interactive mode that a test scope should end.  It takes an optional Literal, which is the name of the scope to end.  This allows for multiple scopes to be closed at once.  Without the Literal, this closes the current scope.

### Load test

This loads a test from a file into the buffer.  It does not run it, however.  It takes a mandatory Literal, which is the filename.  If the file is already loaded, but is not active, this will switch the active buffer to that file.

### Run test

This begins executing the currently loaded file.  If the interpreter is allowed to drop back to the prompt, this will run until it reaches a breakpoint, an error, or the end of the file and then drop back to the prompt.  If the interpreter is not allowed to drop back to the prompt, this will run until the end of the file and then close the interpreter.

### Save test

This saves the current savable commands to the file.  A savable command is a Selenium Command that was entered via the interactive shell or a file that did not result in an error.  It takes a mandatory Literal, which is the path of the file to write to, starting from the current directory.  If the file exists, it is replaced.

### Show test

This shows the remaining lines of the test loaded into the buffer.  Breakpoints and line numbers are marked.

### Show input

This shows all savable input.

### Show all input

This shows all input, savable or not.  Errors and interpreter commands are marked.

### Skip

This skips the next command.  The command will be not be executed and will not be savable.  It takes an optional Literal, the number of lines to skip.

### Next command

This executes the next command, then returns to the interpreter prompt. 

### Break

This sets/unsets a breakpoint before the line indicated in the passed Literal, if the literal is a line number, or at all remaining lines that use the keyword, if a keyword is passed.  A Run test command will stop at that breakpoint.  Here are examples:

    Break "12"
    Break "capture"

### Step into python

This starts a pdb at the beginning of next command.  This is to make Vision development easier.

### Finish

The Finish verb disables the interactivity, and starts up the test.  The test will not stop at errors or breakpoints, and if it reaches an error, it will skip all subsequent commands.

### Quit

This quits the interpreter.

## Miscellaneous

These keywords don't easily fit anyplace.  So I put them here.

### Within

By default, a command needs to finish inside of 15 seconds.  `within` lets this number be changed for a particular command

    Click the "Quick View" link within "5" so that "If we don't get the link clicked inside 5 seconds, fail"

### Is skipped

This marks the command as a failure without running it, but allows subsequent commands to run.  This is so that one can write tests before the functionality is fully implemented.  If "is skipped" is used, "because" or "so that" is required, to ensure there's at least some indication of WHY we're skipping things (It's a great place to put the ticket number of one's bug report).  If a scope command is skipped, the entire scope will not be run, although it will be documented.

    Click the "Quick View" link is skipped because "This is an example of a skipped one-line command"
    Test "Skip this section" is skipped because "This is an example of a skipped scope, all commands in it will also be skipped"
        Click the "Quick View" link

### Because

This takes a comment to enable better explanation of the command.  It doesn't do anything else.  This ***cannot*** be used to "comment out" lines of code.  If you don't want to have a line, delete it.
The following example will take a screenshot of the portlet, and will include a comment in the results log.

    Capture the "Demographics" table because "Taking a screenshot will prove that the patient's picture has changed."

### So that

This is the same as "because".

### The

Ordinarily, a Noun must come before any Literals or modifiers.  "The" allows the Noun to come after them.  The following are equivalent.

    Click the "Submit" button
    Click button "Submit"

### As

The "as" keyword is used to mark a context.  It will mark the context of the verb of the command.  In the following example, the "Layout Table" table can be reached by using the "lt" context.

    The "Layout Table" table should exist as "lt"
    Test the "lt" context
        ...Do stuff in the "Layout Table"...

### After

***this is flaky and should be avoided***

This is a modifier that indicates the Noun comes after the previous Noun in the Command.  Here is an example.

    The "Prescriptions" table should exist after the "Results" text
    
I'm not a fan of this at all.  I added it so that I could test a particularly atrocious legacy page.

### Before

***this is flaky and should be avoided***

This is a modifier that indicates the Noun comes after the previous Noun in the Command.  Here is an example.

    The "Results" text should exist before the "Prescriptions" table

I'm not a fan of this at all.  I added it so that I could test a particularly atrocious legacy page.