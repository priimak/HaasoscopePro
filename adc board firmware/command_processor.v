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
	output reg [7:0]	spics, // which chip to talk to
	
	input wire			locked, // clock is locked
	
	input wire [139:0] lvds1bits, lvds2bits, lvds3bits, lvds4bits,// rx_in[0] drives data to rx_out[(J-1)..0], rx_in[1] drives data to the next J number of bits on rx_out
	input wire			clklvds, // clk1, runs at LVDS bit rate (ADC clk input rate) / 2
	output reg			lvds1wr,
	output reg			lvds1rd,
	input wire			lvds1wrfull,
	input wire			lvds1wrempty,
	input wire			lvds1rdfull,
	input wire			lvds1rdempty,
	output reg [559:0] lvds1bitsfifoout, //output bits to fifo
	input wire [559:0] lvds1bitsfifoin, // input bits from fifo
	
	input wire			activeclock, 
	input wire [1:0]	clkbad,
	
	output reg[2:0] phasecounterselect, // Dynamic phase shift counter Select. 000:all 001:M 010:C0 011:C1 100:C2 101:C3 110:C4. Registered in the rising edge of scanclk.
	output reg phaseupdown=1, // Dynamic phase shift direction; 1:UP, 0:DOWN. Registered in the PLL on the rising edge of scanclk.
	output reg phasestep=0,
	output reg scanclk=0,

	output reg [2:0] spimisossel=0, //which spimiso to listen to
	output reg [27:0]	debugout,  // for debugging
	input wire [3:0]	overrange  //ORA0,A1,B0,B1

);

integer version = 4; // firmware version

assign debugout[0] = locked;
assign debugout[4] = overrange[0];
assign debugout[5] = overrange[1];
assign debugout[6] = overrange[2];
assign debugout[7] = overrange[3];

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
reg [5:0]	channel = 0;

//variables in clklvds domain
reg [ 2:0]  acqstate=0;
reg [15:0]	triggercounter=0, triggercounter2=0;
reg [15:0]	lengthtotake=0, lengthtotake2=0;
reg 			triggerlive=0, triggerlive2=0;
reg [ 7:0]	triggertype=0, triggertype2=0;
reg signed [11:0]  lowerthresh=-12'd10, upperthresh=12'd10;

reg signed [11:0]  samplevalue0=0;
reg signed [11:0]  samplevalue1=0;
reg signed [11:0]  samplevalue2=0;
reg signed [11:0]  samplevalue3=0;
reg signed [11:0]  samplevalue4=0;
reg signed [11:0]  samplevalue5=0;
reg signed [11:0]  samplevalue6=0;
reg signed [11:0]  samplevalue7=0;
reg signed [11:0]  samplevalue8=0;
reg signed [11:0]  samplevalue9=0;
reg [1:0] sampleclkstr0=0;
reg [1:0] sampleclkstr1=0;
reg [1:0] sampleclkstr2=0;
reg [1:0] sampleclkstr3=0;
reg [1:0] sampleclkstr4=0;
reg [1:0] sampleclkstr5=0;
reg [1:0] sampleclkstr6=0;
reg [1:0] sampleclkstr7=0;
reg [1:0] sampleclkstr8=0;
reg [1:0] sampleclkstr9=0;

assign samplevalue0 = {lvds1bits[110],lvds1bits[100],lvds1bits[90],lvds1bits[80],lvds1bits[70],lvds1bits[60],lvds1bits[50],lvds1bits[40],lvds1bits[30],lvds1bits[20],lvds1bits[10],lvds1bits[0]};
assign samplevalue1 = {lvds1bits[111],lvds1bits[101],lvds1bits[91],lvds1bits[81],lvds1bits[71],lvds1bits[61],lvds1bits[51],lvds1bits[41],lvds1bits[31],lvds1bits[21],lvds1bits[11],lvds1bits[1]};
assign samplevalue2 = {lvds1bits[112],lvds1bits[102],lvds1bits[92],lvds1bits[82],lvds1bits[72],lvds1bits[62],lvds1bits[52],lvds1bits[42],lvds1bits[32],lvds1bits[22],lvds1bits[12],lvds1bits[2]};
assign samplevalue3 = {lvds1bits[113],lvds1bits[103],lvds1bits[93],lvds1bits[83],lvds1bits[73],lvds1bits[63],lvds1bits[53],lvds1bits[43],lvds1bits[33],lvds1bits[23],lvds1bits[13],lvds1bits[3]};
assign samplevalue4 = {lvds1bits[114],lvds1bits[104],lvds1bits[94],lvds1bits[84],lvds1bits[74],lvds1bits[64],lvds1bits[54],lvds1bits[44],lvds1bits[34],lvds1bits[24],lvds1bits[14],lvds1bits[4]};
assign samplevalue5 = {lvds1bits[115],lvds1bits[105],lvds1bits[95],lvds1bits[85],lvds1bits[75],lvds1bits[65],lvds1bits[55],lvds1bits[45],lvds1bits[35],lvds1bits[25],lvds1bits[15],lvds1bits[5]};
assign samplevalue6 = {lvds1bits[116],lvds1bits[106],lvds1bits[96],lvds1bits[86],lvds1bits[76],lvds1bits[66],lvds1bits[56],lvds1bits[46],lvds1bits[36],lvds1bits[26],lvds1bits[16],lvds1bits[6]};
assign samplevalue7 = {lvds1bits[117],lvds1bits[107],lvds1bits[97],lvds1bits[87],lvds1bits[77],lvds1bits[67],lvds1bits[57],lvds1bits[47],lvds1bits[37],lvds1bits[27],lvds1bits[17],lvds1bits[7]};
assign samplevalue8 = {lvds1bits[118],lvds1bits[108],lvds1bits[98],lvds1bits[88],lvds1bits[78],lvds1bits[68],lvds1bits[58],lvds1bits[48],lvds1bits[38],lvds1bits[28],lvds1bits[18],lvds1bits[8]};
assign samplevalue9 = {lvds1bits[119],lvds1bits[109],lvds1bits[99],lvds1bits[89],lvds1bits[79],lvds1bits[69],lvds1bits[59],lvds1bits[49],lvds1bits[39],lvds1bits[29],lvds1bits[19],lvds1bits[9]};
assign sampleclkstr0 = {lvds1bits[130],lvds1bits[120]};
assign sampleclkstr1 = {lvds1bits[131],lvds1bits[121]};
assign sampleclkstr2 = {lvds1bits[132],lvds1bits[122]};
assign sampleclkstr3 = {lvds1bits[133],lvds1bits[123]};
assign sampleclkstr4 = {lvds1bits[134],lvds1bits[124]};
assign sampleclkstr5 = {lvds1bits[135],lvds1bits[125]};
assign sampleclkstr6 = {lvds1bits[136],lvds1bits[126]};
assign sampleclkstr7 = {lvds1bits[137],lvds1bits[127]};
assign sampleclkstr8 = {lvds1bits[138],lvds1bits[128]};
assign sampleclkstr9 = {lvds1bits[139],lvds1bits[129]};

always @ (posedge clklvds) begin
	triggerlive2 <= triggerlive;
	lengthtotake2 <= lengthtotake;
	triggertype2 <= triggertype;
end

always @ (posedge clklvds or negedge rstn)
 if (~rstn) begin
	lvds1wr <= 1'b0;
	acqstate <= 3'd0;
 end else begin
	case (acqstate)
	0 : begin // ready
		triggercounter <= -16'd1;
		lvds1wr <= 1'b0;
		if (triggerlive2) begin
			triggercounter<=0;
			if (triggertype2==8'd1) acqstate <= 3'd1; // threshold trigger
			else acqstate <= 3'd3; // go straight to taking data, no trigger, triggertype==0
		end
	end
	1 : begin // ready for first part of trigger condition to be met
		if (samplevalue0<lowerthresh) acqstate <= 3'd2;
	end
	2 : begin // ready for second part of trigger condition to be met
		if (samplevalue0>upperthresh) acqstate <= 3'd3;
	end
	3 : begin // taking data
		lvds1bitsfifoout <= {420'd0,
		sampleclkstr9,samplevalue9,
		sampleclkstr8,samplevalue8,
		sampleclkstr7,samplevalue7,
		sampleclkstr6,samplevalue6,
		sampleclkstr5,samplevalue5,
		sampleclkstr4,samplevalue4,
		sampleclkstr3,samplevalue3,
		sampleclkstr2,samplevalue2,
		sampleclkstr1,samplevalue1,
		sampleclkstr0,samplevalue0};
		//lvds1bitsfifoout <= {56{triggercounter[9:0]}}; // for testing the queue
		if ((!lvds1wrfull) && triggercounter<lengthtotake2) begin
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
 
always @ (posedge clk) begin
	triggercounter2 <= triggercounter;
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
		spics <= 8'hff;
		channel <= 6'd0;
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
			o_tdata <= {7'd0,clkbad[1],7'd0,clkbad[0],7'd0,activeclock,7'd0,clkswitch};
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
				spimisossel <= rx_data[1][2:0]; // select requested data from chip
				spics[rx_data[1][2:0]]<=1'b0; //select requested chip
				spitx <= rx_data[2];//first byte to send
				spistate <= 3'd1;
			end
			1 : begin
				if (spitxready) begin
					spitxdv <= 1'b1;
					if (rx_data[7]==2) spistate <= 3'd4; //sending 2 bytes
					else spistate <= 3'd2; // sending 3 bytes
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
					spics <= 8'hff;//unselect chip
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
		
		4 : begin // not used
			o_tdata <= 19;
			length <= 4;
			o_tvalid <= 1'b1;
			state <= TX_DATA_CONST;
		end
		
		5 : begin // sets length to take
			triggertype <= rx_data[1];
			lengthtotake <= {rx_data[5],rx_data[4]};
			if (triggercounter2 == -16'd1) begin
				triggerlive <= 1'b1;
			end else begin
				triggerlive <= 1'b0;
				state <= RX;
			end
		end
		
		6 : begin
			phasecounterselect<=rx_data[2][2:0];// 000:all 001:M 010:C0 011:C1 100:C2 101:C3 110:C4. 
			phaseupdown<=rx_data[3][0]; // up or down
			scanclk<=1'b0; // start low
			phasestep<=1'b1; // assert!
			pllclock_counter<=0;
			scanclk_cycles<=0;
			state<=PLLCLOCK;
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
			if (channel==40) o_tdata <= {16'hbeef,16'hdead};//marker
			else o_tdata  <= {4'd0, lvds1bitsfifoin[14*(channel+1) +: 12], 4'd0, lvds1bitsfifoin[14*channel +: 12]};
			//TODO: add channels for clk/str
			channel<=channel+6'd2;
			state <= TX_DATA4;
		end
	end
	
	TX_DATA4 : begin
		lvds1rd <= 1'b0;
		if (o_tready) begin
			o_tvalid <= 1'b0;
			if (length >= 4) begin
				length <= length - 16'd4;
				if (channel==42) begin
					channel <= 0;
					state <= TX_DATA1;
				end
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
