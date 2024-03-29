from functools import cached_property
from itertools import chain
import re
from typing import NamedTuple

from markdown_parse import load_markdown

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
    REGEX_WORDS_MARKS = re.compile(r'(?P<words>\d+)(?:ish)?\s+word.*?(?P<marks>\d+)\s+mark')
    REGEX_WORD_COUNT = re.compile(r'\w+')

    @cached_property
    def _words_marks(self):
        return tuple(
            (int(match.group(1)), int(match.group(2)))
            for match in self.REGEX_WORDS_MARKS.finditer(self.template_text or '')
        )

    def testcases(self, target_text):
        target_text = (target_text or '').replace(self.template_text, '')  # Remove template from target (we don't want to count unmodified text)
        total_words = len(self.REGEX_WORD_COUNT.findall(target_text or ''))
        for index, (words, marks) in enumerate(self._words_marks):
            testcase = super()._testcase(target_text, index)
            if words > total_words:
                testcase.result = [junitparser.Error(f'Word count failed: expected {words} got {total_words}', 'word_count')]
            yield testcase
            total_words = total_words - words

class MarkTemplateUrls(MarkTemplate):
    REGEX_URL_MARK = re.compile(r'\(.*?(url|link).*?\)')
    REGEX_URL_COUNT = re.compile(r'https?://')
    @cached_property
    def urls(self):
        return self.REGEX_URL_MARK.findall(self.template_text or '')
    def testcases(self, target_text):
        urls = len(self.REGEX_URL_COUNT.findall(target_text or ''))
        for index, url in enumerate(self.urls):
            testcase = super()._testcase(target_text, index)
            if urls <= 0:
                testcase.result = [junitparser.Error(f'Url count failed: expected {index}', 'url_count')]
            yield testcase
            urls += -1

class MarkTemplateCodeBlockSimple(MarkTemplate):
    # Incomplete - this is awful
    REGEX_CODEBLOCK_MARK = re.compile(r'\(.*?code.*?(?P<marks>\d+)\s+mark')
    REGEX_CODEBLOCK = re.compile(r'FencedCode:(\w+):(\d+)')
    def _lang_lines(self, text):
        return tuple(
            (match.group(1), int(match.group(2)))
            for match in self.REGEX_CODEBLOCK.finditer(text or '')
        )
    def testcases(self, target_text):
        actual_number_of_code_blocks = len(self._lang_lines(target_text))
        required_number_of_code_blocks = len(self.REGEX_CODEBLOCK_MARK.findall(self.template_text or ''))
        for index in range(required_number_of_code_blocks):
            testcase = super()._testcase(target_text, index)
            if (actual_number_of_code_blocks - index) <= 0:
                testcase.result = [junitparser.Error(f'Code block count failed: expected {index}', 'code_block')]
            yield testcase


class MarkTemplateCodeBlock(MarkTemplate):
    # Incomplete - this is awful
    REGEX_CODEBLOCK = re.compile(r'FencedCode:(\w+):(\d+)')
    def _lang_lines(self, text):
        return tuple(
            (match.group(1), int(match.group(2)))
            for match in self.REGEX_CODEBLOCK.finditer(text or '')
        )
    @cached_property
    def _code_blocks(self):
        return self._lang_lines(self.template_text)  # TODO: we should not be reusing REGEX_CODEBLOCK and should have a proper defection of languages and line-count
    def testcases(self, target_text):
        lang_lines = self._lang_lines(target_text)
        for index, (language, lines) in enumerate(self._code_blocks):
            testcase = super()._testcase(target_text, index)
            # TODO: this just counts code blocks, we probably want more
            if index >= len(lang_lines):
                testcase.result = [junitparser.Error(f'Code block count failed: expected {index}', 'code_block')]
            yield testcase

_mark_templates=(MarkTemplateWordCount, MarkTemplateUrls, MarkTemplateCodeBlockSimple)

def mark_template(template, target):
    r"""
    >>> template = {
    ...     'heading1.a': {
    ...         '': '(10 words - 1 mark)\n(10ish words - 1 mark)\n',
    ...         'heading2': {
    ...             '': '\n   (a code block of awesome - 1 mark)   \n',
    ...         }, 
    ...     },
    ...     'heading1.b': {
    ...         '': '(a link to a thing)',
    ...     }
    ... }
    >>> target = {
    ...     'heading1.a': {
    ...         '': 'I once was a chimp who lived on a boat. Chimps cant make or sail boats, so this is obviously fiction',
    ...         'heading2': {
    ...             '': 'FencedCode:javascript:5   and another code block   FencedCode:javascript:5',
    ...         },
    ...     },
    ...     'heading1.b': {
    ...         '': 'i really think https://example.com/ is a good site',
    ...      },
    ... }
    >>> tuple(testcase.is_passed for testcase in mark_template(template, target))
    (True, True, True, True)
    >>> tuple(testcase.is_passed for testcase in mark_template(template, {}))
    (False, False, False, False)
    """
    for template_text, headings in nested_headings_iterator(template):
        target_text = get_text_at_headings(target, headings)
        yield from chain.from_iterable(
            MarkTemplate(headings, template_text).testcases(target_text)
            for MarkTemplate in _mark_templates
        )


# Top Level Exports ------------------------------------------------------------

def markdown_grade(template, target, junit_filename=None, **kwargs):
    suite = junitparser.TestSuite('markdown')
    for k, v in kwargs.items():
        suite.add_property(k, v)
    suite.add_testcases(mark_template(
        template=load_markdown(template),
        target=load_markdown(target),
    ))
    xml = junitparser.JUnitXml()
    xml.add_testsuite(suite)
    if junit_filename:
        xml.write(junit_filename)
    return xml


# Main -------------------------------------------------------------------------

if __name__ == "__main__":
    markdown_grade(
        template='../frameworks_and_languages_module/technical_report.md',
        #target='README.md',
        #target='./technical_report_target.md',
        target='../frameworks_and_languages_module/technical_report.md',
        junit_filename='junit.xml',
    )
