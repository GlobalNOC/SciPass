#
# spec file for package python-ryu
#
# Copyright (c) 2014 Andrew Ragusa.
#

Name:           python-ryu
Version:        3.11
Release:        0
Url:            http://osrg.github.io/ryu/
Summary:        Component-based Software-defined Networking Framework
License:        Apache-2.0
Group:          Development/Languages/Python
Source:         https://pypi.python.org/packages/source/r/ryu/ryu-%{version}.tar.gz
BuildRoot:      %{_tmppath}/%{name}-%{version}-build
BuildRequires:  python-devel

%description
What's Ryu
==========
Ryu is a component-based software defined networking framework.

Ryu provides software components with well defined API that make it
easy for developers to create new network management and control
applications. Ryu supports various protocols for managing network
devices, such as OpenFlow, Netconf, OF-config, etc. About OpenFlow,
Ryu supports fully 1.0, 1.2, 1.3, 1.4 and Nicira Extensions.

All of the code is freely available under the Apache 2.0 license. Ryu
is fully written in Python.


Quick Start
===========
Installing Ryu is quite easy::

   % pip install ryu

If you prefer to install Ryu from the source code::

   % git clone git://github.com/osrg/ryu.git
   % cd ryu; python ./setup.py install

If you want to use Ryu with `OpenStack <http://openstack.org/>`_,
please refer `detailed documents <http://ryu.readthedocs.org/en/latest/using_with_openstack.html>`_.
You can create tens of thousands of isolated virtual networks without
using VLAN.  The Ryu application is included in OpenStack mainline as
of Essex release.

If you want to write your Ryu application, have a look at
`Writing ryu application <http://ryu.readthedocs.org/en/latest/writing_ryu_app.html>`_ document.
After writing your application, just type::

   % ryu-manager yourapp.py


Support
=======
Ryu Official site is `<http://osrg.github.io/ryu/>`_.

If you have any
questions, suggestions, and patches, the mailing list is available at
`ryu-devel ML
<https://lists.sourceforge.net/lists/listinfo/ryu-devel>`_.
`The ML archive at Gmane <http://dir.gmane.org/gmane.network.ryu.devel>`_
is also available.

%prep
%setup -q -n ryu-%{version}

%build
python setup.py build

%install
python setup.py install --prefix=%{_prefix} --root=%{buildroot}

%clean
rm -rf %{buildroot}

%files
%defattr(-,root,root,-)
%{python_sitelib}/*
/usr/bin/ryu
/usr/bin/ryu-manager
/usr/etc/ryu/ryu.conf

%changelog
