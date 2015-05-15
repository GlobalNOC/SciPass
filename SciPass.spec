Summary: Science DMZ and IDS loadbalancer via OpenFlow RYU
Name: SciPass
Version: 0.9.1
Release: 1
License: Apache2
Group: GRNOC
URL: http://globalnoc.iu.edu
Source0: %{name}-%{version}.tar.gz
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-root
Requires: ryu >= 3.18
Requires: perl-Term-ReadLine-Gnu
Requires: python-ipaddr
Requires: WebOb >= 1.3.1
Requires: python-netaddr
Requires: python-oslo-config >= 1.2.0

%description
SciPass is a Science DMZ and IDS load balance via OpenFlow and Ryu

%prep
%setup -q

%build

%install
rm -rf $RPM_BUILD_ROOT
%{__install} -d -p %{buildroot}/%{python_sitelib}/SciPass/
%{__install} -d -p %{buildroot}/%{perl_vendorlib}/SciPass/
%{__install} -d -p %{buildroot}/etc/SciPass/
%{__install} -d -p %{buildroot}/etc/init.d
%{__install} -d -p %{buildroot}/usr/bin/
%{__install} python/*.py %{buildroot}/%{python_sitelib}/SciPass/
%{__install} perl/lib/SciPass/*.pm %{buildroot}/%{perl_vendorlib}/SciPass/
%{__install} etc/SciPass.xml %{buildroot}/etc/SciPass/
%{__install} etc/ryu.conf %{buildroot}/etc/SciPass/
%{__install} etc/scipass-init %{buildroot}/etc/init.d/scipass
%{__install} perl/bin/scipass-cli.pl %{buildroot}/usr/bin/scipass-cli.pl

%clean
rm -rf $RPM_BUILD_ROOT


%files
%defattr(-,root,root,-)
/etc/init.d/scipass
%config(noreplace) /etc/SciPass/SciPass.xml
/etc/SciPass/ryu.conf
%{python_sitelib}/SciPass/*
%{perl_vendorlib}/*

%defattr(754, root, root, -)
/usr/bin/scipass-cli.pl

%doc


%changelog
* Fri Jul 25 2014 aragusa <aragusa@scipass-dev.grnoc.iu.edu> - 
- Initial build.
