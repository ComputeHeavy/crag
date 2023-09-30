import tree_sitter as ts
import pprint
import enum

'''
TODO
    convert line offsets to byte offsets
    pass file or pass file name
    index

DONE

'''

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

named_function_query = PY_LANGUAGE.query(f"""
    (module [
        (function_definition
            name: (identifier) @_fname
            (#eq? @_fname "{fname}")) @fdef
        (decorated_definition
            definition: (function_definition
                name: (identifier) @_fname
                (#eq? @_fname "{fname}")) @fdef)
    ])
    """)

class_query = PY_LANGUAGE.query(f"""
    (class_definition
        name: (identifier) @_cname
        (#eq? @_cname "{cname}")) @cdef
    """)

method_query = PY_LANGUAGE.query(f"""
    (function_definition
        name: (identifier) @_fname
        (#eq? #_fname "{fname}")) @fdef
    """)

class_method_query = PY_LANGUAGE.query(f"""
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
                    (#eq? @_fname "{fname}")) @fdef)
        ]))""")

[ea[0] for ea in class_method_query.captures(tree.root_node) 
    if not ea[1].startswith("_")]

class File:
    def __init__(self, name):
        self.name = name
        self.functions = {}
        self.classes = {}

class Class:
    def __init__(self, name, start, end):
        self.name = name
        self.functions = {}
        self.start = start  
        self.end = end

    def summary(self, f):
        out = f"class {self.name}:"
        if "__init__" in self.functions:
            init = self.functions["__init__"]

class Function:
    def __init__(self, name, params, start, end, decorator):
        self.name = name
        self.params = params
        self.start = start  
        self.end = end

    def signature(self):
        return f"{name}{params}"

    def full(self, fname):
        with open(fname) as f:
            c = f.read

langlib = 'build/lang-lib.so'

ts.Language.build_library(
  langlib,
  [
    'tree-sitter-python'
  ]
)

PY_LANGUAGE = ts.Language(langlib, 'python')

parser = ts.Parser()
parser.set_language(PY_LANGUAGE)

# code = """
# def dogslol():
#     foo()

# def foo(x: int, y):
#     if bar:
#         baz()
# """

# tree = parser.parse(bytes(code, "utf8"))

# with open("../gonk/src/api/server.py", "rb") as f:
with open("../gonk/src/core/events.py", "rb") as f:
    tree = parser.parse(f.read())

# print(tree.root_node.sexp())

print(format_sexpression(tree.root_node.sexp()))

query = PY_LANGUAGE.query("""
(class_definition
    name: (identifier) @class_name) 
""")

captures = query.captures(tree.root_node)

classes = {}

for class_name, _ in captures:
    class_ = class_name.parent
    classes[class_name.text.decode()] = (class_.start_point, class_.end_point)

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

query = PY_LANGUAGE.query("""
(function_definition) @fndef
""")

captures = query.captures(tree.root_node)
print(captures)

query = PY_LANGUAGE.query("""
(function_definition
  name: (identifier) @name
  parameters: (parameters) @params)
""")

# class: name: (start, end)
functions = {}

for function_definition, _ in captures:
    captures = query.captures(function_definition)

    if len(captures) < 2:
        continue

    if len(captures) > 2:
        captures[:2]

    name, params = captures[:2]

    fn_name, _ = name
    fn_params, _ = params
    
    parent, decorator = traverse_parents(function_definition)

    print(parent)
    print(decorator)

    print(fn_name.text.decode(), fn_params.text.decode(), sep="")
    print(function_definition.start_point)
    print(function_definition.end_point)

    print()

    start = function_definition.start_point
    end = function_definition.end_point

    if parent not in functions:
        functions[parent] = {}

    if decorator is not None:
        start = decorator.start_point
        end = decorator.end_point

    functions[parent][fn_name.text.decode()] = (start, end)

#     print(fndef.text)
#     sln, sidx  = fndef.parent.start_point
#     eln, eidx = fndef.parent.end_point
#     lines = code.split("\n")
#     print("\n".join(lines[sln:eln+1]))

pprint.pprint(functions)
