//--------------------------------------------------------------------------------------------------------
// Module  : command_processor
// Function: receive 8 bytes from AXI-stream slave, then take various actions
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
	 
	output reg pllreset,
	 
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
	input wire [19:0] lvdsbits_o2, lvdsbits_other,
	
	output reg[2:0] phasecounterselect, // Dynamic phase shift counter Select. 000:all 001:M 010:C0 011:C1 100:C2 101:C3 110:C4. Registered in the rising edge of scanclk.
	output reg phaseupdown=1, // Dynamic phase shift direction; 1:UP, 0:DOWN. Registered in the PLL on the rising edge of scanclk.
	output reg [3:0] phasestep,
	output reg scanclk=0,

	output reg [2:0] spimisossel=0, //which spimiso to listen to
	output reg [11:0]	debugout,  // for debugging
	input wire [3:0]	overrange,  //ORA0,A1,B0,B1
	
	output reg [1:0] spi_mode=0,
	
	input wire [7:0] boardin,
	output wire [7:0] boardout,
	output reg spireset_L
);

integer version = 13; // firmware version

assign debugout[0] = locked;
assign debugout[1] = spics[4];
assign debugout[2] = spics[5];
assign debugout[3] = phaseupdown;
assign debugout[4] = overrange[0];
assign debugout[5] = overrange[1];
assign debugout[6] = overrange[2];
assign debugout[7] = overrange[3];
assign debugout[11:8] = state;

//for clock phase
reg[7:0] pllclock_counter=0;
reg[7:0] scanclk_cycles=0;
  

//variables in clk domain
localparam [3:0] INIT=4'd0, RX=4'd1, PROCESS=4'd2, TX_DATA_CONST=4'd3, TX_DATA1=4'd4, TX_DATA2=4'd5, TX_DATA3=4'd6, TX_DATA4=4'd7, PLLCLOCK=4'd8;
reg [ 3:0]	state = INIT;
reg [ 3:0]	rx_counter = 0;
reg [ 7:0]	rx_data[7:0];
integer		length = 0;
reg [ 3:0]	spistate = 0;
reg [5:0]	channel = 0;
reg [3:0]	spicscounter = 0;

//variables in clklvds domain
reg [ 2:0]  acqstate=0;
reg [15:0]	triggercounter=0, triggercounter_sync=0;
reg [15:0]	eventcounter=0, eventcounter_sync=0;
reg [15:0]	lengthtotake=0, lengthtotake_sync=0;
reg 			triggerlive=0, triggerlive_sync=0;
reg			didreadout=0, didreadout_sync=0;
reg [ 7:0]	triggertype=0, triggertype_sync=0;
reg signed [11:0]  lowerthresh=-12'd10, upperthresh=12'd10;

reg signed [11:0]  samplevalue[40];
reg [1:0] sampleclkstr[40];


always @ (posedge clklvds) begin
	
	triggerlive_sync <= triggerlive;
	lengthtotake_sync <= lengthtotake;
	triggertype_sync <= triggertype;
	didreadout_sync <= didreadout;
	
samplevalue[0]  <= {lvds1bits[110],lvds1bits[100],lvds1bits[90],lvds1bits[80],lvds1bits[70],lvds1bits[60],lvds1bits[50],lvds1bits[40],lvds1bits[30],lvds1bits[20],lvds1bits[10],lvds1bits[0]};
samplevalue[1]  <= {lvds1bits[111],lvds1bits[101],lvds1bits[91],lvds1bits[81],lvds1bits[71],lvds1bits[61],lvds1bits[51],lvds1bits[41],lvds1bits[31],lvds1bits[21],lvds1bits[11],lvds1bits[1]};
samplevalue[2]  <= {lvds1bits[112],lvds1bits[102],lvds1bits[92],lvds1bits[82],lvds1bits[72],lvds1bits[62],lvds1bits[52],lvds1bits[42],lvds1bits[32],lvds1bits[22],lvds1bits[12],lvds1bits[2]};
samplevalue[3]  <= {lvds1bits[113],lvds1bits[103],lvds1bits[93],lvds1bits[83],lvds1bits[73],lvds1bits[63],lvds1bits[53],lvds1bits[43],lvds1bits[33],lvds1bits[23],lvds1bits[13],lvds1bits[3]};
samplevalue[4]  <= {lvds1bits[114],lvds1bits[104],lvds1bits[94],lvds1bits[84],lvds1bits[74],lvds1bits[64],lvds1bits[54],lvds1bits[44],lvds1bits[34],lvds1bits[24],lvds1bits[14],lvds1bits[4]};
samplevalue[5]  <= {lvds1bits[115],lvds1bits[105],lvds1bits[95],lvds1bits[85],lvds1bits[75],lvds1bits[65],lvds1bits[55],lvds1bits[45],lvds1bits[35],lvds1bits[25],lvds1bits[15],lvds1bits[5]};
samplevalue[6]  <= {lvds1bits[116],lvds1bits[106],lvds1bits[96],lvds1bits[86],lvds1bits[76],lvds1bits[66],lvds1bits[56],lvds1bits[46],lvds1bits[36],lvds1bits[26],lvds1bits[16],lvds1bits[6]};
samplevalue[7]  <= {lvds1bits[117],lvds1bits[107],lvds1bits[97],lvds1bits[87],lvds1bits[77],lvds1bits[67],lvds1bits[57],lvds1bits[47],lvds1bits[37],lvds1bits[27],lvds1bits[17],lvds1bits[7]};
samplevalue[8]  <= {lvds1bits[118],lvds1bits[108],lvds1bits[98],lvds1bits[88],lvds1bits[78],lvds1bits[68],lvds1bits[58],lvds1bits[48],lvds1bits[38],lvds1bits[28],lvds1bits[18],lvds1bits[8]};
samplevalue[9]  <= {lvds1bits[119],lvds1bits[109],lvds1bits[99],lvds1bits[89],lvds1bits[79],lvds1bits[69],lvds1bits[59],lvds1bits[49],lvds1bits[39],lvds1bits[29],lvds1bits[19],lvds1bits[9]};
sampleclkstr[0] <= {lvds1bits[130],lvds1bits[120]};
sampleclkstr[1] <= {lvds1bits[131],lvds1bits[121]};
sampleclkstr[2] <= {lvds1bits[132],lvds1bits[122]};
sampleclkstr[3] <= {lvds1bits[133],lvds1bits[123]};
sampleclkstr[4] <= {lvds1bits[134],lvds1bits[124]};
sampleclkstr[5] <= {lvds1bits[135],lvds1bits[125]};
sampleclkstr[6] <= {lvds1bits[136],lvds1bits[126]};
sampleclkstr[7] <= {lvds1bits[137],lvds1bits[127]};
sampleclkstr[8] <= {lvds1bits[138],lvds1bits[128]};
sampleclkstr[9] <= {lvds1bits[139],lvds1bits[129]};

samplevalue[10]  <= {lvds2bits[110],lvds2bits[100],lvds2bits[90],lvds2bits[80],lvdsbits_other[0],lvdsbits_other[10],lvds2bits[50],lvds2bits[40],lvds2bits[30],lvds2bits[20],lvds2bits[10],lvds2bits[0]};
samplevalue[11]  <= {lvds2bits[111],lvds2bits[101],lvds2bits[91],lvds2bits[81],lvdsbits_other[1],lvdsbits_other[11],lvds2bits[51],lvds2bits[41],lvds2bits[31],lvds2bits[21],lvds2bits[11],lvds2bits[1]};
samplevalue[12]  <= {lvds2bits[112],lvds2bits[102],lvds2bits[92],lvds2bits[82],lvdsbits_other[2],lvdsbits_other[12],lvds2bits[52],lvds2bits[42],lvds2bits[32],lvds2bits[22],lvds2bits[12],lvds2bits[2]};
samplevalue[13]  <= {lvds2bits[113],lvds2bits[103],lvds2bits[93],lvds2bits[83],lvdsbits_other[3],lvdsbits_other[13],lvds2bits[53],lvds2bits[43],lvds2bits[33],lvds2bits[23],lvds2bits[13],lvds2bits[3]};
samplevalue[14]  <= {lvds2bits[114],lvds2bits[104],lvds2bits[94],lvds2bits[84],lvdsbits_other[4],lvdsbits_other[14],lvds2bits[54],lvds2bits[44],lvds2bits[34],lvds2bits[24],lvds2bits[14],lvds2bits[4]};
samplevalue[15]  <= {lvds2bits[115],lvds2bits[105],lvds2bits[95],lvds2bits[85],lvdsbits_other[5],lvdsbits_other[15],lvds2bits[55],lvds2bits[45],lvds2bits[35],lvds2bits[25],lvds2bits[15],lvds2bits[5]};
samplevalue[16]  <= {lvds2bits[116],lvds2bits[106],lvds2bits[96],lvds2bits[86],lvdsbits_other[6],lvdsbits_other[16],lvds2bits[56],lvds2bits[46],lvds2bits[36],lvds2bits[26],lvds2bits[16],lvds2bits[6]};
samplevalue[17]  <= {lvds2bits[117],lvds2bits[107],lvds2bits[97],lvds2bits[87],lvdsbits_other[7],lvdsbits_other[17],lvds2bits[57],lvds2bits[47],lvds2bits[37],lvds2bits[27],lvds2bits[17],lvds2bits[7]};
samplevalue[18]  <= {lvds2bits[118],lvds2bits[108],lvds2bits[98],lvds2bits[88],lvdsbits_other[8],lvdsbits_other[18],lvds2bits[58],lvds2bits[48],lvds2bits[38],lvds2bits[28],lvds2bits[18],lvds2bits[8]};
samplevalue[19]  <= {lvds2bits[119],lvds2bits[109],lvds2bits[99],lvds2bits[89],lvdsbits_other[9],lvdsbits_other[19],lvds2bits[59],lvds2bits[49],lvds2bits[39],lvds2bits[29],lvds2bits[19],lvds2bits[9]};
sampleclkstr[10] <= {lvds2bits[130],lvds2bits[120]};
sampleclkstr[11] <= {lvds2bits[131],lvds2bits[121]};
sampleclkstr[12] <= {lvds2bits[132],lvds2bits[122]};
sampleclkstr[13] <= {lvds2bits[133],lvds2bits[123]};
sampleclkstr[14] <= {lvds2bits[134],lvds2bits[124]};
sampleclkstr[15] <= {lvds2bits[135],lvds2bits[125]};
sampleclkstr[16] <= {lvds2bits[136],lvds2bits[126]};
sampleclkstr[17] <= {lvds2bits[137],lvds2bits[127]};
sampleclkstr[18] <= {lvds2bits[138],lvds2bits[128]};
sampleclkstr[19] <= {lvds2bits[139],lvds2bits[129]};

samplevalue[20]  <= {lvds3bits[110],lvds3bits[100],lvds3bits[90],lvds3bits[80],lvds3bits[70],lvds3bits[60],lvds3bits[50],lvds3bits[40],lvds3bits[30],lvds3bits[20],lvds3bits[10],lvds3bits[0]};
samplevalue[21]  <= {lvds3bits[111],lvds3bits[101],lvds3bits[91],lvds3bits[81],lvds3bits[71],lvds3bits[61],lvds3bits[51],lvds3bits[41],lvds3bits[31],lvds3bits[21],lvds3bits[11],lvds3bits[1]};
samplevalue[22]  <= {lvds3bits[112],lvds3bits[102],lvds3bits[92],lvds3bits[82],lvds3bits[72],lvds3bits[62],lvds3bits[52],lvds3bits[42],lvds3bits[32],lvds3bits[22],lvds3bits[12],lvds3bits[2]};
samplevalue[23]  <= {lvds3bits[113],lvds3bits[103],lvds3bits[93],lvds3bits[83],lvds3bits[73],lvds3bits[63],lvds3bits[53],lvds3bits[43],lvds3bits[33],lvds3bits[23],lvds3bits[13],lvds3bits[3]};
samplevalue[24]  <= {lvds3bits[114],lvds3bits[104],lvds3bits[94],lvds3bits[84],lvds3bits[74],lvds3bits[64],lvds3bits[54],lvds3bits[44],lvds3bits[34],lvds3bits[24],lvds3bits[14],lvds3bits[4]};
samplevalue[25]  <= {lvds3bits[115],lvds3bits[105],lvds3bits[95],lvds3bits[85],lvds3bits[75],lvds3bits[65],lvds3bits[55],lvds3bits[45],lvds3bits[35],lvds3bits[25],lvds3bits[15],lvds3bits[5]};
samplevalue[26]  <= {lvds3bits[116],lvds3bits[106],lvds3bits[96],lvds3bits[86],lvds3bits[76],lvds3bits[66],lvds3bits[56],lvds3bits[46],lvds3bits[36],lvds3bits[26],lvds3bits[16],lvds3bits[6]};
samplevalue[27]  <= {lvds3bits[117],lvds3bits[107],lvds3bits[97],lvds3bits[87],lvds3bits[77],lvds3bits[67],lvds3bits[57],lvds3bits[47],lvds3bits[37],lvds3bits[27],lvds3bits[17],lvds3bits[7]};
samplevalue[28]  <= {lvds3bits[118],lvds3bits[108],lvds3bits[98],lvds3bits[88],lvds3bits[78],lvds3bits[68],lvds3bits[58],lvds3bits[48],lvds3bits[38],lvds3bits[28],lvds3bits[18],lvds3bits[8]};
samplevalue[29]  <= {lvds3bits[119],lvds3bits[109],lvds3bits[99],lvds3bits[89],lvds3bits[79],lvds3bits[69],lvds3bits[59],lvds3bits[49],lvds3bits[39],lvds3bits[29],lvds3bits[19],lvds3bits[9]};
sampleclkstr[20] <= {lvds3bits[130],lvds3bits[120]};
sampleclkstr[21] <= {lvds3bits[131],lvds3bits[121]};
sampleclkstr[22] <= {lvds3bits[132],lvds3bits[122]};
sampleclkstr[23] <= {lvds3bits[133],lvds3bits[123]};
sampleclkstr[24] <= {lvds3bits[134],lvds3bits[124]};
sampleclkstr[25] <= {lvds3bits[135],lvds3bits[125]};
sampleclkstr[26] <= {lvds3bits[136],lvds3bits[126]};
sampleclkstr[27] <= {lvds3bits[137],lvds3bits[127]};
sampleclkstr[28] <= {lvds3bits[138],lvds3bits[128]};
sampleclkstr[29] <= {lvds3bits[139],lvds3bits[129]};

samplevalue[30]  <= {lvdsbits_o2[0],lvds4bits[100],lvds4bits[90],lvds4bits[80],lvds4bits[70],lvds4bits[60],lvds4bits[50],lvds4bits[40],lvds4bits[30],lvds4bits[20],lvds4bits[10],lvds4bits[0]};
samplevalue[31]  <= {lvdsbits_o2[1],lvds4bits[101],lvds4bits[91],lvds4bits[81],lvds4bits[71],lvds4bits[61],lvds4bits[51],lvds4bits[41],lvds4bits[31],lvds4bits[21],lvds4bits[11],lvds4bits[1]};
samplevalue[32]  <= {lvdsbits_o2[2],lvds4bits[102],lvds4bits[92],lvds4bits[82],lvds4bits[72],lvds4bits[62],lvds4bits[52],lvds4bits[42],lvds4bits[32],lvds4bits[22],lvds4bits[12],lvds4bits[2]};
samplevalue[33]  <= {lvdsbits_o2[3],lvds4bits[103],lvds4bits[93],lvds4bits[83],lvds4bits[73],lvds4bits[63],lvds4bits[53],lvds4bits[43],lvds4bits[33],lvds4bits[23],lvds4bits[13],lvds4bits[3]};
samplevalue[34]  <= {lvdsbits_o2[4],lvds4bits[104],lvds4bits[94],lvds4bits[84],lvds4bits[74],lvds4bits[64],lvds4bits[54],lvds4bits[44],lvds4bits[34],lvds4bits[24],lvds4bits[14],lvds4bits[4]};
samplevalue[35]  <= {lvdsbits_o2[5],lvds4bits[105],lvds4bits[95],lvds4bits[85],lvds4bits[75],lvds4bits[65],lvds4bits[55],lvds4bits[45],lvds4bits[35],lvds4bits[25],lvds4bits[15],lvds4bits[5]};
samplevalue[36]  <= {lvdsbits_o2[6],lvds4bits[106],lvds4bits[96],lvds4bits[86],lvds4bits[76],lvds4bits[66],lvds4bits[56],lvds4bits[46],lvds4bits[36],lvds4bits[26],lvds4bits[16],lvds4bits[6]};
samplevalue[37]  <= {lvdsbits_o2[7],lvds4bits[107],lvds4bits[97],lvds4bits[87],lvds4bits[77],lvds4bits[67],lvds4bits[57],lvds4bits[47],lvds4bits[37],lvds4bits[27],lvds4bits[17],lvds4bits[7]};
samplevalue[38]  <= {lvdsbits_o2[8],lvds4bits[108],lvds4bits[98],lvds4bits[88],lvds4bits[78],lvds4bits[68],lvds4bits[58],lvds4bits[48],lvds4bits[38],lvds4bits[28],lvds4bits[18],lvds4bits[8]};
samplevalue[39]  <= {lvdsbits_o2[9],lvds4bits[109],lvds4bits[99],lvds4bits[89],lvds4bits[79],lvds4bits[69],lvds4bits[59],lvds4bits[49],lvds4bits[39],lvds4bits[29],lvds4bits[19],lvds4bits[9]};
sampleclkstr[30] <= {lvds4bits[130],lvds4bits[120]};
sampleclkstr[31] <= {lvds4bits[131],lvds4bits[121]};
sampleclkstr[32] <= {lvds4bits[132],lvds4bits[122]};
sampleclkstr[33] <= {lvds4bits[133],lvds4bits[123]};
sampleclkstr[34] <= {lvds4bits[134],lvds4bits[124]};
sampleclkstr[35] <= {lvds4bits[135],lvds4bits[125]};
sampleclkstr[36] <= {lvds4bits[136],lvds4bits[126]};
sampleclkstr[37] <= {lvds4bits[137],lvds4bits[127]};
sampleclkstr[38] <= {lvds4bits[138],lvds4bits[128]};
sampleclkstr[39] <= {lvds4bits[139],lvds4bits[129]};

end

always @ (posedge clklvds or negedge rstn)
 if (~rstn) begin
	lvds1wr <= 1'b0;
	acqstate <= 3'd0;
 end else begin
	case (acqstate)
	0 : begin // ready
		lvds1wr <= 1'b0;
		triggercounter<=0;
		if (triggerlive_sync) begin
			if (triggertype_sync==8'd1) acqstate <= 3'd1; // threshold trigger
			else acqstate <= 3'd3; // go straight to taking data, no trigger, triggertype==0
		end
	end
	1 : begin // ready for first part of trigger condition to be met
		if (samplevalue[0]<lowerthresh) acqstate <= 3'd2;
	end
	2 : begin // ready for second part of trigger condition to be met
		if (samplevalue[0]>upperthresh) acqstate <= 3'd3;
	end
	3 : begin // taking data
		lvds1bitsfifoout <= {
		sampleclkstr[39],samplevalue[39],
		sampleclkstr[38],samplevalue[38],
		sampleclkstr[37],samplevalue[37],
		sampleclkstr[36],samplevalue[36],
		sampleclkstr[35],samplevalue[35],
		sampleclkstr[34],samplevalue[34],
		sampleclkstr[33],samplevalue[33],
		sampleclkstr[32],samplevalue[32],
		sampleclkstr[31],samplevalue[31],
		sampleclkstr[30],samplevalue[30],
		
		sampleclkstr[29],samplevalue[29],
		sampleclkstr[28],samplevalue[28],
		sampleclkstr[27],samplevalue[27],
		sampleclkstr[26],samplevalue[26],
		sampleclkstr[25],samplevalue[25],
		sampleclkstr[24],samplevalue[24],
		sampleclkstr[23],samplevalue[23],
		sampleclkstr[22],samplevalue[22],
		sampleclkstr[21],samplevalue[21],
		sampleclkstr[20],samplevalue[20],
		
		sampleclkstr[19],samplevalue[19],
		sampleclkstr[18],samplevalue[18],
		sampleclkstr[17],samplevalue[17],
		sampleclkstr[16],samplevalue[16],
		sampleclkstr[15],samplevalue[15],
		sampleclkstr[14],samplevalue[14],
		sampleclkstr[13],samplevalue[13],
		sampleclkstr[12],samplevalue[12],
		sampleclkstr[11],samplevalue[11],
		sampleclkstr[10],samplevalue[10],
		
		sampleclkstr[9],samplevalue[9],
		sampleclkstr[8],samplevalue[8],
		sampleclkstr[7],samplevalue[7],
		sampleclkstr[6],samplevalue[6],
		sampleclkstr[5],samplevalue[5],
		sampleclkstr[4],samplevalue[4],
		sampleclkstr[3],samplevalue[3],
		sampleclkstr[2],samplevalue[2],
		sampleclkstr[1],samplevalue[1],
		sampleclkstr[0],samplevalue[0]
		};
		//lvds1bitsfifoout <= {56{triggercounter[9:0]}}; // for testing the queue
		if ((!lvds1wrfull) && triggercounter<lengthtotake_sync) begin
			lvds1wr <= 1'b1;
			triggercounter<=triggercounter+16'd1;
		end
		else begin
			lvds1wr <= 1'b0;
			eventcounter <= eventcounter+16'd1;
			acqstate <= 3'd4;
		end
	end
	4 : begin // ready to be read out
		triggercounter<= -16'd1;
		if (didreadout_sync) acqstate <= 3'd0;
	end
	default : begin
		acqstate <= 3'd0;
	end
	endcase
 end
 
integer overrange_counter[4];
always @ (posedge clk) begin
	
	triggercounter_sync <= triggercounter;
	eventcounter_sync <= eventcounter;
	
	if (overrange[0]) overrange_counter[0]<=overrange_counter[0]+1;
	if (overrange[1]) overrange_counter[1]<=overrange_counter[1]+1;
	if (overrange[2]) overrange_counter[2]<=overrange_counter[2]+1;
	if (overrange[3]) overrange_counter[3]<=overrange_counter[3]+1;
end

reg [1:0] pllresetstate=0;
reg pllreset2=0;
always @ (posedge clk) begin
	case (pllresetstate)
   0 : begin
		if (pllreset2) begin
			pllreset<=1'b1;
			pllresetstate<=2'd1;
		end
	end
	1 : begin
		pllreset<=1'b0;
		if (!pllreset2) pllresetstate<=2'd0;
	end
	endcase
end

always @ (posedge clk or negedge rstn)
 if (~rstn) begin
	state  <= INIT;
 end else begin
 
  case (state)
   INIT : begin
		spireset_L <= 1'b1;
		pllreset2 <= 1'b0;
		lvds1rd <= 1'b0;
   	rx_counter <= 0;
		length <= 0;
		spistate <= 0;
		spitxdv <= 1'b0;
		spics <= 8'hff;
		channel <= 6'd0;
		triggerlive <= 1'b0;
		didreadout <= 1'b0;
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
			
		0 : begin // send a length of bytes
			didreadout <= 1'b1; // tell it we have read out this event
			length <= {rx_data[7],rx_data[6],rx_data[5],rx_data[4]};
			state <= TX_DATA1;
		end
		
		1 : begin // sets length of data to take, activates trigger for new event if we don't alrady have one
			triggertype <= rx_data[1]; // while we're at it, set the trigger type
			lengthtotake <= {rx_data[5],rx_data[4]};
			if (triggercounter_sync == 0) triggerlive <= 1'b1; // gets reset in INIT state
			//else triggerlive <= 1'b0;
			o_tdata <= {eventcounter_sync,triggercounter_sync}; // return triggercounter, so we can see if we have an event ready to be read out
			length <= 4;
			o_tvalid <= 1'b1;
			state <= TX_DATA_CONST;
		end
		
		2 : begin // reads version or other info
			if (rx_data[1]==0) o_tdata <= version;
			if (rx_data[1]==1) o_tdata <= {boardin,boardin,boardin,boardin};
			if (rx_data[1]==2) o_tdata <= overrange_counter[rx_data[2][1:0]];
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
				
				if (spicscounter==4'd5) begin // wait a bit for cs to go low
					spicscounter<=4'd0;
					spistate <= 4'd1;
				end
				else spicscounter<=spicscounter+4'd1;
			end
			1 : begin
				if (spitxready) begin
					spitxdv <= 1'b1;
					if (rx_data[7]==2) spistate <= 4'd4; //sending 2 bytes
					else spistate <= 4'd2; // sending more than 2 bytes
				end
			end
			2 : begin
				spitxdv <= 1'b0;
				spitx <= rx_data[3];//second byte to send
				spistate <= 4'd3;
			end
			3 : begin
				if (spitxready) begin
					spitxdv <= 1'b1;
					spistate <= 4'd4;
				end
			end
			4 : begin
				spitxdv <= 1'b0;
				spitx <= rx_data[4];//third byte to send (ignored during read)
				spistate <= 4'd5;
			end
			5 : begin
				if (spitxready) begin
					spitxdv <= 1'b1;
					if (rx_data[7]==4) spistate <= 4'd6; // send the 4th byte
					else spistate <= 4'd8; // skip the 4th byte
				end
			end
			6 : begin
				spitxdv <= 1'b0;
				spitx <= rx_data[5];//fourth byte to send
				spistate <= 4'd7;
			end
			7 : begin
				if (spitxready) begin
					spitxdv <= 1'b1;
					spistate <= 4'd8;
				end
			end
			8 : begin
				spitxdv <= 1'b0;
				if (spirxdv) begin
					spistate <= 4'd9;
					o_tdata <= spirx; // send back the SPI data read
				end
			end
			9 : begin
				if (spicscounter==4'd15) begin // wait a bit before setting cs high
					spicscounter<=4'd0;
					spistate <= 4'd0;
					length <= 4;
					o_tvalid <= 1'b1;
					state <= TX_DATA_CONST;		
				end
				else spicscounter<=spicscounter+4'd1;
			end
			default : spistate <= 4'd0;
			endcase
		end
		
		4 : begin // set SPI_MODE (see SPI_Master.v)
			spireset_L <= 1'b0;
			spi_mode <= rx_data[1][1:0];
			o_tdata <= rx_data[1];
			length <= 4;
			o_tvalid <= 1'b1;
			state <= TX_DATA_CONST;
		end
		
		5 : begin // reset plls
			pllreset2 <= 1'b1;
			o_tdata <= 33;
			length <= 4;
			o_tvalid <= 1'b1;
			state <= TX_DATA_CONST;
		end
		
		6 : begin
			phasecounterselect<=rx_data[2][2:0];// 000:all 001:M 010:C0 011:C1 100:C2 101:C3 110:C4. 
			phaseupdown<=rx_data[3][0]; // up or down
			scanclk<=1'b0; // start low
			phasestep[rx_data[1]]<=1'b1; // assert!
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
			state <= INIT;
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
			if (channel==48) o_tdata <= {16'hbeef,16'hdead};//marker
			else if (channel==46) o_tdata  <= {
				12'd0,
				lvds1bitsfifoin[14*39+12 +: 2], //sampleclkstr39
				lvds1bitsfifoin[14*38+12 +: 2], //...
				lvds1bitsfifoin[14*37+12 +: 2],
				lvds1bitsfifoin[14*36+12 +: 2],
				lvds1bitsfifoin[14*35+12 +: 2],
				lvds1bitsfifoin[14*34+12 +: 2],
				lvds1bitsfifoin[14*33+12 +: 2],
				lvds1bitsfifoin[14*32+12 +: 2],
				lvds1bitsfifoin[14*31+12 +: 2],
				lvds1bitsfifoin[14*30+12 +: 2], //sampleclkstr30
				};
			else if (channel==44) o_tdata  <= {
				12'd0,
				lvds1bitsfifoin[14*29+12 +: 2], //sampleclkstr29
				lvds1bitsfifoin[14*28+12 +: 2], //...
				lvds1bitsfifoin[14*27+12 +: 2],
				lvds1bitsfifoin[14*26+12 +: 2],
				lvds1bitsfifoin[14*25+12 +: 2],
				lvds1bitsfifoin[14*24+12 +: 2],
				lvds1bitsfifoin[14*23+12 +: 2],
				lvds1bitsfifoin[14*22+12 +: 2],
				lvds1bitsfifoin[14*21+12 +: 2],
				lvds1bitsfifoin[14*20+12 +: 2], //sampleclkstr20
				};
			else if (channel==42) o_tdata  <= {
				12'd0,
				lvds1bitsfifoin[14*19+12 +: 2], //sampleclkstr19
				lvds1bitsfifoin[14*18+12 +: 2], //...
				lvds1bitsfifoin[14*17+12 +: 2],
				lvds1bitsfifoin[14*16+12 +: 2],
				lvds1bitsfifoin[14*15+12 +: 2],
				lvds1bitsfifoin[14*14+12 +: 2],
				lvds1bitsfifoin[14*13+12 +: 2],
				lvds1bitsfifoin[14*12+12 +: 2],
				lvds1bitsfifoin[14*11+12 +: 2],
				lvds1bitsfifoin[14*10+12 +: 2], //sampleclkstr10
				};
			else if (channel==40) o_tdata  <= {
				12'd0,
				lvds1bitsfifoin[14*9+12 +: 2], //sampleclkstr9
				lvds1bitsfifoin[14*8+12 +: 2], //...
				lvds1bitsfifoin[14*7+12 +: 2],
				lvds1bitsfifoin[14*6+12 +: 2],
				lvds1bitsfifoin[14*5+12 +: 2],
				lvds1bitsfifoin[14*4+12 +: 2],
				lvds1bitsfifoin[14*3+12 +: 2],
				lvds1bitsfifoin[14*2+12 +: 2],
				lvds1bitsfifoin[14*1+12 +: 2],
				lvds1bitsfifoin[14*0+12 +: 2], //sampleclkstr0
				};
			else o_tdata  <= {4'd0, lvds1bitsfifoin[14*(channel+1) +: 12], 4'd0, lvds1bitsfifoin[14*channel +: 12]};
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
				if (channel==50) begin
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
			if (scanclk_cycles>5) phasestep[rx_data[1]]=1'b0; // deassert!
			if (scanclk_cycles>7) state=INIT;
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
