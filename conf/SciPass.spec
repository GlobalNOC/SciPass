Summary: Science DMZ and IDS loadbalancer via OpenFlow RYU
Name: SciPass
Version: 1.0.0
Release: 1
License: Apache2
Group: GRNOC
URL: 
Source0: %{name}-%{version}.tar.gz
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-root
Requires: ryu

%description
SciPass is a Science DMZ and IDS load balance via OpenFlow and Ryu

%prep
%setup -q

%build

%install
rm -rf $RPM_BUILD_ROOT
%{__install} -d -p %{python_sitelib}/SciPass/
%{__install} python/* %{python_sitelib}/SciPass/

%clean
rm -rf $RPM_BUILD_ROOT


%files
%defattr(-,root,root,-)
/etc/init.d/scipass
/etc/SciPass/SciPass.conf
%{python_sitelib}/SciPass/*
%doc


%changelog
* Fri Jul 25 2014 aragusa <aragusa@scipass-dev.grnoc.iu.edu> - 
- Initial build.

