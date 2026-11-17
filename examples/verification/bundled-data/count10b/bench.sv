`timescale 1ns/1ps
`ifndef balsa_init_time
  `define balsa_init_time 20
`endif

module count10b_tb;
  localparam integer MAX_VECTORS = 4096;
  integer N = 10;
  localparam time HANDSHAKE_TIMEOUT = 1000ns;
  localparam time TOTAL_TIMEOUT = 1ms;
  reg activate_r = 0;
  wire activate_a;
  wire input_r;
  reg input_a = 0;
  reg [5:0] input_d = 0;
  wire output_r;
  reg output_a = 0;
  wire [3:0] output_d;
  reg [9:0] vectors [0:MAX_VECTORS-1];
  reg checking = 0;
  reg holding_output = 0;
  reg forbid_output = 0;
  reg [3:0] held_output;
  integer checked = 0;
  integer output_requests = 0;
  integer transaction = 0;
  bit delayed, bad_expected, stall_output;
  string vector_file;
  string scenario = "baseline";
  bit require_coverage;
  bit model_valid = 0;
  integer model_state;
  integer predicted;
  integer load_hits [0:9][0:9][0:1];
  integer count_hits [0:9][0:15][0:1];
  integer load_bins = 0, count_bins = 0;
  integer up_wraps = 0, down_wraps = 0;
  integer repeated_commands = 0, direction_changes = 0;
  reg [5:0] command, previous_command;
  integer data_value, direction;
  reg [31:0] delay_rng = 32'h573c10b;
  time input_delay, output_delay, return_delay = 2ns;

  Balsa_updown10 dut (
    .activate_0r(activate_r), .activate_0a(activate_a),
    .in__sigs_0r(input_r), .in__sigs_0a(input_a), .in__sigs_0d(input_d),
    .count_0r(output_r), .count_0a(output_a), .count_0d(output_d)
  );

  // Both channels are active at the DUT. The bench drives acknowledgements.
  task automatic wait_request(input bit output_channel, input bit level);
    fork
      begin
        wait ((output_channel ? output_r : input_r) === level);
      end
      begin
        #HANDSHAKE_TIMEOUT;
        if (output_channel && level)
          $fatal(1, "FAIL: timeout waiting count request high, transaction %0d", transaction);
        else if (output_channel)
          $fatal(1, "FAIL: timeout waiting count request low, transaction %0d", transaction);
        else if (level)
          $fatal(1, "FAIL: timeout waiting input request high, transaction %0d", transaction);
        else
          $fatal(1, "FAIL: timeout waiting input request low, transaction %0d", transaction);
      end
    join_any
    disable fork;
  endtask

  task automatic send_command(input reg [5:0] command, input time response_delay);
    wait_request(0, 1);
    #response_delay;
    if (input_r !== 1'b1 || input_a !== 1'b0)
      $fatal(1, "FAIL: input request withdrawn before acknowledgement");
    input_d = command;
    #2ns;                         // Bundled data setup before pull acknowledgement.
    input_a = 1;
    wait_request(0, 0);
    #return_delay;                // Hold input data through the full RTZ phase.
    input_a = 0;
    #1ns;
    // input_d remains unchanged until the following command is requested.
  endtask

  task automatic receive_count(input reg [3:0] expected, input time response_delay);
    reg [3:0] wanted;
    wait_request(1, 1);
    #response_delay;               // Legal receiver backpressure before accepting data.
    if (output_r !== 1'b1 || output_a !== 1'b0)
      $fatal(1, "FAIL: count request withdrawn before acknowledgement");
    wanted = expected;
    // Fault-detection evidence must not hide a real DUT mismatch or unknown.
    if (output_d !== expected)
      $fatal(1, "FAIL: count mismatch transaction=%0d actual=%h expected=%h",
             transaction, output_d, expected);
    if (bad_expected && transaction == 1)
      wanted = expected ^ 4'b0001;
    if (output_d !== wanted) begin
      $fatal(1, "FAIL: injected expected-value mismatch actual=%h expected=%h",
             output_d, wanted);
    end
    held_output = output_d;
    holding_output = 1;
    if (stall_output && transaction == 1)
      $display("INJECT: withholding count acknowledgement");
    else
      output_a = 1;
    wait_request(1, 0);
    holding_output = 0;
    if (stall_output && transaction == 1)
      $fatal(1, "FAIL: count request dropped without acknowledgement");
    #return_delay;
    output_a = 0;
    #1ns;
    checked = checked + 1;
    $display("CHECK: transaction=%0d count=%0d", transaction, expected);
  endtask

  // Check four-state controls after initialization and data through push RTZ.
  always @(input_r or output_r or activate_a) begin
    if (checking) begin
      if ((input_r !== 1'b0 && input_r !== 1'b1) ||
          (output_r !== 1'b0 && output_r !== 1'b1))
        $fatal(1, "FAIL: unknown request signal");
      if (activate_a !== 1'b0)
        $fatal(1, "FAIL: permanent loop unexpectedly acknowledged activation");
    end
  end
  always @(output_d) begin
    if (holding_output && output_d !== held_output)
      $fatal(1, "FAIL: count data changed before request returned low");
  end
  always @(posedge output_r) begin
    if (checking) begin
      output_requests = output_requests + 1;
      if (forbid_output || output_requests > N)
        $fatal(1, "FAIL: unexpected extra output request");
    end
  end

  initial begin
    delayed = $test$plusargs("DELAYED");
    bad_expected = $test$plusargs("BAD_EXPECTED");
    stall_output = $test$plusargs("STALL_OUTPUT");
    require_coverage = $test$plusargs("REQUIRE_COVERAGE");
    if ($value$plusargs("NUM_VECTORS=%d", N)) begin end
    if ($value$plusargs("SCENARIO=%s", scenario)) begin end
    if (N < 1 || N > MAX_VECTORS)
      $fatal(1, "FAIL: vector count out of range");
    if (!$value$plusargs("VECTORS=%s", vector_file))
      $fatal(1, "FAIL: supply +VECTORS=path/to/vectors.hex");
    $readmemh(vector_file, vectors, 0, N-1);
    for (integer i = 0; i < N; i = i + 1)
      if ((^vectors[i]) === 1'bx)
        $fatal(1, "FAIL: missing or unknown vector %0d", i);
    for (integer state = 0; state < 10; state = state + 1) begin
      for (integer data = 0; data < 16; data = data + 1)
        for (integer dir = 0; dir < 2; dir = dir + 1) begin
          count_hits[state][data][dir] = 0;
          if (data < 10) load_hits[state][data][dir] = 0;
        end
    end

    #(`balsa_init_time + 20);
    if (input_r !== 0 || output_r !== 0 || activate_a !== 0)
      $fatal(1, "FAIL: interface did not initialize idle");
    checking = 1;
    activate_r = 1;                // Permanent loop: hold high; no completion ack.
    for (integer i = 0; i < N; i = i + 1) begin
      transaction = i + 1;
      command = vectors[i][9:4];
      data_value = command[3:0];
      direction = command[5];
      if (!command[4]) begin
        if (data_value > 9) $fatal(1, "FAIL: unsupported load outside decade domain");
        predicted = data_value;
      end else begin
        if (!model_valid) $fatal(1, "FAIL: count before initial load");
        // Independent arithmetic oracle; generator uses explicit lookup tables.
        predicted = (model_state + (direction ? 1 : 9)) % 10;
      end
      if (vectors[i][3:0] !== predicted[3:0])
        $fatal(1, "FAIL: vector expectation disagrees with reference model at %0d", transaction);
      input_delay = delayed ? (3 + i % 4) * 1ns : 1ns;
      output_delay = delayed ? (5 + i % 5) * 1ns : 1ns;
      return_delay = 2ns;
      if (delayed && require_coverage) begin
        delay_rng = delay_rng * 32'd1664525 + 32'd1013904223;
        input_delay = (1 + delay_rng % 23) * 1ns;
        delay_rng = delay_rng * 32'd1664525 + 32'd1013904223;
        output_delay = (1 + delay_rng % 31) * 1ns;
        delay_rng = delay_rng * 32'd1664525 + 32'd1013904223;
        return_delay = (1 + delay_rng % 7) * 1ns;
      end
      send_command(command, input_delay);
      receive_count(vectors[i][3:0], output_delay);
      // Count coverage only after the actual value and complete handshake passed.
      if (model_valid) begin
        if (command[4]) begin
          count_hits[model_state][data_value][direction]++;
          if (direction && model_state == 9) up_wraps++;
          if (!direction && model_state == 0) down_wraps++;
        end else
          load_hits[model_state][data_value][direction]++;
      end
      if (i > 0) begin
        if (command == previous_command) repeated_commands++;
        if (command[4] && previous_command[4] && command[5] != previous_command[5])
          direction_changes++;
      end
      previous_command = command;
      model_state = predicted;
      model_valid = 1;
    end
    forbid_output = 1;
    wait_request(0, 1);            // Next pull proves the last iteration completed.
    #20ns;
    if (checked != N || output_requests != N || output_r !== 0 ||
        input_a !== 0 || output_a !== 0 || input_r !== 1)
      $fatal(1, "FAIL: final transaction/handshake accounting");
    for (integer state = 0; state < 10; state = state + 1)
      for (integer data = 0; data < 16; data = data + 1)
        for (integer dir = 0; dir < 2; dir = dir + 1) begin
          if (count_hits[state][data][dir] > 0) count_bins++;
          if (data < 10 && load_hits[state][data][dir] > 0) load_bins++;
        end
    $display("COVERAGE: load=%0d/200 count=%0d/320 up_wraps=%0d down_wraps=%0d repeated=%0d direction_changes=%0d",
             load_bins, count_bins, up_wraps, down_wraps, repeated_commands, direction_changes);
    if (require_coverage && (load_bins != 200 || count_bins != 320 ||
        up_wraps == 0 || down_wraps == 0 || repeated_commands < 20 || direction_changes < 20))
      $fatal(1, "FAIL: expanded functional coverage incomplete");
    $display("PASS: count10b structural Verilog checked %0d transactions (%s)", N, scenario);
    $finish;
  end

  initial begin
    #TOTAL_TIMEOUT;
    $fatal(1, "FAIL: overall simulation timeout");
  end
endmodule
