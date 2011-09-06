"""Constants for OpenNode CLI"""

KVM_VIRT_INSTALL = "virt-install "
KVM_QEMU_IMG = "qemu-img "

DRIVE_LETTERS = ["a","b","c","d","e","f","g","h","i","j","k","l","m","n","o","p","q","r","s","t","u","v","w","x","y","z"]

SYSTEM_ARCHES = ["x86_64", "i686"]
KVM_VIRT_TYPES = ["hvm"]
KVM_FEATURES = ["acpi", "apic", "pae"]

OS_VARIANTS = ["linux","rhel2.1","rhel3","rhel4","rhel5","centos5","fedora5","fedora6","fedora7","sles10","debianEtch","debianLenny",
               "generic26","generic24","windows","winxp","win2k","win2k3","vista","unix","solaris9","solaris10","freebsd6","openbsd4",
               "other","msdos","netware4","netware5","netware6"]

OS_TYPES = ["linux","windows","unix","other"]

OPENVZ_DEFAULT_MEMORY = 256
OPENVZ_DEFAULT_DISK = 2048
OPENVZ_DEFAULT_VCPU = 1
OPENVZ_DEFAULT_VCPULIMIT = 50

KVM_DEFAULT_MEMORY = 256
KVM_DEFAULT_VCPU = 1

OPENVZ_CONF_CREATOR_OPTIONS = ["NUMPROC", "AVNUMPROC", "NUMTCPSOCK", "NUMOTHERSOCK", "VMGUARPAGES", "KMEMSIZE", "TCPSNDBUF", "TCPRCVBUF",
                               "OTHERSOCKBUF", "DGRAMRCVBUF", "OOMGUARPAGES", "PRIVVMPAGES", "LOCKEDPAGES", "SHMPAGES", "PHYSPAGES",
                               "DCACHESIZE", "NUMFILE", "NUMFLOCK", "NUMPTY", "NUMSIGINFO", "NUMIPTENT", "DISKSPACE", "DISKINODES", 
                               "QUOTATIME", "CPUUNITS", "CPULIMIT", "CPUS", "IP_ADDRESS", "NAMESERVER", "SEARCHDOMAIN", "ONBOOT"]

DIR_OFFSET = ''

MIRROR_LIST = 'http://opennode.activesys.org/mirrorlist.txt'

TEMPLATE_DIR_OPENVZ = 'templates/openvz/' 
TEMPLATE_DIR_KVM = 'templates/kvm/'

TEMPLATE_ROOT_DIR = DIR_OFFSET+'/storage/'

LOCAL_TEMPLATE_LIST_DIR = DIR_OFFSET+'/opt/opennode/var/'

MINION_CONF = DIR_OFFSET+'/etc/certmaster/minion.conf'

FILE_BASED_IMAGE_DIR = DIR_OFFSET+'/storage/images/'

ISO_IMAGE_DIR = DIR_OFFSET+'/storage/iso/'

INSTALL_TEMPLATE_OPENVZ = DIR_OFFSET+'/vz/private/'
INSTALL_CONFIG_OPENVZ = DIR_OFFSET+'/etc/vz/conf/'

DEPLOY_TEMPLATE_OPENVZ = DIR_OFFSET+TEMPLATE_ROOT_DIR+TEMPLATE_DIR_OPENVZ+'deploy/'
ORIGINAL_TEMPLATE_OPENVZ = DIR_OFFSET+'/vz/template/cache/'

DEPLOY_TEMPLATE_KVM = DIR_OFFSET+TEMPLATE_ROOT_DIR+TEMPLATE_DIR_KVM+'deploy/'

TEMPLATE_KVM = DIR_OFFSET+TEMPLATE_ROOT_DIR+TEMPLATE_DIR_KVM
TEMPLATE_OPENVZ = DIR_OFFSET+TEMPLATE_ROOT_DIR+TEMPLATE_DIR_OPENVZ

LOG_FILENAME = DIR_OFFSET+'/var/log/opennode.log'

