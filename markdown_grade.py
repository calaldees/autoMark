from functools import cached_property
from itertools import chain
import operator
import re
from typing import NamedTuple, Tuple

from markdown_parse import load_markdown_file

import junitparser  # https://pypi.org/project/junitparser/

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
    def _testcase(self, target_text, index=0) -> junitparser.TestCase:
        testcase = junitparser.TestCase()
        testcase.name = f'{self.headings[-1]}.{index}'
        testcase.classname = '.'.join(self.headings + (str(index),))
        testcase.system_out = self.template_text
        testcase.system_err = target_text
        return testcase

class MarkTemplateWordCount(MarkTemplate):
    REGEX_WORDS_MARKS = re.compile(r'(?P<words>\d+)\s+word.*?(?P<marks>\d+)\s+mark')
    REGEX_WORD_COUNT = re.compile(r'\w+')

    @cached_property
    def _words_marks(self):
        return tuple(
            (int(match.group(1)), int(match.group(2)))
            for match in self.REGEX_WORDS_MARKS.finditer(self.template_text or '')
        )

    def testcases(self, target_text):
        total_words = len(self.REGEX_WORD_COUNT.findall(target_text or ''))
        for index, (words, marks) in enumerate(self._words_marks):
            testcase = super()._testcase(target_text, index)
            if words > total_words:
                testcase.result = [junitparser.Error(f'Word count failed: expected {words} got {total_words}', 'word_count')]
            yield testcase
            total_words = total_words - words

class MarkTemplateUrls(MarkTemplate):
    REGEX_URL_MARK = re.compile(r'\(.*?url.*?\)')
    REGEX_URL_COUNT = re.compile(r'https?://')
    @cached_property
    def urls(self):
        return self.REGEX_URL_MARK.findall(self.template_text or '')
    def testcases(self, target_text):
        urls = len(self.REGEX_URL_COUNT.findall(target_text or ''))
        for index, url in enumerate(self.urls):
            testcase = super()._testcase(target_text, index)
            if urls < 0:
                testcase.result = [junitparser.Error(f'Url count failed: expected {index}', 'url_count')]
            yield testcase
            urls += -1

class MarkTemplateCodeBlock(MarkTemplate):
    @property
    def code_blocks(self):
        pass
    def testcases(self, target_text):
        yield
        #return  # NotImplemented
        #testcase = super().testcase(target_text)
        #return testcase

_mark_templates=(MarkTemplateWordCount, MarkTemplateUrls, MarkTemplateCodeBlock)

def mark_template(template, target):
    r"""
    >>> template = {
    ...     'heading1.a': {
    ...         '': '(10 words - 1 mark)\n(10 words - 1 mark)\n',
    ...         'heading2': {
    ...             '': '(code block)',
    ...         }, 
    ...     },
    ...     'heading1.b': {
    ...         '': '(url)',
    ...     }
    ... }
    >>> target = {
    ...     'heading1.a': {
    ...         '': 'I once was a chimp who lived on a boat. Chimps cant make or sail boats, so this is obviously fiction',
    ...         'heading2': {
    ...             '': 'FencedCode:javascript:5',
    ...         },
    ...     },
    ...     'heading1.b': {
    ...         '': 'https://example.com/',
    ...      },
    ... }
    >>> tuple(mark_template(template, target))
    """
    for template_text, headings in nested_headings_iterator(template):
        target_text = get_text_at_headings(target, headings)
        yield from chain.from_iterable(
            MarkTemplate(headings, template_text).testcases(target_text)
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
