import types

from snack import Textbox, Entry, Button, Listbox
from snack import ButtonBar, TextboxReflowed, CheckboxTree, GridFormHelp, SnackScreen

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

def CreateTemplateWindow(screen, title, vm_type, templates, help = None):
    """Helper class for displaying a form for creating a new VM template"""
    label_base = Textbox(40, 2, 'Select %s VM to be used as a template' %vm_type, 0, 0)
    
    base_tmpl = Listbox(7, 1, 0, 30, 1)
    for vm in templates.keys():
        base_tmpl.append(templates[vm], vm)
    
    label_newname = Textbox(40, 2, 'Name of the template to be created', 0, 0)
    spacer1 = Textbox(1, 1, "", 0, 0)
    spacer2 = Textbox(1, 1, "", 0, 0)
    entry_newname = Entry(30, 'template_name')
    bb = ButtonBar(screen, ('Create new template', 'Main menu'))
    form = GridFormHelp(screen, title, help, 1, 7)
    form.add(label_base, 0, 0)
    form.add(base_tmpl, 0, 1)
    form.add(spacer1, 0, 2)
    form.add(label_newname, 0, 3)
    form.add(entry_newname, 0, 4)
    form.add(spacer2, 0, 5)
    form.add(bb, 0, 6)
    form_result = form.runOnce()
    return (bb.buttonPressed(form_result), templates[base_tmpl.current()], entry_newname.value())
