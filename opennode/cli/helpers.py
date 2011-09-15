import types

from snack import ButtonBar, TextboxReflowed, CheckboxTree, GridFormHelp

def SelectCheckboxWindow(screen, title, text, items, buttons = ('Ok', 'Cancel'),
            width = 40, scroll = 0, height = -1, help = None):
    """Helper class for displaying a windows with a checkbox list. 
    On exit, list of selected items is returned"""
    if (height == -1): height = len(items)
    if len(items) > height: scroll = 1
    bb = ButtonBar(screen, buttons)
    t = TextboxReflowed(width, text)
    cb = CheckboxTree(height, scroll = scroll)
    count = 0
    for count, item in enumerate(items):
        if isinstance(item, types.TupleType):
            (text, key, selected) = item
        else:
            text = item
            key = count
            selected = 0

        cb.append(text, key, selected)

    g = GridFormHelp(screen, title, help, 1, 3)
    g.add(t, 0, 0)
    g.add(cb, 0, 1, padding = (0, 1, 0, 1))
    g.add(bb, 0, 2, growx = 1)
    rc = g.runOnce()
    return (bb.buttonPressed(rc), cb.getSelection())

