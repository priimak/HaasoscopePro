
//--------------------------------------------------------------------------------------------------------
// Module  : command_processor
// Type    : synthesizable
// Standard: Verilog 2001 (IEEE1364-2001)
// Function: receive 8 bytes from AXI-stream slave,
//           then take various actions,
//				 send length of bytes on AXI-stream master
//           this module will called by fpga_top_ft600_tx_mass.v or fpga_top_ft232h_tx_mass.v
//--------------------------------------------------------------------------------------------------------

module command_processor (
    input  wire        rstn,
    input  wire        clk,
    // AXI-stream slave
    output wire        i_tready,
    input  wire        i_tvalid,
    input  wire [ 7:0] i_tdata,
    // AXI-stream master
    input  wire        o_tready,
    output wire        o_tvalid,
    output wire [31:0] o_tdata,
    output wire [ 3:0] o_tkeep,
    output wire        o_tlast
);


localparam [2:0] RX = 3'd0,
                 PROCESS = 3'd1,
                 TX_DATA  = 3'd4;

reg [ 2:0]       state = RX;
reg [ 3:0]       rx_counter = 0;
reg [ 7:0]       rx_data[7:0];
reg [31:0]       length = 0;

always @ (posedge clk or negedge rstn)
 if (~rstn) begin
	  state  <= RX;
	  rx_counter <= 0;
	  length <= 0;
 end else begin
  case (state)
  
	RX : if (i_tvalid) begin // get 8 bytes
		 rx_data[rx_counter] <= i_tdata;
		 if (rx_counter==7) begin
			  state <= PROCESS;
			  rx_counter <= 0;
		 end
		 else rx_counter <= rx_counter+4'd1;
	end
	
	PROCESS : begin // do something, based on the command in the first byte
		case (rx_data[0])
			
			0 : begin // send a length of bytes given by the last 4 bytes of the command
				length <= {rx_data[7],rx_data[6],rx_data[5],rx_data[4]};
				state <= TX_DATA;
			end
			
			default: // some command we didn't know
				state <= RX;
			
		endcase
	end
	
	TX_DATA : if (o_tready) begin
		 if (length >= 4) begin
			length <= length - 4;
		 end else begin
			length <= 0;
			state <= RX;
		 end
	end
	
	default :
		 state <= RX;
	
  endcase
 end

assign i_tready = (state != TX_DATA);

assign o_tvalid = (state == TX_DATA);

assign o_tdata  = {length[7:0] - 8'd4,
                   length[7:0] - 8'd3,
                   length[7:0] - 8'd2,
                   length[7:0] - 8'd1 };

assign o_tkeep  = (length>=4) ? 4'b1111 :
                  (length==3) ? 4'b0111 :
                  (length==2) ? 4'b0011 :
                  (length==1) ? 4'b0001 :
                 /*length==0*/  4'b0000;

assign o_tlast  = (length>=4) ? 1'b0 : 1'b1;


endmodule
