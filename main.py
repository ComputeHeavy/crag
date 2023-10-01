import tree_sitter as ts
import pprint
import click
import enum

tabwidth = 4
tab = ' '*tabwidth

def format_sexpression(s, indent_level=0, indent_size=2):
    output = ""
    i = 0
    need_newline = False
    cdepth = []
    while i < len(s):
        if s[i] == "(":
            output += "\n" + " " * (indent_level * indent_size) + "("
            indent_level += 1
            need_newline = False  
        elif s[i] == ":":
            indent_level += 1
            cdepth.append(indent_level)
            output += ":"
        elif s[i] == ")":
            indent_level -= 1
            if len(cdepth) > 0 and indent_level == cdepth[-1]:
                cdepth.pop()
                indent_level -= 1
            output += ")"
            need_newline = True 
        elif s[i] == " ":
            output += " "
        else:
            j = i
            while j < len(s) and s[j] not in ["(", ")", " ", ":"]:
                j += 1
            if need_newline:
                output += "\n" + " " * (indent_level * indent_size)
            output += s[i:j]
            i = j - 1
            need_newline = True 
        i += 1
    return output

def traverse_parents(node):
    class_name = None
    decorator = None

    while node is not None:
        # print(node)
        # print(node.type)
        if class_name is None and node.type == "class_definition":
            query = PY_LANGUAGE.query("""
                (class_definition
                    name: (identifier) @name)""")
            captures = query.captures(node)
            if len(captures) == 1:
                name, _ = captures[0]
                class_name = name.text.decode()

        if node.type == "decorated_definition":
            decorator = node

        node = node.parent

    return class_name, decorator

def named_function_query(lang, fname): 
    return lang.query(f"""
        (module [
            (function_definition
                name: (identifier) @_fname
                (#eq? @_fname "{fname}")) @fdef
            (decorated_definition
                definition: (function_definition
                    name: (identifier) @_fname
                    (#eq? @_fname "{fname}"))) @ddef
        ])
        """)

def class_method_query(lang, cname, fname):
    return lang.query(f"""
        (class_definition
            name: (identifier) @_cname
            (#eq? @_cname "{cname}")
            body: (block [
                (function_definition
                    name: (identifier) @_fname
                    (#eq? @_fname "{fname}")) @fdef
                (decorated_definition
                    definition: (function_definition
                        name: (identifier) @_fname
                        (#eq? @_fname "{fname}"))) @ddef
            ]))""")

def class_query(lang, cname):
    return lang.query(f"""
        (class_definition
            name: (identifier) @_cname
            (#eq? @_cname "{cname}")) @cdef
        """)

def clean(captures):
    return [ea[0] for ea in captures if not ea[1].startswith("_")]

def load_parser(lang):
    langlib = 'build/lang-lib.so'

    ts.Language.build_library(
      langlib,
      [
        'tree-sitter-python'
      ]
    )

    PY_LANGUAGE = ts.Language(langlib, lang)

    parser = ts.Parser()
    parser.set_language(PY_LANGUAGE)

    return PY_LANGUAGE, parser

@click.group()
def cli():
    pass

class Bar:
    pass

class Baz:
    pass

class Foo(Bar, Baz):
    '''doc string'''
    def __init__(self):
        pass

    def bar(self):
        """doc string"""
        pass

@cli.command("fetch")
@click.option("--file", required=True, type=str)
@click.option("--class", "class_", required=False, type=str)
@click.option("--function", required=False, type=str)
def fetch(file, class_, function):
    if class_ is None and function is None:
        raise ValueError("must provide at least one of class or function")

    lang, parser = load_parser("python")

    # with open("../gonk/src/api/server.py", "rb") as f:
    with open(file, "rb") as f:
        tree = parser.parse(f.read())

    # print(format_sexpression(tree.root_node.sexp()))

    if class_ and function:
        q = class_method_query(lang, class_, function)
    elif class_:
        q = class_query(lang, class_)
    elif function:
        q = named_function_query(lang, function)

    caps = clean(q.captures(tree.root_node))

    if len(caps) == 0:
        raise ValueError("nothing found")

    if len(caps) > 1:
        raise ValueError("multiple found")
        
    node, = caps

    start = node.start_byte - node.start_point[1]
    print(tree.root_node.text[start:node.end_byte].decode())

    return node

def class_info(lang, cnode):
    name_query = lang.query(f"""
        (class_definition 
            name: (identifier) @name)
        """)
    name = name_query.captures(cnode)

    if len(name) != 1:
        raise ValueError("classname not found")

    name, = [ea[0].text.decode() for ea in name]

    super_query = lang.query(f"""
        (class_definition 
            superclasses: (argument_list
                (identifier) @superclass))
        """)

    supers = super_query.captures(cnode)
    supers = [ea[0].text.decode() for ea in supers]

    docstring_query = lang.query(f"""
        (class_definition 
            body: (block
                .
                (expression_statement
                    (string
                        (string_content) @docstring))))
        """)

    docstring = docstring_query.captures(cnode)
    docstring = [ea[0].text.decode() for ea in docstring]

    if len(docstring) == 1:
        docstring, = docstring
    else:
        docstring = ""

    function_query = lang.query(f"""
        (class_definition
            body: (block [
                (function_definition) @fdef
                (decorated_definition
                    definition: (function_definition)) @ddef
            ]))
        """)

    functions = function_query.captures(cnode)
    functions = [ea[0] for ea in functions]

    return name, supers, docstring, function

# @cli.command("summarize")
# @click.option("--file", required=True, type=str)
# @click.option("--class", "class_", required=True, type=str)
def summarize(file, class_):
    lang, parser = load_parser("python")

    with open(file, "rb") as f:
        tree = parser.parse(f.read())

    q = class_query(lang, class_)
    caps = clean(q.captures(tree.root_node))

    if len(caps) == 0:
        raise ValueError("nothing found")

    if len(caps) > 1:
        raise ValueError("multiple found")
        
    cnode, = caps

    name, supers, docstring, functions = class_info(lang, cnode)

    print(format_sexpression(cnode.sexp()))

    print(f"class {name}({', '.join(supers)}):")
    if docstring:
        print(f'{tab}"""{docstring}"""')

    print(functions)

    return cnode

if __name__ == "__main__":
    cli()

# pprint.pprint(classes)

"""
module names
class names
class init
superclasses
function names
function classes
function decorators
class variables
"""

