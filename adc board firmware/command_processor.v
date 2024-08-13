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
	
	input wire			syncse, // can't drive with 3.3V, so set as input (use TMSTP+- inputs instead)
	
	input wire [139:0] lvds1bits, // rx_in[0] drives data to rx_out[(J-1)..0], rx_in[1] drives data to the next J number of bits on rx_out
	input wire			clklvds, // clk1, runs at LVDS bit rate (ADC clk input rate) / 2
	output reg			lvds1wr,
	output reg			lvds1rd,
	input wire			lvds1wrfull,
	input wire			lvds1wrempty,
	input wire			lvds1rdfull,
	input wire			lvds1rdempty,
	output reg [139:0] lvds1bitsfifoout, //output bits to fifo
	input wire [139:0] lvds1bitsfifoin, // input bits from fifo
	input wire [10:0]	lvds1wrused,
	input wire [10:0]	lvds1rdused,
	
	input wire			activeclock, clkbad1, clkbad0,
	
  output reg[2:0] phasecounterselect, // Dynamic phase shift counter Select. 000:all 001:M 010:C0 011:C1 100:C2 101:C3 110:C4. Registered in the rising edge of scanclk.
  output reg phaseupdown=1, // Dynamic phase shift direction; 1:UP, 0:DOWN. Registered in the PLL on the rising edge of scanclk.
  output reg phasestep=0,
  output reg scanclk=0
);

integer version = 4; // firmware version

//for clock phase
reg[7:0] pllclock_counter=0;
reg[7:0] scanclk_cycles=0;
  

//variables in clk domain
localparam [3:0] INIT=4'd0, RX=4'd1, PROCESS=4'd2, TX_DATA_CONST=4'd3, TX_DATA1=4'd4, TX_DATA2=4'd5, TX_DATA3=4'd6, TX_DATA4=4'd7, PLLCLOCK=4'd8;
reg [ 3:0]	state = INIT;
reg [ 3:0]	rx_counter = 0;
reg [ 7:0]	rx_data[7:0];
reg [15:0]	length = 0;
reg [ 2:0]	spistate = 0;
reg [3:0]	channel = 0;

//variables in clklvds domain
reg [ 2:0]  acqstate = 0;
reg [15:0]	triggercounter = 0;
reg [15:0]	lengthtotake=0, lengthtotake2=0;
reg 			triggerlive=0, triggerlive2=0;
reg signed [11:0]  samplevalue =0, lowerthresh=-10, upperthresh=10;

always @ (posedge clklvds) begin
	triggerlive2 <= triggerlive;
	lengthtotake2 <= lengthtotake;
end

always @ (posedge clklvds or negedge rstn)
 if (~rstn) begin
	lvds1wr <= 1'b0;
	acqstate <= 3'd0;
 end else begin
	samplevalue <= {lvds1bits[110],lvds1bits[100],lvds1bits[90],lvds1bits[80],lvds1bits[70],lvds1bits[60],lvds1bits[50],lvds1bits[40],lvds1bits[30],lvds1bits[20],lvds1bits[10],lvds1bits[0]};
	case (acqstate)
	0 : begin // ready
		triggercounter <= -16'd1;
		lvds1wr <= 1'b0;
		if (triggerlive2) begin
			triggercounter<=0;
			acqstate <= 3'd1;
		end
	end
	1 : begin // ready for first part of trigger condition to be met
		if (samplevalue<lowerthresh) acqstate <= 3'd2;
	end
	2 : begin // ready for second part of trigger condition to be met
		if (samplevalue>upperthresh) acqstate <= 3'd3;
	end
	3 : begin // taking data
		lvds1bitsfifoout <= lvds1bits;
		//lvds1bitsfifoout <= {14{triggercounter[9:0]}}; // for testing the queue
		if (lvds1wrused<1020 && triggercounter<lengthtotake2) begin
			lvds1wr <= 1'b1;
			triggercounter<=triggercounter+16'd1;
		end
		else begin
			lvds1wr <= 1'b0;
			acqstate <= 3'd0;
		end
	end
	default : begin
		acqstate <= 3'd0;
	end
	endcase
 end

always @ (posedge clk or negedge rstn)
 if (~rstn) begin
	state  <= INIT;
	lvds1rd <= 1'b0;
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
			
		0 : begin // send a length of bytes given by the command
			length <= {rx_data[5],rx_data[4]};
			state <= TX_DATA1;
		end
		
		1 : begin // toggles clkswitch
			clkswitch <= ~clkswitch;
			o_tdata <= {7'd0,clkbad1,7'd0,clkbad0,7'd0,activeclock,7'd0,clkswitch};
			length <= 4;
			o_tvalid <= 1'b1;
			state <= TX_DATA_CONST;
		end
		
		2 : begin // reads version
			o_tdata <= version;
			length <= 4;
			o_tvalid <= 1'b1;
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
					spistate <= 3'd0;
					o_tdata <= spirx; // send back the SPI data read
					length <= 4;
					o_tvalid <= 1'b1;
					state <= TX_DATA_CONST;					
				end
			end
			default : spistate <= 3'd0;
			endcase
		end
		
		4 : begin // reads fifo used
			o_tdata <= lvds1rdused;
			length <= 4;
			o_tvalid <= 1'b1;
			state <= TX_DATA_CONST;
		end
		
		5 : begin // sets length to take
			lengthtotake <= {rx_data[5],rx_data[4]};
			if (triggercounter == -16'd1) begin
				triggerlive <= 1'b1;
			end else begin
				triggerlive <= 1'b0;
				state <= RX;
			end
		end
		
		6 : begin
			phasecounterselect=rx_data[2][2:0];// 000:all 001:M 010:C0 011:C1 100:C2 101:C3 110:C4. 
			phaseupdown=rx_data[3][0]; // up or down
			scanclk=1'b0; // start low
			phasestep=1'b1; // assert!
			pllclock_counter=0;
			scanclk_cycles=0;
			state=PLLCLOCK;
		end
		
		default: // some command we didn't know
			state <= RX;
			
		endcase
	end
	
	TX_DATA_CONST : if (o_tready) begin
		if (length >= 4) begin
			length <= length - 16'd4;
		end else begin
			length <= 0;
			o_tvalid <= 1'b0;
			state <= RX;
		end
	end
	
	TX_DATA1 : begin //channel==0
		o_tvalid <= 1'b0;
		if (o_tready) begin
			if (lvds1rdempty) begin // wait for data
				lvds1rd <= 1'b0;
			end
			else begin
				lvds1rd <= 1'b1;
				state <= TX_DATA2;
			end
		end
	end
	
	TX_DATA2 : begin // wait for read
		lvds1rd <= 1'b0;
		o_tvalid <= 1'b0;
		if (o_tready) begin
			state <= TX_DATA3;
		end
	end
	
	TX_DATA3 : begin
		lvds1rd <= 1'b0;
		if (o_tready) begin
			o_tvalid <= 1'b1;
			if (channel==14) o_tdata <= {16'hbeef,16'hdead};//marker
			else o_tdata  <= {6'h0, lvds1bitsfifoin[10*(channel+1) +: 10], 6'h0, lvds1bitsfifoin[10*channel +: 10]};
			channel<=channel+4'd2;
			state <= TX_DATA4;
		end
	end
	
	TX_DATA4 : begin
		lvds1rd <= 1'b0;
		if (o_tready) begin
			o_tvalid <= 1'b0;
			if (length >= 4) begin
				length <= length - 16'd4;
				if (channel==0) state <= TX_DATA1;
				else state <= TX_DATA3;
			end 
			else begin
				length <= 0;
				channel<=0;
				state <= RX;
			end
		end
	end
	
	PLLCLOCK : begin // to step the clock phase, you have to toggle scanclk a few times
		pllclock_counter=pllclock_counter+8'd1;
		if (pllclock_counter[4]) begin
			scanclk = ~scanclk;
			pllclock_counter=0;
			scanclk_cycles=scanclk_cycles+8'd1;
			if (scanclk_cycles>5) phasestep=1'b0; // deassert!
			if (scanclk_cycles>7) state=RX;
		end
	end
	
	default :
		state <= RX;
	
  endcase
 end

assign i_tready = (state == RX);

assign o_tkeep  = (length>=4) ? 4'b1111 :
                  (length==3) ? 4'b0111 :
                  (length==2) ? 4'b0011 :
                  (length==1) ? 4'b0001 :
                 /*length==0*/  4'b0000;

assign o_tlast  = (length>=4) ? 1'b0 : 1'b1;


endmodule
