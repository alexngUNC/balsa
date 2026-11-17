`timescale 1ns/1ps
`ifndef balsa_init_time
  `define balsa_init_time 20
`endif

module dot_product_tb;
  localparam integer MAX_VECTORS = 4096;
  reg [81:0] vectors [0:MAX_VECTORS-1];
  integer n = 0, checked = 0, requests = 0, transaction = 0;
  reg activate_r = 0, initialise = 1, input_a = 0, output_a = 0;
  wire activate_a, input_r, output_r;
  reg [63:0] input_d = 0;
  wire [17:0] output_d;
  reg checking = 0, holding = 0, forbid_output = 0;
  reg [17:0] held_data;
  bit delayed, bad_expected, stall_output;
  string vector_file, scenario;
  reg [31:0] rng = 32'h0573d074;
  time response_in, response_out, return_delay = 2ns;
  reg [63:0] command, previous_command;
  integer reference, previous_result = -1;
  integer pair_hits [0:3][0:7][0:7];
  integer edge_hits [0:3][0:5][0:5];
  integer pair_bins = 0, edge_bins = 0, maxima = 0, wide_results = 0;
  integer repeats = 0, cleared = 0;
  integer av, bv, ai, bi;
  bit isolated;

  Balsa_dot4 dut (
    .activate_0r(activate_r), .activate_0a(activate_a), .initialise(initialise),
    .operands_0r(input_r), .operands_0a(input_a), .operands_0d(input_d),
    .result_0r(output_r), .result_0a(output_a), .result_0d(output_d)
  );

  function automatic integer bit_index(input integer value);
    bit_index = -1;
    for (integer i = 0; i < 8; i++)
      if (value == (1 << i)) bit_index = i;
  endfunction
  function automatic integer edge_index(input integer value);
    case (value)
      0: edge_index = 0;
      1: edge_index = 1;
      127: edge_index = 2;
      128: edge_index = 3;
      254: edge_index = 4;
      255: edge_index = 5;
      default: edge_index = -1;
    endcase
  endfunction

  task automatic wait_request(input bit result_channel, input bit level);
    fork
      begin wait ((result_channel ? output_r : input_r) === level); end
      begin
        #10000ns;
        if (result_channel && level)
          $fatal(1, "FAIL: timeout waiting result request high, transaction %0d", transaction);
        else if (result_channel)
          $fatal(1, "FAIL: timeout waiting result request low, transaction %0d", transaction);
        else if (level)
          $fatal(1, "FAIL: timeout waiting input request high, transaction %0d", transaction);
        else
          $fatal(1, "FAIL: timeout waiting input request low, transaction %0d", transaction);
      end
    join_any
    disable fork;
  endtask

  task automatic exchange(input reg [63:0] operands, input reg [17:0] expected);
    reg [17:0] wanted;
    wait_request(0, 1);
    #response_in;
    if (input_r !== 1 || input_a !== 0)
      $fatal(1, "FAIL: input request withdrawn before acknowledgement");
    input_d = operands;
    #2ns;
    input_a = 1;
    wait_request(0, 0);
    #return_delay;
    input_a = 0;
    #1ns;
    wait_request(1, 1);
    #response_out;
    if (output_r !== 1 || output_a !== 0)
      $fatal(1, "FAIL: result request withdrawn before acknowledgement");
    if (output_d !== expected)
      $fatal(1, "FAIL: result mismatch transaction=%0d actual=%0d expected=%0d",
             transaction, output_d, expected);
    wanted = expected;
    if (bad_expected && transaction == 1) wanted = expected ^ 18'd1;
    if (output_d !== wanted)
      $fatal(1, "FAIL: injected expected-value mismatch actual=%0d expected=%0d", output_d, wanted);
    held_data = output_d;
    holding = 1;
    if (stall_output && transaction == 1)
      $display("INJECT: withholding result acknowledgement");
    else
      output_a = 1;
    wait_request(1, 0);
    holding = 0;
    if (stall_output && transaction == 1)
      $fatal(1, "FAIL: result request withdrawn without acknowledgement");
    #return_delay;
    output_a = 0;
    #1ns;
    checked++;
    $display("CHECK: transaction=%0d result=%0d", transaction, expected);
  endtask

  always @(input_r or output_r or activate_a) begin
    if (checking) begin
      if ((input_r !== 0 && input_r !== 1) || (output_r !== 0 && output_r !== 1))
        $fatal(1, "FAIL: unknown request signal");
      if (activate_a !== 0) $fatal(1, "FAIL: permanent circuit acknowledged activation");
    end
  end
  always @(output_d)
    if (holding && output_d !== held_data)
      $fatal(1, "FAIL: result changed before request returned low");
  always @(posedge output_r)
    if (checking) begin
      requests++;
      if (forbid_output || requests > n) $fatal(1, "FAIL: unexpected extra result");
    end

  initial begin
    delayed = $test$plusargs("DELAYED");
    bad_expected = $test$plusargs("BAD_EXPECTED");
    stall_output = $test$plusargs("STALL_OUTPUT");
    if (!$value$plusargs("VECTORS=%s", vector_file) ||
        !$value$plusargs("NUM_VECTORS=%d", n) ||
        !$value$plusargs("SCENARIO=%s", scenario))
      $fatal(1, "FAIL: missing vectors/count/scenario arguments");
    if (n < 1 || n > MAX_VECTORS) $fatal(1, "FAIL: invalid vector count");
    $readmemh(vector_file, vectors, 0, n-1);
    for (integer i = 0; i < n; i++)
      if ((^vectors[i]) === 1'bx) $fatal(1, "FAIL: missing/unknown vector %0d", i);
    for (integer lane = 0; lane < 4; lane++) begin
      for (integer a = 0; a < 8; a++)
        for (integer b = 0; b < 8; b++) pair_hits[lane][a][b] = 0;
      for (integer a = 0; a < 6; a++)
        for (integer b = 0; b < 6; b++) edge_hits[lane][a][b] = 0;
    end
    #`balsa_init_time;
    initialise = 0;
    #20ns;
    if (input_r !== 0 || output_r !== 0 || activate_a !== 0)
      $fatal(1, "FAIL: interface did not initialize idle");
    checking = 1;
    activate_r = 1;
    for (integer i = 0; i < n; i++) begin
      transaction = i + 1;
      command = vectors[i][81:18];
      // Native integer multiplication is independent of the DUT's shift/add loop.
      reference = 0;
      for (integer lane = 0; lane < 4; lane++)
        reference += int'(command[8*lane +: 8]) * int'(command[32+8*lane +: 8]);
      if (vectors[i][17:0] !== reference[17:0])
        $fatal(1, "FAIL: fixture disagrees with SV arithmetic reference");
      response_in = 1ns; response_out = 1ns; return_delay = 2ns;
      if (delayed) begin
        rng = rng * 32'd1664525 + 32'd1013904223;
        response_in = (1 + rng % 23) * 1ns;
        rng = rng * 32'd1664525 + 32'd1013904223;
        response_out = (1 + rng % 31) * 1ns;
        rng = rng * 32'd1664525 + 32'd1013904223;
        return_delay = (1 + rng % 7) * 1ns;
      end
      exchange(command, vectors[i][17:0]);
      // Record only after the actual output and complete handshake passed.
      for (integer lane = 0; lane < 4; lane++) begin
        isolated = 1;
        for (integer other = 0; other < 4; other++)
          if (other != lane && (command[8*other +: 8] != 0 || command[32+8*other +: 8] != 0))
            isolated = 0;
        if (isolated) begin
          av = command[8*lane +: 8]; bv = command[32+8*lane +: 8];
          ai = bit_index(av); bi = bit_index(bv);
          if (ai >= 0 && bi >= 0) pair_hits[lane][ai][bi]++;
          ai = edge_index(av); bi = edge_index(bv);
          if (ai >= 0 && bi >= 0) edge_hits[lane][ai][bi]++;
        end
      end
      if (reference == 260100) maxima++;
      if (reference > 65535) wide_results++;
      if (reference == 0 && previous_result == 260100) cleared++;
      if (i > 0 && command == previous_command) repeats++;
      previous_command = command;
      previous_result = reference;
    end
    forbid_output = 1;
    wait_request(0, 1);
    #20ns;
    if (checked != n || requests != n || output_r !== 0 || input_a !== 0 || output_a !== 0)
      $fatal(1, "FAIL: final result/handshake accounting");
    for (integer lane = 0; lane < 4; lane++) begin
      for (integer a = 0; a < 8; a++)
        for (integer b = 0; b < 8; b++) if (pair_hits[lane][a][b] > 0) pair_bins++;
      for (integer a = 0; a < 6; a++)
        for (integer b = 0; b < 6; b++) if (edge_hits[lane][a][b] > 0) edge_bins++;
    end
    $display("COVERAGE: bit_pairs=%0d/256 boundaries=%0d/144 maxima=%0d wide=%0d repeats=%0d cleared=%0d",
             pair_bins, edge_bins, maxima, wide_results, repeats, cleared);
    if (pair_bins != 256 || edge_bins != 144 || maxima == 0 || wide_results == 0 || repeats < 8 || cleared < 8)
      $fatal(1, "FAIL: dot-product coverage incomplete");
    $display("PASS: dot-product structural Verilog checked %0d transactions (%s)", n, scenario);
    $finish;
  end
  initial begin #10ms; $fatal(1, "FAIL: overall simulation timeout"); end
endmodule
