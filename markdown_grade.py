from functools import cached_property
import operator
import re
from typing import NamedTuple, Tuple

from markdown_parse import load_markdown_file

#from junitparser import JUnitXml  # https://pypi.org/project/junitparser/
#from junitparser import TestCase, TestSuite, JUnitXml, Skipped, Error
import junitparser

REGEX_NUMBER_IN_BRACKETS = re.compile(r'\(.*(?P<number>\d+).*\)')



# Data Extraction --------------------------------------------------------------

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


# Mark to Test -----------------------------------------------------------------

class MarkTemplate(NamedTuple):
    headings: tuple[str]
    template_text: str
    def mark(self, target_text):
        testcase = junitparser.TestCase(
            name=f'{self.headings[-1]} ({self.marks} marks)', 
            classname='.'.join(self.headings),
        )
        testcase.system_out = self.template_text
        testcase.system_err = target_text
        return testcase

class MarkTemplateWordCount(MarkTemplate):
    REGEX_WORDS_MARKS = re.compile(r'(?P<words>\d+)\s+word.*?(?P<marks>\d+)\s+mark')

    @cached_property
    def _words_marks(self):
        return tuple(
            (int(match.group(1)), int(match.group(2)))
            for match in self.REGEX_WORDS_MARKS.finditer(self.template_text)
        )
    @property
    def words(self):
        return sum(map(operator.itemgetter(0), self._words_marks))
    @property
    def marks(self):
        return sum(map(operator.itemgetter(1), self._words_marks))

    def mark(self, target_text):
        testcase = super().mark(target_text)
        testcase.result  # TODO
        #case1.classname = "modified.class.name" # specify or change case attrs
        #case1.result = [Skipped()] # You can have a list of results

        #case2 = TestCase('case2')
        #case2.result = [Error('Example error message', 'the_error_type')]
        return testcase

class MarkTemplateCodeBlock(MarkTemplate):
    @property
    def code_blocks(self):
        pass
    @property
    def marks(self):
        pass
    def mark(self, target_text):
        testcase = super().mark(target_text)
        return testcase

class MarkTemplateUrls(MarkTemplate):
    REGEX_URLS = re.compile(r'https?://')
    @property
    def urls(self):
        return sum(int(match.group(1)) for match in self.REGEX_URLS.finditer())
    @property
    def marks(self):
        pass
    def mark(self, target_text):
        testcase = super().mark(target_text)
        return testcase



_mark_templates=(MarkTemplateWordCount, MarkTemplateCodeBlock, MarkTemplateUrls)

def mark_template(template, target):
    for template_text, headings in nested_headings_iterator(template):
        target_text = get_text_at_headings(target, headings)
        yield from (
            MarkTemplate(headings, template_text).mark(target_text)
            for MarkTemplate in _mark_templates
        )

if __name__ == "__main__":
    template = load_markdown_file('../frameworks_and_languages_module/technical_report.md')
    target = load_markdown_file('README.md')

    suite = junitparser.TestSuite('markdown')
    suite.add_property('build', '55')
    for testcase in mark_template(template, target):
        suite.add_testcase(testcase)
        print(testcase)
    xml = junitparser.JUnitXml()
    xml.add_testsuite(suite)
    xml.write('junit.xml')
