from collections import defaultdict
tree = lambda: defaultdict(tree)
from pathlib import Path

import marko

# parse markdown for automated marking/stats

md_test = """
before

Test1
=====
This is a test.
* thing1
  * thing1.5
* [thing2](http://example.com/) a link
End of test

code
----
Some code
```javascript
function test() {return "yes"}
```

Test2
=====
Another test.

"""

def parse(data):
    return marko.Markdown().parse(data)

def _children_text(block):
    if not hasattr(block, 'children'):
        return
    if isinstance(block.children, str):
        yield block.children
    for child in block.children:
        yield from _children_text(child)
def _block_text(block):
    return '\n'.join(_children_text(block))
def _block_code_summary(block):
    assert block.get_type() == 'FencedCode'
    line_count = block.children[0].children.count('\n')
    return f'FencedCode:{block.lang}:{line_count}'

def markdown_text_dicts(blocks):
    r'''
    >>> markdown_text_dicts(parse(md_test).children)
    {'': 'before', 'Test1': {'': 'This is a test.\nthing1\nthing1.5\nthing2\n a link\nEnd of test', 'code': {'': 'Some code\nFencedCode:javascript:1'}}, 'Test2': {'': 'Another test.'}}
    '''
    data = tree()
    heading_stack = []
    def get_data():
        _d = data
        for k in heading_stack:
            _d = _d[k]
        return _d.setdefault('', [])

    for block in blocks:
        _level = getattr(block, 'level', len(heading_stack))
        if _level != len(heading_stack):
            if _level > len(heading_stack):
                heading_stack[:] = heading_stack + ['(unknown)']*(_level-1 - len(heading_stack))
            if _level < len(heading_stack):
                heading_stack[:] = heading_stack[:_level-1]
            heading_stack.append(_block_text(block))
            get_data()
        if block.get_type() in ('Paragraph', 'List'):
            get_data().append(_block_text(block))
        if block.get_type() == 'FencedCode':
            get_data().append(_block_code_summary(block))

    def normalise_data(data):
        for k, v in data.items():
            if isinstance(v, dict):
                data[k] = normalise_data(v)
            if isinstance(v, list):
                data[k] = '\n'.join(v)
        return dict(data)
    return normalise_data(data)


def markdown_codeblock_languages(block):
    r'''
    >>> markdown_codeblock_languages(parse(md_test))
    {'javascript': ['function test() {return "yes"}']}
    '''
    raise NotImplementedError()

#bb = parse(md_test)
#from pprint import pprint
#pprint(
#    markdown_text_dicts(bb.children)
#)

def load_markdown(data):
    r"""
    >>> load_markdown('# Test')
    {'Test': {'': ''}}
    >>> from pathlib import Path
    >>> _ = 'TODO: tempfile for path'
    >>> import io
    >>> load_markdown(io.StringIO('# Test'))
    {'Test': {'': ''}}
    """
    try:
        if isinstance(data, str) and Path(data).is_file():
            data = Path(data)
    except OSError:
        pass
    if isinstance(data, Path):
        data = data.open('rt')
    if hasattr(data, 'read') and callable(data.read):
        data = data.read()
    return markdown_text_dicts(parse(data).children)
