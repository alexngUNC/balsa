`timescale 1ns/1ps
`ifndef AW
`define AW 8
`endif
`ifndef BW
`define BW 8
`endif
module compare_tb;
reg activate=0,init=1,ia=0,oa=0;
reg [`AW+`BW-1:0] data=0;
wire ir,orq,aa;
wire [3:0] result;
integer a=0,b=0,sa,sb,checked=0;
reg [3:0] expected;
bit signed_inputs;
Balsa_compare8 dut(.activate_0r(activate),.activate_0a(aa),.initialise(init),
 .command_0r(ir),.command_0a(ia),.command_0d(data),
 .result_0r(orq),.result_0a(oa),.result_0d(result));
initial begin
 signed_inputs=$test$plusargs("SIGNED");
 #20; init=0; #20; activate=1;
 for(a=0;a<(1<<`AW);a++) for(b=0;b<(1<<`BW);b++) begin
  sa=(signed_inputs && a>=(1<<(`AW-1)))?a-(1<<`AW):a;
  sb=(signed_inputs && b>=(1<<(`BW-1)))?b-(1<<`BW):b;
  expected={sa>=sb,sa>sb,sa<=sb,sa<sb};
  wait(ir===1); #1; data=(b<<`AW)|a; #1; ia=1;
  wait(ir===0); #1; ia=0;
  wait(orq===1); #1;
  if(result!==expected) $fatal(1,"FAIL: compare a=%0d b=%0d actual=%b expected=%b",sa,sb,result,expected);
  oa=1; wait(orq===0); #1; oa=0; checked++;
 end
 wait(ir===1); #10;
 $display("PASS: %0d input pairs; all four relational operators",checked);
 $finish;
end
initial begin #100000000; $fatal(1,"FAIL: timeout a=%0d b=%0d",a,b); end
endmodule
