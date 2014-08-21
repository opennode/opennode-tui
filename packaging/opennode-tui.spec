%{!?python_sitelib: %global python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print get_python_lib()")}

Summary: OpenNode Textual User Interface RPM
Name: opennode-tui
Version: 2.0.0
Release: 1.on
License: GPL
Group: System Environment/Shells
URL: http://opennodecloud.com
Vendor: OpenNode LLC <info@opennodecloud.com>
Packager: OpenNode LLC <info@opennodecloud.com>
Source0: opennode-tui-2.0.0.tar.gz
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)
BuildRequires: python-setuptools
Requires: libvirt
Requires: open-ovf
Requires: python-netifaces
Requires: libguestfs-tools
Requires: progressbar
Requires: salt-minion
Requires: smolt
Requires: newt-python
Requires: python-hivex
Requires: python-libguestfs

%description
This package contains the OpenNode Textual User Interface for the OpenNode cloud toolkit.

%prep
%setup -q -n %{name}-%{version}

%build
%{__python} -c 'import setuptools; execfile("setup.py")' build

%install
[ "%{buildroot}" != "/" ] && rm -rf %{buildroot}
%{__python} setup.py install -O1 --skip-build --root %{buildroot}

#Create directories for files
mkdir -p $RPM_BUILD_ROOT/opt/opennode/bin/
mkdir -p $RPM_BUILD_ROOT/etc/opennode/
mkdir -p $RPM_BUILD_ROOT/etc/profile.d/
mkdir -p $RPM_BUILD_ROOT/var/spool/opennode

# create default storage endpoint
mkdir -p $RPM_BUILD_ROOT/storage/local
mkdir -p $RPM_BUILD_ROOT/storage/local/iso
mkdir -p $RPM_BUILD_ROOT/storage/local/images
mkdir -p $RPM_BUILD_ROOT/storage/local/openvz/unpacked
mkdir -p $RPM_BUILD_ROOT/storage/local/kvm/unpacked

#Copy files to system
cp scripts/* $RPM_BUILD_ROOT/opt/opennode/bin/
cp conf/opennode-tui.conf $RPM_BUILD_ROOT/etc/opennode/
cp conf/openvz.conf $RPM_BUILD_ROOT/etc/opennode/
cp conf/kvm.conf $RPM_BUILD_ROOT/etc/opennode/
cp opennode-tui.sh $RPM_BUILD_ROOT/etc/profile.d/

%clean
[ "%{buildroot}" != "/" ] && rm -rf %{buildroot}

%post
mkdir -p /var/spool/opennode
%{__python} -c "from opennode.cli.actions import storage; storage.add_pool('local')"

target_salt=%{python_sitelib}/salt/modules/onode

# only set symlink if not already present
if [ ! -L $target_salt ]; then
    ln -sf %{python_sitelib}/opennode/cli/actions $target_salt
fi

# a workaround for salt getting stuck if salt-master is not reachable (TUI-47)
if [ -e /etc/salt/minion ]; then
    sed -i '/retry_dns:/ c retry_dns: 0' /etc/salt/minion
fi

%files
%defattr(-,root,root,-)
%{python_sitelib}/opennode*
/opt/opennode/bin
/etc/opennode
/etc/profile.d/opennode-tui.sh

%changelog
* Thu Jan 17 2013 Ilja Livenson <ilja@opennodecloud.com>
- Remove salt-minion restart from the pot-install actions

* Sun Nov 26 2012 Ilja Livenson <ilja@opennodecloud.com>
- Replaced Func dependencies with Salt

* Mon Nov 28 2011 Andres Toomsalu <andres@opennodecloud.com>
- Fixing issue #59 - func modules need to be copied not symlinked

* Thu Nov 17 2011 Andres Toomsalu <andres@opennodecloud.com>
- First packaging of opennode-tui as a separate rpm.
