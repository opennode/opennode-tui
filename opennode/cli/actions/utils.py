import os
import errno
import commands
import subprocess
import shlex
import ConfigParser
import shutil
import urllib
import urlparse
import cPickle as pickle
import tarfile

from progressbar import Bar, ETA, FileTransferSpeed, Percentage, ProgressBar, RotatingMarker

from openvz_exit_status import OpenVZ_EXIT_STATUS
from opennode.cli.log import get_logger
from opennode.cli.config import get_config


class CommandException(Exception):

    def __init__(self, msg, code=None):
        super(CommandException, self).__init__(msg)
        self.code = code
        get_logger().error('Command exception: %s', msg)


class TemplateException(Exception):

    def __init__(self, msg):
        super(TemplateException, self).__init__(msg)


def mkdir_p(path):
    """Emulates mkdir -p. http://stackoverflow.com/questions/600268/mkdir-p-functionality-in-python"""
    try:
        os.makedirs(path)
    except OSError as exc:
        if exc.errno != errno.EEXIST:
            raise


def delete(fnm):
    """Delete a filename, suppress exception on a missing file."""
    try:
        os.unlink(fnm)
    except OSError:
        pass


def del_folder(path):
    shutil.rmtree(path)


def get_file_size_bytes(path):
    return int(os.stat(path)[6])


def execute(cmd):
    """
    Run cmd in a shell, return output of the execution. Raise exception for
    non-0 return code. vzctl gets special treatment.
    TODO: add other vz family commmands
    """
    get_logger().debug('execute cmd: %s', cmd)
    status, output = commands.getstatusoutput("LC_ALL=C %s" % cmd)
    if status != 0:
        if cmd.startswith('vzctl'):
            raise CommandException("Failed to execute command '%s'. Status: '%s'. Message: '%s'. Output: '%s'"
                                   % (cmd, status>>8, OpenVZ_EXIT_STATUS[cmd.split(' ')[0]], output), status>>8)
        raise CommandException("Failed to execute command '%s'. Status: '%s'. Output: '%s'"
                               % (cmd, status, output), status)
    get_logger().debug('execute returned: %s', output)
    return output


def execute2(cmd):
    get_logger().debug('execute2 cmd: %s', cmd)
    args = shlex.split(cmd)
    p = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    while(True):
        retcode = p.poll()  # returns None while subprocess is running
        line = p.stdout.readline()
        yield line
        if(retcode is not None):
            break


def calculate_hash(target_file):
    """Hash contents of a file and write hashes out to a file"""
    execute("pfff -k 6996807 -B \"%s\" > \"%s\".pfff" % (target_file, target_file))


def execute_in_screen(name, cmd):
    """Create a named screen session and run command there"""
    execute('screen -S %s %s' % (name, cmd))


def attach_screen(name):
    """Attached to the named screen session (multi-screen mode)"""
    execute('screen -x -r %s' % name)


class SimpleConfigParser(ConfigParser.ConfigParser):
    """ Parses configuration file without sections. """
    COMMENT_CHAR = '#'
    OPTION_CHAR = '='

    def __init__(self):
        ConfigParser.ConfigParser.__init__(self)
        self.options = {}

    def get(self, key):
        return self.options[key]

    def items(self):
        return self.options

    def read(self, filename):
        with open(filename) as configfile:
            for line in configfile:
                # First, remove comments:
                if self.COMMENT_CHAR in line:
                    # split on comment char, keep only the part before
                    line, comment = line.split(self.COMMENT_CHAR, 1)
                # Second, find lines with an option=value:
                if self.OPTION_CHAR in line:
                    # split on option char:
                    option, value = line.split(self.OPTION_CHAR, 1)
                    # strip spaces:
                    option = option.strip()
                    value = value.strip()
                    # store in dictionary:
                    self.options[option] = value


class ConsoleProgressBar(object):
    """A progress bar compatible with urllib download hook"""
    pbar = None

    def update_url(self, url):
        if self.pbar.start_time is not None and self.pbar.finished is False:
            self.finish()
        self.pbar.maxval = None

    def __init__(self, tmpl_name):
        widgets = [tmpl_name, Percentage(), ' ', Bar(marker=RotatingMarker()),
                   ' ', ETA(), ' ', FileTransferSpeed()
               ]

        self.pbar = ProgressBar(widgets=widgets)

    def download_hook(self, count, blockSize, totalSize):
        if self.pbar.maxval is None:
            self.pbar.maxval = totalSize
            self.pbar.start()
        self.pbar.update(min(self.pbar.maxval, blockSize * count))

    def finish(self):
        self.pbar.finish()


class BasicURLOpener(urllib.FancyURLopener):
    """URL opener capable of basic HTTP authentication. """
    def __init__(self, username=None, password=None):
        urllib.FancyURLopener.__init__(self)
        self.username = username
        self.password = password

    def prompt_user_passwd(self, host, realm):
        return (self.username, self.password)


def download(remote, local):
    """Download a remote file to a local file, using optional username/password
    for basic HTTP authentication. Using cURL as external dependency"""
    msg = "Getting remote file %s" % remote
    get_logger().info(msg)
    print msg
    url = urlparse.urlsplit(remote)
    if url.username:
        if 'http_proxy' in os.environ:
            if url.password:
                remote = remote.replace('%s:%s@' % (url.username, url.password), '')
                userauth = '%s:%s' % (url.username, url.password)
            else:
                remote = remote.replace('%s@' % url.username, '')
                userauth = url.username
            subprocess.call(['curl', '--anyauth', 
                             '--user', userauth,
                             '-C', '-', '-o', '%s' % local, '%s' % remote])
    else:
        subprocess.call(['curl', '-C', '-', '-o', '%s' % local, '%s' % remote])


def urlopen(remote):
    """Return a response to a remote URL. Supports username:password@url schema
    for remote URL"""
    url = urlparse.urlsplit(remote)
    opener = BasicURLOpener(url.username, url.password)
    return opener.open(remote)


def roll_data(filename, data, default=None):
    """Save data in a file. Return previous value of the data."""
    try:
        if os.path.exists(filename):
            with open(filename, 'r') as od:
                res = pickle.load(od)
            with open(filename, 'w') as od:
                pickle.dump(data, od)
            return res
        else:
            with open(filename, 'w') as od:
                pickle.dump(data, od)
            return default
    except EOFError:
        return default


def test_passwordless_ssh(remote_host, port=22):
    """Test passwordless ssh connection from the current host to the specified remote host"""
    try:
        execute("ssh -q -oProtocol=2 -oBatchMode=yes -oStrictHostKeyChecking=no -p %s "
                "root@%s /bin/true" % (port, remote_host))
        return True
    except CommandException:
        return False


def setup_passwordless_ssh(remote_host):
    """Execute a script for setting up a passwordless login to the target host"""
    execute("ssh-keyput root@%s" % remote_host)


def save_to_tar(tar_filename, filelist):
    """ save_to_flat_tar(tar_filename, filelist)
    Save files to tar file.
    'tar_filename' is desired name for tar archive
    'filelist' is list of filename to be added to tar
    [(filename_on_disk, filename in archive),]"""
    tmpl = tarfile.open(tar_filename, 'w')
    for f in filelist:
        tmpl.add(f[0], arcname=f[1])
    tmpl.close()


def generate_filelist(template_type, template_name, new_name = None):
    if new_name is None:
        new_name = template_name
    unpacked_base = get_unp_base(template_type)
    filenames = []
    filenames.append((os.path.join(unpacked_base, template_name + '.scripts.tar.gz'),
                      new_name+'.scripts.tar.gz'))
    filenames.append((os.path.join(unpacked_base, template_name + '.tar.gz'),
                      new_name+'.tar.gz'))
    filenames.append((os.path.join(unpacked_base, template_name + '.ovf'),
                      new_name+'.ovf'))
    return filenames


def update_referenced_files(ovf_file, template_name, new_name):
    VirtualSystem = ovf_file.document.getElementsByTagName('VirtualSystem')
    VirtualSystem[0].attributes['ovf:id'].value = new_name
    References = ovf_file.document.getElementsByTagName('References')
    # TODO: until our packaged templates contain incorrect .ovf
    # we can not rely on files defined in References section
    for ref_node in References:
        file_nodes = ref_node.getElementsByTagName('File')
        for item in file_nodes:
            if item.attributes['ovf:href'].value == template_name + '.tar.gz':
                item.attributes['ovf:href'].value = new_name + '.tar.gz'
    return ovf_file


def get_unp_base(vm_type):
    return os.path.join(get_config().getstring('general', 'storage-endpoint'),
                        get_config().getstring('general', 'default-storage-pool'),
                        vm_type, 'unpacked')
