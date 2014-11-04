#!/usr/bin/perl
use strict;

use SciPass::CLI;

sub main {

    my $cli = SciPass::CLI->new();
    my $success= $cli->login();
    if ($success){
	$cli->terminal_loop();
    }


}


&main;
