#!/usr/bin/perl

#--------------------------------------------------------------------
#----- SciPass CLI library
#-----
#----- Copyright(C) 2014 The Trustees of Indiana University
#--------------------------------------------------------------------
#----- $HeadURL:
#----- $Id:
#-----
#----- Library that acts as a CLI for the SciPass Webservices
#---------------------------------------------------------------------

package SciPass::CLI;

use strict;
use Term::ReadLine;    #using Term::ReadLine::Gnu however best practices say not to require it directly?
use GRNOC::Config;
use FindBin;
use Data::Dumper;
use Template;
use GRNOC::WebService::Client;
use Switch;

#use Text::Table;
our $VERSION = "1.0.0";

sub new {

    my $proto = shift;
    my $class = ref($proto) || $proto;

    my %attributes = (
        host     => undef,
        user     => undef,
        password => undef,
        timeout  => 30,
        debug    => 0,
        @_,
	);

    my $self = \%attributes;

    bless( $self, $class );

    $self->_init();

    return $self;

}

sub _init {
    my $self = shift;

    $self->{'config'} = GRNOC::Config->new( config_file => '/etc/SciPass/SciPass.xml');
    my $base_url              = 'http://localhost';
    my $port                  = '8080';
    $self->{history}       = [];
    $self->{history_index} = 0;

    $self->{'ws'} = GRNOC::WebService::Client->new(
        url     => "$base_url:$port/scipass/switches",
        uid     => 'test_user',
        passwd  => 'supersecretpassword',
        realm   => 'foo',
        usePost => 0,
	);

    $self->build_command_list();

    $self->{'term'} = Term::ReadLine->new('SciPass CLI');
    $self->set_prompt('SciPass#');

    my $attribs = $self->{'term'}->Attribs;

    #setting completion function up for Term::Readline
    my $cli = $self;
    $attribs->{completion_function} = sub {
        my ( $text, $line, $start ) = @_;
        $self->command_complete( $text, $line, $start );
    };

    return;
}

sub expand_commands {
    my $self  = shift;
    my $input = shift;

    my $new_text;

    my @input_parts = split( " ", $input );
    foreach my $input_part (@input_parts) {
        $input_part = quotemeta($input_part);
    }
    my $command_list  = $self->get_command_list();
    my $times_matched = 0;

    my $exact_matches   = {};
    my $partial_matches = {};

    #for each command, use exact match for each step avaliable,
    #bomb out if there are multiple partial matches

    foreach my $command (@$command_list) {
        my $matching_parts = 0;

        my @command_parts = split( " ", $command );
        for ( my $i = 0 ; $i < scalar(@input_parts) ; $i++ ) {

            unless ( $partial_matches->{$i} ) {
                $partial_matches->{$i} = {};
            }

            if ( $command_parts[$i] =~ /^$input_parts[$i]$/ ) {
                $exact_matches->{$i} = $command_parts[$i];
            }
            elsif ( $command_parts[$i] =~ /^$input_parts[$i].*/ ) {
                $matching_parts++;
                $partial_matches->{$i}->{ $command_parts[$i] } = 1;
		
                #print "$command_parts[$i] matches $input_parts[$i]\n";
            }

        }

    }
    for ( my $i = 0 ; $i < scalar(@input_parts) ; $i++ ) {
        if ( $exact_matches->{$i} ) {
            $new_text .= "$exact_matches->{$i} ";
        }
        elsif ( $partial_matches->{$i} && scalar( keys %{ $partial_matches->{$i} } ) == 1 ) {
            my @values = keys %{ $partial_matches->{$i} };

            $new_text .= "$values[0] ";
        }
        else {

            #no partial or exact matches, or multiple partial matches
            warn "command not found\n";
            return ( 1, $input );
        }
    }
    chop($new_text);
    return ( 0, $new_text );

}

sub command_complete {
    my $self = shift;

    my ( $text, $line, $start ) = @_;
    my $command_list = $self->get_command_list();
    my @matches_at_level;

    # $line= quotemeta($line);

    my @text_parts = split( " ", $line );
    foreach (@text_parts) {
        $_ = quotemeta($_);
    }
    if ( $line eq "" ) {

        #warn "Line is empty\n\n";
        my @return;
        foreach my $command (@$command_list) {
            my @command_parts = split( " ", $command );
            my $last_word = $command_parts[0];
            push( @return, $command_parts[0] );

        }
        return @return;
    }

    foreach my $command (@$command_list) {
        my $offset = 0;

        my $is_match      = 1;
        my @command_parts = split( " ", $command );
        my $last_word     = $command_parts[0];

        #default to assuming the whole line matches until we find a word that doesn't in our current depth
        #for n words in line
        # if all words match and there are no options after it.. this is a full command, woot you've hit the end of the line
        # if all words match and you have more than one match, your last word options should be all options that match at this depth
        # if all words match and there are no other matches at this depth, give next depth option

        #warn "number of parts in arry $#text_parts";
        for ( my $i = 0 ; $i <= $#text_parts ; $i++ ) {

            #    warn "command: $command_parts[$i], text:$text_parts[$i]\n";
            unless ( $matches_at_level[$i] ) {
                $matches_at_level[$i] = {};
            }
            unless ( $matches_at_level[ $i + 1 ] ) {
                $matches_at_level[ $i + 1 ] = {};
            }

            my $is_exact_match = 0;
            if ( $command_parts[$i] =~ /^$text_parts[$i].*/ ) {

                #print "matched $command_parts[$i]\n";
                #$last_word = $command_parts[$i];

                if ( $i == $#text_parts ) {

                    #print "adding at level $i\n";
                    #if we've started the next command only accept full matches for additions to the list of matches?
                    unless ( $line =~ /.*?\s+$/ ) {

                        #print "index $i, $command_parts[$i] matches $text_parts[$i]";
                        $matches_at_level[$i]->{ $command_parts[$i] } = 1;
                    }

                }
            }
            elsif ( $is_match && $i == $#text_parts && $text eq "" ) {

                #everything matches up to this point, add next option
                #$matches_at_level[$i]->{$command_parts[$i]} =1;
                #$matches_at_level[$i+1]->{$command_parts[$i+1]}=1; #=  $command_parts[$i+1];
            }
            else {
                if ( $i == $#text_parts ) {

                    # print "index $i, $command_parts[$i] does not match $text_parts[$i]";
                }
                $is_match = 0;
                last;
            }

            if ( $command_parts[$i] =~ /^$text_parts[$i]$/ ) {

                #exactly matches, so add current line and next line to matches at levels
                if ( $i == $#text_parts ) {

                    # print "index $i, $command_parts[$i] exactly matches $text_parts[$i]";
                    $matches_at_level[$i]->{ $command_parts[$i] } = 1;
                    $matches_at_level[ $i + 1 ]->{ $command_parts[ $i + 1 ] } = 1;
                }

            }

        }

        #if ($command =~ /^$line$/){
        #command is complete, perfect match don't add any options?
        #    return;
        #}

    }

    #warn Dumper (\@matches_at_level);
    #warn scalar(keys %{$matches_at_level[$#text_parts]});
    if ( $matches_at_level[$#text_parts] && ( scalar( keys %{ $matches_at_level[$#text_parts] } ) > 1 ) ) {

        #multiple matches at top level
        my @return = keys %{ $matches_at_level[$#text_parts] };

        #print "multiple matches at this level $#text_parts : returning ".Dumper(\@return);
        return @return;
    }
    if ( $matches_at_level[$#text_parts] && ( scalar( keys %{ $matches_at_level[$#text_parts] } ) == 1 ) ) {
        if ( $matches_at_level[ $#text_parts + 1 ] && scalar( keys %{ $matches_at_level[ $#text_parts + 1 ] } ) ) {
            my @return = keys %{ $matches_at_level[ $#text_parts + 1 ] };

            # print "Only one match at current level returning next level: ".Dumper(\@return);
            #return @return;
            return @return;
        }
        my @return = keys %{ $matches_at_level[$#text_parts] };

        #print "Only one match at current level and no next level matches yet: ".Dumper(\@return);
        return @return;
    }

    #print "found no matches at $#text_parts \n";
    return;

    #my @return = keys (%matches);
    #print Dumper (\%matches);
    #return @return;
}

#stubbed out in case we ever have a legitimate auth system for the WS.
sub login {

    my $self = shift;

    return 1;

}

sub build_command_list {

    my $self = shift;
    my $ws   = $self->{'ws'};

    my $base_url = $self->{'config'}->get('/config/base_url');
    my $port     = $self->{'config'}->get('/config/port');
    $base_url = 'http://localhost';
    $port     = '8080';

    my $possible_commands =  [ "show switches",
			       "show switch [% sw_name %] flows",
			       "show switch [% sw_name %] domains", 
			       "show switch [% sw_name %] domain [% domain_name %] status",
			       "show switch [% sw_name %] domain [% domain_name %] flows",
			       "show switch [% sw_name %] domain [% domain_name %] sensors",
			       "show switch [% sw_name %] domain [% domain_name %] sensor [% sensor_id %] status",
			       "show good flows", "show bad flows", "help", "?", "quit", "exit" ];
    
    my $tt  = Template->new() || die $Template::ERROR;
    
    foreach my $command (@$possible_commands){
	foreach my $switch (@{$self->{'config'}->get('/SciPass/switch')}) {
	    $self->{'switches'}->{$switch->{'dpid'}} = {name => $switch->{'name'}, dpid => $switch->{'dpid'}};
	    
	    $self->{'switch_names'}->{$switch->{'name'}}->{'dpid'} = $switch->{'dpid'};
	    if(ref($switch->{'domain'}) ne 'ARRAY'){
		my @domain = keys (%{$switch->{'domain'}});
		$switch->{'domain'}->{$domain[0]}->{'name'} = $domain[0];
		$switch->{'domain'} = [ $switch->{'domain'}->{$domain[0]} ];
	    }
	    foreach my $domain ( @{ $switch->{'domain'} }){
		push(@{$self->{'switches'}->{$switch->{'dpid'}}->{'domains'}},$domain);

		foreach my $sensor (keys (% {$domain->{'sensor_port'} })){
		    
		    my $vars;
		    $vars->{'sw_name'} = $switch->{'name'};
		    $vars->{'domain_name'} = $domain->{'name'};
		    $vars->{'sensor_id'} = $domain->{'sensor_port'}->{$sensor}->{'sensor_id'};
		    
		    my $new_command;
		    $tt->process(\$command, $vars, \$new_command) || die $tt->error() . "\n";
		    push(@{$self->{'possible_commands'}}, $new_command);
		    
		    $new_command = "";
		    $vars->{'sw_name'} = $switch->{'dpid'};
		    $tt->process(\$command, $vars, \$new_command) || die $tt->error() . "\n";
		    push(@{$self->{'possible_commands'}}, $new_command);
		}
	    }
	}
    }

    return;
}

sub get_command_list {
    my $self = shift;
    return $self->{'possible_commands'};
}

sub set_prompt {
    my $self = shift;
    $self->{'prompt'} = shift;
}

sub get_prompt {
    my $self = shift;
    return $self->{'prompt'};
}



sub handle_input {
    my $self        = shift;
    my $input       = shift;
    my $insert_text = 0;
    my $ws          = $self->{'ws'};
    my $base_url    = $self->{'config'}->get('/config/base_url');
    my $port        = $self->{'config'}->get('/config/port');
    $base_url = 'http://localhost';
    $port     = '8080';
    ( $insert_text, $input ) = $self->expand_commands($input);

    if ( $input =~ /^exit$/ || $input =~ /^quit$/ ) {
        exit;
    }
    if ( $input =~ /^help$/ || $input =~ /^\?$/ ) {
        print <<END;
show switches

     Returns details of each switch connected to SciPass:

show switch [sw_name] flows

     returns all of the flows currently installed on a switch

show switch [sw_name] domain [domain_name] status

     returns the current status of the domain

show switch [sw_name] domain [domain_name] flow

     returns the flows for the domain

show switch [sw_name] domain [domain_name] sensors

     returns the list of sensors in the domain

show switch [sw_name] domain [domain_name] sensor [sensor_id] status

     returns the status of the sensor

show good flows
 
     returns a list of currently bypassed flows

show bad flows

     returns a list of currently blocked flows

quit | exit
     exit application

help
    returns this message

END

    } elsif ( $input =~ /^show switches$/ ) {

        my $dpid = $1 || undef;
        $ws->set_url("$base_url:$port/scipass/switches");
        my $status_obj = $ws->foo();

        unless ( grep { defined $_ } @$status_obj ) {
            print "No switches found connected SciPass\n";
        }
        foreach my $switch (@$status_obj) {
            if ( $dpid && $switch->{'dpid'} != $dpid ) {
                next;
            }
            my ($address) = $switch->{'address'};
	    if(!defined($self->{'switches'}->{$switch->{'dpid'}})){
		print "UNCONFIGURED FOR SCIPASS\n";
	    }else{
		print "Name: " . $self->{'switches'}->{$switch->{'dpid'}}->{'name'} . "\n";
		$self->{'switches'}->{$switch->{'dpid'}}->{'status'} = 'active';
	    }
	    print "DPID:\t$switch->{'dpid'}\n";
            print "IP:\t$address\n";
	    print "STATUS: Connected\n";
            print "Ports:\n";
            print "Name\tPort Number\tStatus\n\n";

            foreach my $port ( @{ $switch->{'ports'} } ) {
                my $port_num = $port->{'port_no'};
                print "$port->{'name'}\t$port_num\tUP\n";
            }
            print "\n\n";
        }
	
	foreach my $dpid (keys (%{ $self->{'switches'}})){
	    next if ((defined($self->{'switches'}->{$dpid}->{'status'})) && ($self->{'switches'}->{$dpid}->{'status'} eq 'active'));
	    print "NAME:\t" . $self->{'switches'}->{$dpid}->{'name'} . "\n";
	    print "DPID:\t$dpid\n";
	    print "IP:\tNOT CONNECTED\n";
	    print "STATUS:\tNOT CONNECTED\n";
	    print "\n\n";
	}


    }elsif ( $input =~ /^show switch (\S+) flows$/ ) {
	
	my $switch_dpid = $1;
	if(defined($self->{'switch_names'}->{$switch_dpid})){
	    $switch_dpid = $self->{'switch_names'}->{$switch_dpid}->{'dpid'};
	}

	$ws->set_url("$base_url:$port/scipass/switch/$switch_dpid/flows");
	my $res = $ws->foo();
	if(!defined($res)){
	    print "No Flows configured for switch $1\n";
	    return;
	}

	foreach my $flow (@$res){
	    print "Flow:\n";
	    print $self->flow_to_human($flow) . "\n\n";
	}

    }elsif ( $input =~ /^show switch (\S+) domains/ ) {

	my $switch_dpid = $1;

        if(defined($self->{'switch_names'}->{$switch_dpid})){
            $switch_dpid = $self->{'switch_names'}->{$switch_dpid}->{'dpid'};
        }

	$ws->set_url("$base_url:$port/scipass/switch/$switch_dpid/domains");
	my $res = $ws->foo();
	if(!defined($res)){
            print "No Domains configured for switch $1\n";
            return;
        }

	foreach my $domain (@$res){
            print "Domain: " . $domain . "\n";
        }

    }elsif ( $input =~ /^show switch (\S+) domain (\S+) status/ ) {
	my $switch_dpid = $1;
        if(defined($self->{'switch_names'}->{$switch_dpid})){
	    $switch_dpid = $self->{'switch_names'}->{$switch_dpid}->{'dpid'};
	}

	$ws->set_url("$base_url:$port/scipass/switch/$switch_dpid/domain/$2/status");
	my $res = $ws->foo();
	print Data::Dumper::Dumper($res);

    }elsif( $input =~ /^show switch (\S+) domain (\S+) flows/){

	my $switch_dpid = $1;
	if(defined($self->{'switch_names'}->{$switch_dpid})){
            $switch_dpid = $self->{'switch_names'}->{$switch_dpid}->{'dpid'};
	}

	$ws->set_url("$base_url:$port/scipass/switch/$switch_dpid/domain/$2/flows");
	my $res = $ws->foo();

	if(!defined($res)){
	    print "Unable to fetch flows!\n\n";
	    return;
	}

	foreach my $flow (@$res){
	    print "Flow:\n";
	    print $self->flow_to_human($flow) . "\n\n";
	}


    }elsif( $input =~ /^show switch (\S+) domain (\S+) sensors/){
	my $switch_dpid = $1;
	if(defined($self->{'switch_names'}->{$switch_dpid})){
            $switch_dpid = $self->{'switch_names'}->{$switch_dpid}->{'dpid'};
	}
	$ws->set_url("$base_url:$port/scipass/switch/$switch_dpid/domain/$2/sensors");
	my $res = $ws->foo();

	if(!defined($res)){
	    print "Unable to find any sensors!!\n";
	    return;
	}
	
	warn Data::Dumper::Dumper($res);

	foreach my $sensor (@$res){
	    print "Sensor: " . $sensor . "\n";
	}

    }elsif( $input =~ /^show switch (\S+) domain (\S+) sensor (\S+) status/){
	my $switch_dpid = $1;
	if(defined($self->{'switch_names'}->{$switch_dpid})){
            $switch_dpid = $self->{'switch_names'}->{$switch_dpid}->{'dpid'};
	}
	$ws->set_url("$base_url:$port/scipass/switch/$switch_dpid/domain/$2/sensor/$3/status");
	my $res = $ws->foo();
	print Data::Dumper::Dumper($res);
    }
    
    return;    #$insert_text;
}

sub flow_to_human{
    my $self = shift;
    my $flow = shift;
    my $str = "";
    $str .= "DPID:\t" . $flow->{'dpid'} . "\n";
    $str .= "Match:\n";
    foreach my $key (keys (%{$flow->{'header'}})){
	my $of_match_name;
	switch($key){
	    case 'phys_port'{
		$of_match_name = 'IN PORT';
	    }case 'dl_vlan'{
		$of_match_name = 'VLAN';
	    }case 'dl_type'{
		$of_match_name = "Ether Type";
	    }case 'nw_src'{
		$of_match_name = "Source IP";
	    }case 'nw_src_mask'{
		$of_match_name = "Source IP Mask";
	    }case 'nw_dst'{
		$of_match_name = "Destination IP";
	    }case 'nw_dst_mask'{
		$of_match_name = "Destination IP Mask";
	    }case 'tp_src'{
		$of_match_name = "Source Port";
	    }case 'tp_dst'{
		$of_match_name = "Destination Port";
	    }
	}
	$str .= "  " . $of_match_name . ":" . $flow->{'header'}->{$key} . "\n";
    }

    $str .= "Actions:\n";
    
    if($#{$flow->{'actions'}} == -1){
	$str .= "  DROP";
    }

    foreach my $action (@{$flow->{'actions'}}){
	switch($action->{'type'}){
	    case 'output'{
		$str .= "  OUTPUT: " . $action->{'port'} . "\n";
	    }case 'set_vlan_vid'{
		$str .= "  SET VLAN ID: " . $action->{'vlan_vid'} . "\n";
	    }
	}
    }
    return $str;
}

sub terminal_loop {
    
    my $self = shift;
    
    my $line;
    my $term = $self->{'term'};
    my $insert_text;
    my $preput = "";
    while ( defined( $line = $term->readline( $self->get_prompt(), $preput ) ) ) {

        $insert_text = $self->handle_input($line);
        if ($insert_text) {
            $preput = $line;
        }
        else {
            $preput = "";
        }

    }

}


1;
