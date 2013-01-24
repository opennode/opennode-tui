import types
import re

from opennode.cli import actions

from snack import (Textbox, Entry, Button, Listbox, Grid, Scale, Form,
                   ButtonBar, TextboxReflowed, CheckboxTree, GridFormHelp,
                   ButtonChoiceWindow, ListboxChoiceWindow, Label)


class DownloadMonitor():

    def __init__(self, screen, title, item_count=0):
        self.screen = screen
        self.title = title
        self.current_item = 0
        self.item_count = item_count

        g = Grid(1, 2)
        self.fnm_label = Textbox(40, 2, 'Downloading...', 0, 0)
        self.scale = Scale(40, 100)
        self.scale.set(0)
        g.setField(self.fnm_label, 0, 1)
        g.setField(self.scale, 0, 0)
        self.screen.gridWrappedWindow(g, title)
        self.f = Form()
        self.f.add(self.scale)
        self.f.add(self.fnm_label)

    def update_url(self, fnm):
        self.current_item = self.current_item + 1
        self.fnm_label.setText("(%s/%s): %s" % (self.current_item,
                                                self.item_count, fnm))

    def download_hook(self, count, blockSize, totalSize):
        donep = int(min(100, float(blockSize * count) / totalSize * 100))
        self.scale.set(donep)
        self.f.draw()
        self.screen.refresh()


def create_select_checkbox(screen, title, text, items, buttons=(('Cancel', 'cancel', 'F12'), 'Ok'),
            width=40, scroll=0, height=-1, help=None):
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


def display_create_template(screen, title, vm_type, templates, help=None):
    """Helper class for displaying a form for creating a new VM template"""
    label_base = Textbox(40, 2,
        'Select %s VM to be used as a basis\n(only stopped VMs are allowed)' %
        vm_type, 0, 0)

    base_tmpl = Listbox(7, 1, 0, 30, 1)
    for vm in templates.keys():
        base_tmpl.append(templates[vm], vm)

    label_newname = Textbox(40, 2, 'Name of the template to be created', 0, 0)
    spacer1 = Textbox(1, 1, "", 0, 0)
    spacer2 = Textbox(1, 1, "", 0, 0)
    entry_newname = Entry(30, 'template_name')
    bb = ButtonBar(screen, ('Create new template', ('Back to menu', 'back')))
    form = GridFormHelp(screen, title, help, 1, 7)
    form.add(label_base, 0, 0)
    form.add(base_tmpl, 0, 1)
    form.add(spacer1, 0, 2)
    form.add(label_newname, 0, 3)
    form.add(entry_newname, 0, 4)
    form.add(spacer2, 0, 5)
    form.add(bb, 0, 6)
    form_result = form.runOnce()
    tmpl_name = entry_newname.value()
    # remove whitespaces from the template name
    tmpl_name = re.sub(r'\s', '', tmpl_name)
    return (bb.buttonPressed(form_result), str(base_tmpl.current()), tmpl_name)


def display_selection(screen, title, list_of_items, subtitle, default = None,
                      buttons = [('Back', 'back', 'F12'), 'Ok']):
    """Display a list of items, return selected one or None, if nothing was selected"""
    #if len(list_of_items) == 1:
        # shortcut if there's only one item for choosing
    #    return list_of_items[0]

    if len(list_of_items) > 0:
        if not isinstance(list_of_items[0], types.TupleType):
            # if we have a list of strings, we'd prefer to get these strings as the selection result
            list_of_items = zip(list_of_items, list_of_items)
        height = 10
        scroll = 1 if len(list_of_items) > height else 0
        action, selection = ListboxChoiceWindow(screen, title, subtitle, list_of_items,
                            buttons, scroll = scroll, height = height, default = default)
        if buttons == [('Back', 'back', 'F12'), 'Ok'] or buttons == [('Menu', 'back', 'F12'), 'Ok']:
            if action != 'back':
                return selection
        else:
            return (action, selection) # customized buttons
    else:
        ButtonChoiceWindow(screen, title, 'Sorry, there are no items to choose from.', ['Back'])
    return None


def display_checkbox_selection(screen, title, list_of_items, subtitle):
    if len(list_of_items) > 0:
        action, selection = create_select_checkbox(screen, title, subtitle,
                                                   list_of_items,
                                                   ['Ok', 'Back'],
                                                   height = 10)
        if action != 'back':
            return selection
    else:
        ButtonChoiceWindow(screen, title,
                           'Sorry, there are no items to choose from',
                           ['Back'])
    return None


def display_vm_type_select(screen, title):
    """Display selection menu for the template type"""
    types = [actions.vm.backend_hname(t) for t in actions.vm.backends()]
    return display_selection(screen, title, types, 'Select a VM type to use:',
                             buttons=[('Menu', 'back', 'F12'), 'Ok'])


def display_info(screen, title, info_text="Close me, please.", width=50, height=2):
    """Display information message on information screen"""
    g = GridFormHelp(screen, title, help, 1, 2)
    g.add(Textbox(width, height, info_text, 0, 0), 0, 0, padding = (0, 1, 0, 1))
    g.add(Button("OK"), 0, 1)
    g.runOnce()


def display_template_edit_form(screen, title, settings):
    buttons=(('Cancel', 'cancel', 'F12'), 'Ok')
    label_mincpu = Label('Minimal cpus')
    label_normcpu = Label('Default cpus')
    label_minmem = Label('Minimal memory (GB)')
    label_normmem = Label('Default memory (GB)')
    label_name = Label('Template name')
    e_mincpu = Entry(30, settings.get('vcpu_min', 1))
    e_normcpu = Entry(30, settings.get('vcpu', 1))
    e_minmem = Entry(30, settings.get('memory_min', 0.25))
    e_normmem = Entry(30, settings.get('memory', 0.25))
    e_name = Entry(30, settings.get('template_name'))
    gr = Grid(2, 5)
    gr.setField(label_name, 0, 0)
    gr.setField(e_name, 1, 0)
    gr.setField(label_minmem, 0, 1)
    gr.setField(e_minmem, 1, 1)
    gr.setField(label_normmem, 0, 2)
    gr.setField(e_normmem, 1, 2)
    gr.setField(label_mincpu, 0, 3)
    gr.setField(e_mincpu, 1, 3)
    gr.setField(label_normcpu, 0, 4)
    gr.setField(e_normcpu, 1, 4)

    g = GridFormHelp(screen, 'Rename', help, 1, 3)
    t = TextboxReflowed(50, 'Edit template %s' % settings.get('template_name'))
    bb = ButtonBar(screen, buttons)
    g.add(t, 0, 0, growx=1)
    g.add(gr, 0, 1)
    g.add(bb, 0, 2, growx=1)
    rc = g.runOnce() 

    if bb.buttonPressed(rc) == 'cancel':
        return None

    new_values = {}
    new_values['vcpu_min'] = e_mincpu.value()
    new_values['vcpu'] = e_normcpu.value()
    new_values['memory_min'] = e_minmem.value()
    new_values['memory'] = e_normmem.value()
    new_values['template_name'] = e_name.value()

    return new_values
