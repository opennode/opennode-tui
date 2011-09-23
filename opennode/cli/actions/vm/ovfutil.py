import warnings

from ovf import Ovf

# Methods adopted from ovf.Ovf

def get_ovf_vcpu(ovf_file):
    """
    Retrieves the number of virtual CPUs to be allocated for the virtual
    machine from the Ovf file.
    """
    result = {"min": None, "normal": None, "max": None}
    virtual_hardware_node = ovf_file.document.getElementsByTagName("VirtualHardwareSection")[0] 
    rasd = Ovf.getDict(virtual_hardware_node)['children']
    for resource in rasd:
        if(resource.has_key('rasd:ResourceType') and
           resource['rasd:ResourceType'] == '3'):
            
            if "attr" in resource and "bound" in resource["attr"]:
                bound = resource["attr"]["bound"]
            else:
                bound = "normal"
            result[bound] = resource['rasd:VirtualQuantity'] 
    return result["min"], result["normal"], result["max"]

def get_ovf_memory_gb(ovf_file):
    """
    Retrieves the maximum amount of memory (kB) to be allocated for the
    virtual machine from the Ovf file.

    @note: DSP0004 v2.5.0 outlines the Programmatic Unit forms for
    OVF. This pertains specifically to rasd:AllocationUnits, which accepts
    both the current and deprecated forms. New implementations should not
    use Unit Qualifiers as this form is deprecated.
        - PUnit form, as in "byte * 2^20"
        - PUnit form w/ Units Qualifier(deprecated), as in "MegaBytes"

    @param virtualHardware: Ovf VirtualSystem Node
    @type virtualHardware: DOM Element

    @param configId: configuration name
    @type configId: String

    @return: memory in kB
    @rtype: String
    """
    memory = ''
    result = {"min": None, "normal": None, "max": None}

    virtual_hardware_node = ovf_file.document.getElementsByTagName("VirtualHardwareSection")[0]
    rasd = Ovf.getDict(virtual_hardware_node)['children']
    for resource in rasd:
        if(resource.has_key('rasd:ResourceType') and
           resource['rasd:ResourceType'] == '4'):
            memoryQuantity = resource['rasd:VirtualQuantity']
            memoryUnits = resource['rasd:AllocationUnits']
            
            if "attr" in resource and "bound" in resource["attr"]:
                bound = resource["attr"]["bound"]
            else:
                bound = "normal"

            if(memoryUnits.startswith('byte') or
                 memoryUnits.startswith('bit')):
                # Calculate PUnit numerical factor
                memoryUnits = memoryUnits.replace('^','**')

                # Determine PUnit Quantifier DMTF DSP0004, {byte, bit}
                # Convert to kilobytes
                memoryUnits = memoryUnits.split(' ', 1)
                quantifier = memoryUnits[0]
                if quantifier == 'byte':
                    memoryUnits[0] = '2**-10'
                elif quantifier == 'bit':
                    memoryUnits[0] = '2**-13'
                else:
                    raise ValueError("Incompatible PUnit quantifier for memory.")

                memoryUnits = ' '.join(memoryUnits)
                memoryFactor = int(eval(memoryUnits))

            else:
                if memoryUnits.startswith('Kilo'):
                    memoryFactor = 1024**0
                elif memoryUnits.startswith('Mega'):
                    memoryFactor = 1024**1
                elif memoryUnits.startswith('Giga'):
                    memoryFactor = 1024**2
                else:
                    raise ValueError("Incompatible PUnit quantifier for memory.")

                if memoryUnits.endswith('Bytes'):
                    memoryFactor *= 1
                elif memoryUnits.endswith('Bits'):
                    memoryFactor *= 0.125
                else:
                    raise ValueError("Incompatible PUnit quantifier for memory.")
                warnings.warn("DSP0004 v2.5.0: use PUnit Qualifiers",
                              DeprecationWarning)

            memory = str(float(memoryQuantity) * memoryFactor / 1024 ** 2)
            result[bound] = memory 

    return result["min"], result["normal"], result["max"]
