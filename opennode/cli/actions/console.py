import os

def run_kvm():
    __run_shell('qemu:///system')

def run_openvz():
    __run_shell('openvz:///system')

def __run_shell(driver):
    os.system('virsh -c ' + driver)

