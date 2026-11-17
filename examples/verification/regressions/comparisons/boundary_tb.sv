`timescale 1ns/1ps
module mixed_tb;
reg activate=0,initialise=1,input_ack=0,output_ack=0;
reg [`AW+`BW-1:0] input_data=0;
wire input_request,output_request;
wire [3:0] output_data;
reg [`AW+`BW+3:0] vectors[0:127];
integer count,index=0,failures=0;
string path;
CompareAdapter dut(activate,initialise,input_request,input_ack,input_data,output_request,output_ack,output_data);
initial begin
 if(!$value$plusargs("VECTORS=%s",path) || !$value$plusargs("N=%d",count)) $fatal(1,"FAIL: arguments");
 if(count<1 || count>128) $fatal(1,"FAIL: vector count");
 $readmemh(path,vectors,0,count-1);
 #20;initialise=0;#20;activate=1;
 for(index=0;index<count;index++) begin
  if((^vectors[index])===1'bx) $fatal(1,"FAIL: unknown vector");
  wait(input_request===1);#1;input_data=vectors[index][`AW+`BW+3:4];#1;input_ack=1;
  wait(input_request===0);#1;input_ack=0;
  wait(output_request===1);#1;
  if(output_data!==vectors[index][3:0]) begin
   failures++;
   $display("MISMATCH %0d actual=%b expected=%b",index+1,output_data,vectors[index][3:0]);
  end
  output_ack=1;wait(output_request===0);#1;output_ack=0;
 end
 $display("CHECKED %0d FAILURES %0d",count,failures);
 if(failures) $fatal(1,"FAIL: mixed-sign comparisons");
 $display("PASS: mixed-sign boundary comparisons");$finish;
end
initial begin #1000000;$fatal(1,"FAIL: handshake timeout index=%0d",index);end
endmodule
