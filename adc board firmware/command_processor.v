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
	output wire        o_tlast,
	 
	output reg clkswitch, // sets which input clk the pll uses
	 
	output reg [7:0]	spitx,
	input  reg [7:0]	spirx,
	input  reg 			spitxready,
	output reg			spitxdv,
	input  reg			spirxdv,
	output reg			spicsadc,
	
	input wire [139:0] lvds1bits 	// rx_in[(n-1)..0] is deserialized and driven on rx_out[(J * n)-1 ..0], where J is the deserialization factor and n is the number of channels.
											// rx_in[0] drives data to rx_out[(J-1)..0]. rx_in[1] drives data to the next J number of bits on rx_out.
);

integer version = 4; // firmware version


localparam [2:0] INIT = 3'd0, RX = 3'd1, PROCESS = 3'd2, TX_DATA_CONST = 3'd3, TX_DATA  = 3'd4;

reg [ 2:0]	state = INIT;
reg [ 3:0]	rx_counter = 0;
reg [ 7:0]	rx_data[7:0];
reg [31:0]	length = 0;
reg [ 2:0]	spistate = 0;


always @ (posedge clk or negedge rstn)
 if (~rstn) begin
	state  <= INIT;
 end else begin
  case (state)
   INIT : begin
		clkswitch <= 1'b0;
   	rx_counter <= 0;
		length <= 0;
		spistate <= 0;
		spitxdv <= 1'b0;
		spicsadc <= 1'b1;
		state <= RX;
	end
  
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
			o_tdata  <= {rx_data[4]-8'd4, rx_data[4]-8'd3, rx_data[4]-8'd2, rx_data[4]-8'd1 }; // dummy data
			state <= TX_DATA;
		end
		
		1 : begin // toggles clkswitch
			clkswitch <= ~clkswitch;
			o_tdata <= 0+clkswitch;
			length <= 4;
			state <= TX_DATA_CONST;
		end
		
		2 : begin // reads version
			o_tdata <= version;
			length <= 4;
			state <= TX_DATA_CONST;
		end
		
		3 : begin // SPI command
			case (spistate)			
			0 : begin
				spicsadc <= 1'b0;//select adc chip
				spitx <= rx_data[2];//first byte to send
				spistate <= 3'd1;
			end
			1 : begin
				if (spitxready) begin
					spitxdv <= 1'b1;
					spistate <= 3'd2;
				end
			end
			2 : begin
				spitxdv <= 1'b0;
				spitx <= rx_data[3];//second byte to send
				spistate <= 3'd3;
			end
			3 : begin
				if (spitxready) begin
					spitxdv <= 1'b1;
					spistate <= 3'd4;
				end
			end
			4 : begin
				spitxdv <= 1'b0;
				spitx <= rx_data[4];//third byte to send (ignored during read)
				spistate <= 3'd5;
			end
			5 : begin
				if (spitxready) begin
					spitxdv <= 1'b1;
					spistate <= 3'd6;
				end
			end
			6 : begin
				spitxdv <= 1'b0;
				if (spirxdv) begin
					spicsadc <= 1'b1;//unselect adc chip
					o_tdata <= spirx; // send back the SPI data read
					length <= 4;
					state <= TX_DATA_CONST;					
					spistate <= 3'd0;
				end
			end
			default : spistate <= 3'd0;
			endcase
		end
		
		default: // some command we didn't know
			state <= RX;
			
		endcase
	end
	
	TX_DATA_CONST : if (o_tready) begin
		if (length >= 4) begin
			length <= length - 4;
		end else begin
			length <= 0;
			state <= RX;
		end
	end
	
	TX_DATA : if (o_tready) begin
		//o_tdata  <= {length[7:0]-8'd4,length[7:0]-8'd3,length[7:0]-8'd2,length[7:0]-8'd1 };
		o_tdata  <= {lvds1bits[1:0],lvds1bits[11:10],lvds1bits[21:20],lvds1bits[31:30],lvds1bits[41:40],lvds1bits[51:50],lvds1bits[61:60],
						 lvds1bits[71:70],lvds1bits[81:80],lvds1bits[91:90],lvds1bits[101:100],lvds1bits[111:110],lvds1bits[121:120],lvds1bits[131:130],
						 4'hf};
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

assign i_tready = (state == RX);

assign o_tvalid = (state == TX_DATA || state == TX_DATA_CONST);

assign o_tkeep  = (length>=4) ? 4'b1111 :
                  (length==3) ? 4'b0111 :
                  (length==2) ? 4'b0011 :
                  (length==1) ? 4'b0001 :
                 /*length==0*/  4'b0000;

assign o_tlast  = (length>=4) ? 1'b0 : 1'b1;


endmodule
