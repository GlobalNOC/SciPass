@load base/protocols/ftp
@load base/utils/exec

#@load base/protocols/ftp/gridftp
#module GridFTP;

function signalSciPass(c: connection)
         {
                local anagram : Exec::Command;
                
                local prog = fmt("curl -X PUT -d '{\"nw_dst\":\"%s/32\", \"nw_src\":\"%s/32\", \"tp_src\":\"%d\", \"tp_dst\":\"%d\"}' http://scipass-controller:8080/scipass/flows/good_flow",
                                  c$id$resp_h, c$id$orig_h,c$id$orig_p, c$id$resp_p);
                #print prog;
                local param = "";
                anagram = [$cmd = prog, $stdin = param];
		when ( local result = Exec::run(anagram))
		     {
			if ( result$exit_code != 0 )
			     {
			     return;
			     }
	             }
		     return;
         }

event bro_init()
      {
        print "BRO Starting";
      }


event ftp_request(c: connection, command: string, arg: string)
      {
        #print fmt("FTP REQUEST!! command: %s args: %s", command, arg);

      }

event ftp_reply(c: connection, code: count, msg: string, cont_resp: bool)
      {
        #print fmt("FTP REPLY!! code: %d, msg: %s", code, msg);
      }



event file_over_new_connection(f: fa_file, c: connection, is_orig: bool)
      {
        print "FILE TRANSFER STARTED!";
	signalSciPass(c);
      }