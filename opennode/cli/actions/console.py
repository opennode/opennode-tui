import os

def run_kvm():
    __run_shell('qemu:///system')

def run_openvz():
    ps1_string = "[vzctl --help | vzlist | vzctl enter CT | exit] #"
    os.system("PS1='%s ' bash --norc -i -r " % ps1_string)
    #__run_shell('openvz:///system')

def __run_shell(driver):
    os.system('virsh -c ' + driver)

