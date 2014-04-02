OpenNode Textual User Interface (TUI)
-------------------------------------

Opennode TUI contains a library of typical actions performed on OpenNode node and an ncurses-based user interface for typical operations.

Actions are wrapped as [Saltstack](http://saltstack.com/) modules and can be called remotely.


Installation
============

A preferred method of installation by installing RPM packages. The latest RPMs can be downloaded from the Opennode repository: http://www.opennodecloud.com/CentOS/6/opennode-dev/x86_64/RPMS/

For development, do the following:

 1. yum install python-devel gcc gcc-c++ autoconf automake newt-python
 2. pip install -r requirements.txt
 3. git clone git@github.com:opennode/opennode-tui.git

Running
=======
 1. Make sure scripts/ are on the PATH.
 2. Due to a number of reasons a common way for updating environment is by running a sync script. Example script is simple-sync.sh
 3. Run 'scripts/opennode'


License
=======

TUI specific code is licensed under Apache License v2. Libraries used in TUI can be more restrictive.
(c) Opennode Ltd.

Contact
=======

Please report bugs to Github issues or to info@opennodecloud.com.
