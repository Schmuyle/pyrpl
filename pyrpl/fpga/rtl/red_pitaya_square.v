module red_pitaya_square (
   input                 clk_i,
   input                 rstn_i,
   input      [14-1:0]   dat_i,
   output reg [14-1:0]   dat_o
);

wire signed [27:0] sample = {{14{dat_i[13]}}, dat_i};
wire signed [27:0] product = sample * sample;
wire        [14:0]  scaled = product[27:13];

always @(posedge clk_i) begin
   if (!rstn_i)
      dat_o <= 14'd0;
   else if (scaled > 15'd8191)
      dat_o <= 14'd8191;
   else
      dat_o <= scaled[13:0];
end

endmodule
