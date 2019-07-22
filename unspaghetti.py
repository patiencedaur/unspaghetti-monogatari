"""
Monogatari Visual Novel Unspaghettifier

Helps you keep up with the growing script of your Monogatari novel.
Keep track of possible storylines, visualizing them in a graph.

# How To
1. Put this file in your project folder (where the "js" folder is located).
2. Open the terminal and go to your project folder.
Launch from the command line: `python unspaghetti.py`.
A file called `viz.txt` will be created.
This is your story in the form of a graph in DOT language.
3. Copy the content of `viz.txt` and post it on viz-js.com.
The rest will be done by Viz.js.
Viz.js is Graphviz (a library to draw graphs) on the web.
4. Ta-da!
"""

from __future__ import print_function
import re
import os
from itertools import cycle

# Only look for story scripts in this folder
folder = 'js'
# Do not consider non-storyline-related JS
file_mask = r'^(?:(?!options)(?!main)(?!storage).)*?\.js$'

# Regular Expressions #

# jump directive with next label name
monogatari_jump = r'jump \w+'

# Do not use spaces before the opening bracket
# after monogatari.label in the story scripts
# (it doesn't work for whatever reason)


# Data Extraction #

def read_file(folder, file):
    """
    Read file contents and strip it of whitespace.
    """
    with open(os.path.join(folder, file)) as f:
        contents = f.read()
    return ''.join(re.split(r'\t|\n', contents))


def regular_labels(file_no_spaces):
    """
    Return an iterator over labels in regularly formatted files
    (not like the Start label in script.js).
    """
    # monogatari.label(SOMETHING]);
    monogatari_label = r'monogatari\.label\s?\(.*?\]\);?'
    return re.finditer(monogatari_label, file_no_spaces)


def curly_bracket_parse(text):
    """
    Helper for parsing monogatari.script().
    Return everything between the first left and the last right
    curly brackets - with other curly brackets inside.
    """
    bracket_balance = 0 # left +, right -
    first_left = 0
    last_right = 0

    for i in range(len(text)):
        if text[i] == '{':
            if bracket_balance == 0:
                first_left = i
            bracket_balance += 1
        elif text[i] == '}':
            bracket_balance -= 1
            if bracket_balance == 0:
                # becomes zero only if bracket is passed and closed
                # (that's why we decrement first and then check the condition)
                last_right = i
                break # skip everything after the end of monogatari.script()

    return text[first_left:last_right]


def start_labels(script_file_no_spaces):
    """
    Return an iterator over labels used in the start script.
    Only applicable to the file called script.js
    (because it is the only one using monogatari.script()-formatted labels).
    """
    # find everything AFTER "monogatari.script"
    text = script_file_no_spaces.partition("monogatari.script")[2]
    # extract everything in curly brackets
    starting_script = curly_bracket_parse(text)
    # look for anything like 'LabelName': [content]
    # iterate over labels
    monogatari_start_parts = r'(?:\"|\')\w+(?:\"|\')\:\s{0,1}\[.*?\]'
    return re.finditer(monogatari_start_parts, starting_script)


def parse_start(label):
    """
    Starting labels look somewhat different:
    monogatari.script({'name': [content], 'name2': [more_content]});
    Parse a label like this and return (name, [where it jumps to]).
    """
    name_and_content = re.split("\:\s{0,1}\[", label.group())
    label_name = name_and_content[0][1:-1]
    jumps = re.findall(monogatari_jump, name_and_content[1])
    jump_names = [j[5:] for j in jumps]
    return (label_name, jump_names)


def parse_regular(label):
    """
    Parse a string like monogatari.label('name', [content]).
    Return (name, [where it jumps to]).
    """
    label_content = label.group().split('monogatari.label')[1]
    label_name = label_content[2:].split('\'')[0]
    jumps = re.findall(monogatari_jump, label_content)
    jump_names = [j[5:] for j in jumps]
    return (label_name, jump_names)


def fullmatch(regex, string, flags=0):
    """
    For backwards compatibility. Emulate python3 re.fullmatch.
    """
    return re.match("(?:" + regex + r")\Z", string, flags=flags)


def story_schema(folder):
    """
    Parse all script files in the folder.
    Return a dict of nodes like
    {file: [(label1, [jump points]), [(label2, [jump points])]}.
    """
    schema = {}

    for file in os.listdir(folder):  # run through the folder
        if fullmatch(file_mask, file):  # find only script-related js files
            no_spaces = read_file(folder, file)
            file_labels = []  # a list of tuples for each file

            if file == 'script.js':
                # parse and add 'start'-formatted labels
                for label in start_labels(no_spaces):
                    node = parse_start(label)
                    file_labels.append(node)

            for label in regular_labels(no_spaces):
                # parse and append the rest
                node = parse_regular(label)
                file_labels.append(node)

            schema[file] = file_labels

    return schema


def print_schema(folder):
    """
    Print all story labels and their jumps, one file after another.
    """
    schema = story_schema(folder)
    for file in schema.keys():
        print(file)
        print(schema[file])
        print()


# Create a DOT file for Viz.js #

def viz_js(schema):
    """
    Generate a file in Dot language to export to Viz.js.
    """
    colors = cycle(['yellow', 'green', 'pink', 'lightblue', 'orange', 'grey'])
    end_nodes = []

    with open('viz.txt', 'w') as f:

        # begin generating the file
        f.write("# I'm a Dot graph of your Monogatari visual novel!\n\n")
        f.write("digraph G {\n")

        # create a subgraph for each file in the scenario
        for file in schema.keys():
            color = next(colors)  # color of all nodes in the file

            # discard the hyphen and ".js" in name
            subgraph_name = re.sub("-", "_", file[:-3].capitalize())
            f.write("\n\tsubgraph %s {\n" % subgraph_name)
            f.write("\t\tnode [style=filled, color=%s];\n" % color)

            for node in schema[file]:
                # go through tuples like (label_name, [list_of_jumps])
                if node[0] == "Start":
                    f.write("\t\tStart [shape=box];\n")
                if node[1]:
                    for jump in node[1]:  # go through all jumps
                        f.write("\t\t%s -> %s;\n" % (node[0], jump))
                # otherwise, it's an end node
                else:
                    # print("end node", node)
                    end_nodes.append(node[0])

            # display label and close subgraph
            f.write('\t\tlabel = "%s";\n\t}\n' % subgraph_name)

        # end nodes are out of any subgraph
        for end_node in end_nodes:
            f.write("\t%s -> end;\n" % end_node)

        # Display the node 'end'
        f.write("\n\tend [shape=Msquare];   \n}")


schema = story_schema(folder)
# print_schema(folder)
viz_js(schema)
