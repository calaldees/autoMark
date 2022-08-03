import re
from pathlib import Path

from markdown_parse import load_markdown_file

#from junitparser import JUnitXml  # https://pypi.org/project/junitparser/
#from junitparser import TestCase, TestSuite, JUnitXml, Skipped, Error
import junitparser

REGEX_NUMBER_IN_BRACKETS = re.compile(r'\(.*(?P<number>\d+).*\)')
REGEX_MARKS_IN_BRACKETS = re.compile(r'\(.*(?P<marks>\d+)\s+mark.*\)')
REGEX_WORDS_IN_BRACKETS = re.compile(r'\(.*(?P<words>\d+)\s+word.*\)')


def temp():

    case1 = junitparser.TestCase('case1', 'class.name') # params are optional
    #case1.classname = "modified.class.name" # specify or change case attrs
    case1.result = [Skipped()] # You can have a list of results
    case2 = TestCase('case2')
    case2.result = [Error('Example error message', 'the_error_type')]


    suite = junitparser.TestSuite('markdown')
    suite.add_property('build', '55')
    suite.add_testcase(case1)
    suite.add_testcase(case2)

    xml = JUnitXml()
    xml.add_testsuite(suite)
    xml.write('junit.xml')


def nested_headings_iterator(data, heading=()):
    """
    >>> data = {'Heading1': {'': 'some text', 'Heading2 (heading order 1)': {'': 'Some more text', 'Heading3.a': {'': ''}}, 'Heading2 (heading order 2)': {'': 'final'} }}
    >>> tuple(nested_headings_iterator(data))
    (('some text', ('Heading1',)), ('Some more text', ('Heading1', 'Heading2 (heading order 1)')), ('', ('Heading1', 'Heading2 (heading order 1)', 'Heading3.a')), ('final', ('Heading1', 'Heading2 (heading order 2)')))
    """
    for k, v in data.items():
        if k == '':
            yield (v, heading)
        else:
            yield from nested_headings_iterator(v, heading=heading+(k,))

def _normalise_heading(heading):
    """
    >>> _normalise_heading('heading')
    'heading'
    >>> _normalise_heading('(heading 3 - I think)')
    3
    """
    try:
        return int(REGEX_NUMBER_IN_BRACKETS.search(heading).group(1))
    except:
        return heading
def get_text_at_headings(data, headings):
    """
    >>> data = {'Heading1': {'': 'some text', 'Heading2 (heading order 1)': {'': 'Some more text', 'Heading3.a': {'': ''}}, 'Heading2 (heading order 2)': {'': 'final'} }}
    >>> get_text_at_headings(data, ('Heading1',))
    'some text'
    >>> get_text_at_headings(data, ('Heading1', 2))
    'final'
    >>> get_text_at_headings(data, ('Some nonsense', 'more nonsense'))
    """
    for heading in map(_normalise_heading, headings):
        try:
            heading = tuple(data.keys())[heading]
        except:
            pass
        if heading in data:
            data = data[heading]
    return data.get('')


def mark(template, target):
    for template_text, headings in nested_headings_iterator(template):
        target_text = get_text_at_headings(target, headings)
        print(f'{template_text=} {target_text=}')


if __name__ == "__main__":
    template = load_markdown_file('../frameworks_and_languages_module/technical_report.md')
    target = load_markdown_file('README.md')
    mark(template, target)
