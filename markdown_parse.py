import marko

# parse markdown for automated marking/stats

md_test = """
Test1
=====
This is a test.
* thing1
  * thing1.5
* thing2
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

def markdown_text_dicts(block):
    r'''
    >>> markdown_text_dicts(parse(md_test))
    {'Test1': {'': 'This is a test. thing1 thing1.5 thing2 End of test', 'code': 'Some code'}, 'Test2': {'': 'Another test.'}}
    '''
    raise NotImplementedError()

def markdown_codeblock_langauges(block):
    r'''
    >>> markdown_codeblock_langauges(parse(md_test))
    {'javascript': ['function test() {return "yes"}']}
    '''
    raise NotImplementedError()
