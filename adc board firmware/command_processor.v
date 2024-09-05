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
	input wire [19:0] lvdsbits_short, lvdsbits_other,
	
	output reg[2:0] phasecounterselect, // Dynamic phase shift counter Select. 000:all 001:M 010:C0 011:C1 100:C2 101:C3 110:C4. Registered in the rising edge of scanclk.
	output reg phaseupdown=1, // Dynamic phase shift direction; 1:UP, 0:DOWN. Registered in the PLL on the rising edge of scanclk.
	output reg [3:0] phasestep,
	output reg scanclk=0,

	output reg [2:0] spimisossel=0, //which spimiso to listen to
	output reg [27:0]	debugout,  // for debugging
	input wire [3:0]	overrange,  //ORA0,A1,B0,B1
	input wire			clklvds90, clklvds180, clklvds270,
	input wire [19:0] lvdsbitsC_o

);

integer version = 8; // firmware version

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
integer		length = 0;
reg [ 2:0]	spistate = 0;
reg [5:0]	channel = 0;

//variables in clklvds domain
reg [ 2:0]  acqstate=0;
reg [15:0]	triggercounter=0, triggercounter2=0, triggercounter3=0;
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

reg signed [11:0]  samplevalue10=0;
reg signed [11:0]  samplevalue11=0;
reg signed [11:0]  samplevalue12=0;
reg signed [11:0]  samplevalue13=0;
reg signed [11:0]  samplevalue14=0;
reg signed [11:0]  samplevalue15=0;
reg signed [11:0]  samplevalue16=0;
reg signed [11:0]  samplevalue17=0;
reg signed [11:0]  samplevalue18=0;
reg signed [11:0]  samplevalue19=0;
reg [1:0] sampleclkstr10=0;
reg [1:0] sampleclkstr11=0;
reg [1:0] sampleclkstr12=0;
reg [1:0] sampleclkstr13=0;
reg [1:0] sampleclkstr14=0;
reg [1:0] sampleclkstr15=0;
reg [1:0] sampleclkstr16=0;
reg [1:0] sampleclkstr17=0;
reg [1:0] sampleclkstr18=0;
reg [1:0] sampleclkstr19=0;

reg signed [11:0]  samplevalue20=0;
reg signed [11:0]  samplevalue21=0;
reg signed [11:0]  samplevalue22=0;
reg signed [11:0]  samplevalue23=0;
reg signed [11:0]  samplevalue24=0;
reg signed [11:0]  samplevalue25=0;
reg signed [11:0]  samplevalue26=0;
reg signed [11:0]  samplevalue27=0;
reg signed [11:0]  samplevalue28=0;
reg signed [11:0]  samplevalue29=0;
reg [1:0] sampleclkstr20=0;
reg [1:0] sampleclkstr21=0;
reg [1:0] sampleclkstr22=0;
reg [1:0] sampleclkstr23=0;
reg [1:0] sampleclkstr24=0;
reg [1:0] sampleclkstr25=0;
reg [1:0] sampleclkstr26=0;
reg [1:0] sampleclkstr27=0;
reg [1:0] sampleclkstr28=0;
reg [1:0] sampleclkstr29=0;

reg signed [11:0]  samplevalue30=0;
reg signed [11:0]  samplevalue31=0;
reg signed [11:0]  samplevalue32=0;
reg signed [11:0]  samplevalue33=0;
reg signed [11:0]  samplevalue34=0;
reg signed [11:0]  samplevalue35=0;
reg signed [11:0]  samplevalue36=0;
reg signed [11:0]  samplevalue37=0;
reg signed [11:0]  samplevalue38=0;
reg signed [11:0]  samplevalue39=0;
reg [1:0] sampleclkstr30=0;
reg [1:0] sampleclkstr31=0;
reg [1:0] sampleclkstr32=0;
reg [1:0] sampleclkstr33=0;
reg [1:0] sampleclkstr34=0;
reg [1:0] sampleclkstr35=0;
reg [1:0] sampleclkstr36=0;
reg [1:0] sampleclkstr37=0;
reg [1:0] sampleclkstr38=0;
reg [1:0] sampleclkstr39=0;


reg signed [11:0]  samplevalue0sync=0;
reg signed [11:0]  samplevalue1sync=0;
reg signed [11:0]  samplevalue2sync=0;
reg signed [11:0]  samplevalue3sync=0;
reg signed [11:0]  samplevalue4sync=0;
reg signed [11:0]  samplevalue5sync=0;
reg signed [11:0]  samplevalue6sync=0;
reg signed [11:0]  samplevalue7sync=0;
reg signed [11:0]  samplevalue8sync=0;
reg signed [11:0]  samplevalue9sync=0;
reg [1:0] sampleclkstr0sync=0;
reg [1:0] sampleclkstr1sync=0;
reg [1:0] sampleclkstr2sync=0;
reg [1:0] sampleclkstr3sync=0;
reg [1:0] sampleclkstr4sync=0;
reg [1:0] sampleclkstr5sync=0;
reg [1:0] sampleclkstr6sync=0;
reg [1:0] sampleclkstr7sync=0;
reg [1:0] sampleclkstr8sync=0;
reg [1:0] sampleclkstr9sync=0;

reg signed [11:0]  samplevalue10sync=0;
reg signed [11:0]  samplevalue11sync=0;
reg signed [11:0]  samplevalue12sync=0;
reg signed [11:0]  samplevalue13sync=0;
reg signed [11:0]  samplevalue14sync=0;
reg signed [11:0]  samplevalue15sync=0;
reg signed [11:0]  samplevalue16sync=0;
reg signed [11:0]  samplevalue17sync=0;
reg signed [11:0]  samplevalue18sync=0;
reg signed [11:0]  samplevalue19sync=0;
reg [1:0] sampleclkstr10sync=0;
reg [1:0] sampleclkstr11sync=0;
reg [1:0] sampleclkstr12sync=0;
reg [1:0] sampleclkstr13sync=0;
reg [1:0] sampleclkstr14sync=0;
reg [1:0] sampleclkstr15sync=0;
reg [1:0] sampleclkstr16sync=0;
reg [1:0] sampleclkstr17sync=0;
reg [1:0] sampleclkstr18sync=0;
reg [1:0] sampleclkstr19sync=0;

reg signed [11:0]  samplevalue20sync=0;
reg signed [11:0]  samplevalue21sync=0;
reg signed [11:0]  samplevalue22sync=0;
reg signed [11:0]  samplevalue23sync=0;
reg signed [11:0]  samplevalue24sync=0;
reg signed [11:0]  samplevalue25sync=0;
reg signed [11:0]  samplevalue26sync=0;
reg signed [11:0]  samplevalue27sync=0;
reg signed [11:0]  samplevalue28sync=0;
reg signed [11:0]  samplevalue29sync=0;
reg [1:0] sampleclkstr20sync=0;
reg [1:0] sampleclkstr21sync=0;
reg [1:0] sampleclkstr22sync=0;
reg [1:0] sampleclkstr23sync=0;
reg [1:0] sampleclkstr24sync=0;
reg [1:0] sampleclkstr25sync=0;
reg [1:0] sampleclkstr26sync=0;
reg [1:0] sampleclkstr27sync=0;
reg [1:0] sampleclkstr28sync=0;
reg [1:0] sampleclkstr29sync=0;

reg signed [11:0]  samplevalue30sync=0;
reg signed [11:0]  samplevalue31sync=0;
reg signed [11:0]  samplevalue32sync=0;
reg signed [11:0]  samplevalue33sync=0;
reg signed [11:0]  samplevalue34sync=0;
reg signed [11:0]  samplevalue35sync=0;
reg signed [11:0]  samplevalue36sync=0;
reg signed [11:0]  samplevalue37sync=0;
reg signed [11:0]  samplevalue38sync=0;
reg signed [11:0]  samplevalue39sync=0;
reg [1:0] sampleclkstr30sync=0;
reg [1:0] sampleclkstr31sync=0;
reg [1:0] sampleclkstr32sync=0;
reg [1:0] sampleclkstr33sync=0;
reg [1:0] sampleclkstr34sync=0;
reg [1:0] sampleclkstr35sync=0;
reg [1:0] sampleclkstr36sync=0;
reg [1:0] sampleclkstr37sync=0;
reg [1:0] sampleclkstr38sync=0;
reg [1:0] sampleclkstr39sync=0;




reg signed [11:0]  samplevalue0sync2=0;
reg signed [11:0]  samplevalue1sync2=0;
reg signed [11:0]  samplevalue2sync2=0;
reg signed [11:0]  samplevalue3sync2=0;
reg signed [11:0]  samplevalue4sync2=0;
reg signed [11:0]  samplevalue5sync2=0;
reg signed [11:0]  samplevalue6sync2=0;
reg signed [11:0]  samplevalue7sync2=0;
reg signed [11:0]  samplevalue8sync2=0;
reg signed [11:0]  samplevalue9sync2=0;
reg [1:0] sampleclkstr0sync2=0;
reg [1:0] sampleclkstr1sync2=0;
reg [1:0] sampleclkstr2sync2=0;
reg [1:0] sampleclkstr3sync2=0;
reg [1:0] sampleclkstr4sync2=0;
reg [1:0] sampleclkstr5sync2=0;
reg [1:0] sampleclkstr6sync2=0;
reg [1:0] sampleclkstr7sync2=0;
reg [1:0] sampleclkstr8sync2=0;
reg [1:0] sampleclkstr9sync2=0;

reg signed [11:0]  samplevalue10sync2=0;
reg signed [11:0]  samplevalue11sync2=0;
reg signed [11:0]  samplevalue12sync2=0;
reg signed [11:0]  samplevalue13sync2=0;
reg signed [11:0]  samplevalue14sync2=0;
reg signed [11:0]  samplevalue15sync2=0;
reg signed [11:0]  samplevalue16sync2=0;
reg signed [11:0]  samplevalue17sync2=0;
reg signed [11:0]  samplevalue18sync2=0;
reg signed [11:0]  samplevalue19sync2=0;
reg [1:0] sampleclkstr10sync2=0;
reg [1:0] sampleclkstr11sync2=0;
reg [1:0] sampleclkstr12sync2=0;
reg [1:0] sampleclkstr13sync2=0;
reg [1:0] sampleclkstr14sync2=0;
reg [1:0] sampleclkstr15sync2=0;
reg [1:0] sampleclkstr16sync2=0;
reg [1:0] sampleclkstr17sync2=0;
reg [1:0] sampleclkstr18sync2=0;
reg [1:0] sampleclkstr19sync2=0;

reg signed [11:0]  samplevalue20sync2=0;
reg signed [11:0]  samplevalue21sync2=0;
reg signed [11:0]  samplevalue22sync2=0;
reg signed [11:0]  samplevalue23sync2=0;
reg signed [11:0]  samplevalue24sync2=0;
reg signed [11:0]  samplevalue25sync2=0;
reg signed [11:0]  samplevalue26sync2=0;
reg signed [11:0]  samplevalue27sync2=0;
reg signed [11:0]  samplevalue28sync2=0;
reg signed [11:0]  samplevalue29sync2=0;
reg [1:0] sampleclkstr20sync2=0;
reg [1:0] sampleclkstr21sync2=0;
reg [1:0] sampleclkstr22sync2=0;
reg [1:0] sampleclkstr23sync2=0;
reg [1:0] sampleclkstr24sync2=0;
reg [1:0] sampleclkstr25sync2=0;
reg [1:0] sampleclkstr26sync2=0;
reg [1:0] sampleclkstr27sync2=0;
reg [1:0] sampleclkstr28sync2=0;
reg [1:0] sampleclkstr29sync2=0;

reg signed [11:0]  samplevalue30sync2=0;
reg signed [11:0]  samplevalue31sync2=0;
reg signed [11:0]  samplevalue32sync2=0;
reg signed [11:0]  samplevalue33sync2=0;
reg signed [11:0]  samplevalue34sync2=0;
reg signed [11:0]  samplevalue35sync2=0;
reg signed [11:0]  samplevalue36sync2=0;
reg signed [11:0]  samplevalue37sync2=0;
reg signed [11:0]  samplevalue38sync2=0;
reg signed [11:0]  samplevalue39sync2=0;
reg [1:0] sampleclkstr30sync2=0;
reg [1:0] sampleclkstr31sync2=0;
reg [1:0] sampleclkstr32sync2=0;
reg [1:0] sampleclkstr33sync2=0;
reg [1:0] sampleclkstr34sync2=0;
reg [1:0] sampleclkstr35sync2=0;
reg [1:0] sampleclkstr36sync2=0;
reg [1:0] sampleclkstr37sync2=0;
reg [1:0] sampleclkstr38sync2=0;
reg [1:0] sampleclkstr39sync2=0;





always @ (posedge clklvds) begin
	triggerlive2 <= triggerlive;
	lengthtotake2 <= lengthtotake;
	triggertype2 <= triggertype;
samplevalue0  <= {lvds1bits[110],lvds1bits[100],lvds1bits[90],lvds1bits[80],lvds1bits[70],lvds1bits[60],lvdsbits_short[10],lvds1bits[40],lvds1bits[30],lvds1bits[20],lvds1bits[10],lvds1bits[0]};
samplevalue1  <= {lvds1bits[111],lvds1bits[101],lvds1bits[91],lvds1bits[81],lvds1bits[71],lvds1bits[61],lvdsbits_short[11],lvds1bits[41],lvds1bits[31],lvds1bits[21],lvds1bits[11],lvds1bits[1]};
samplevalue2  <= {lvds1bits[112],lvds1bits[102],lvds1bits[92],lvds1bits[82],lvds1bits[72],lvds1bits[62],lvdsbits_short[12],lvds1bits[42],lvds1bits[32],lvds1bits[22],lvds1bits[12],lvds1bits[2]};
samplevalue3  <= {lvds1bits[113],lvds1bits[103],lvds1bits[93],lvds1bits[83],lvds1bits[73],lvds1bits[63],lvdsbits_short[13],lvds1bits[43],lvds1bits[33],lvds1bits[23],lvds1bits[13],lvds1bits[3]};
samplevalue4  <= {lvds1bits[114],lvds1bits[104],lvds1bits[94],lvds1bits[84],lvds1bits[74],lvds1bits[64],lvdsbits_short[14],lvds1bits[44],lvds1bits[34],lvds1bits[24],lvds1bits[14],lvds1bits[4]};
samplevalue5  <= {lvds1bits[115],lvds1bits[105],lvds1bits[95],lvds1bits[85],lvds1bits[75],lvds1bits[65],lvdsbits_short[15],lvds1bits[45],lvds1bits[35],lvds1bits[25],lvds1bits[15],lvds1bits[5]};
samplevalue6  <= {lvds1bits[116],lvds1bits[106],lvds1bits[96],lvds1bits[86],lvds1bits[76],lvds1bits[66],lvdsbits_short[16],lvds1bits[46],lvds1bits[36],lvds1bits[26],lvds1bits[16],lvds1bits[6]};
samplevalue7  <= {lvds1bits[117],lvds1bits[107],lvds1bits[97],lvds1bits[87],lvds1bits[77],lvds1bits[67],lvdsbits_short[17],lvds1bits[47],lvds1bits[37],lvds1bits[27],lvds1bits[17],lvds1bits[7]};
samplevalue8  <= {lvds1bits[118],lvds1bits[108],lvds1bits[98],lvds1bits[88],lvds1bits[78],lvds1bits[68],lvdsbits_short[18],lvds1bits[48],lvds1bits[38],lvds1bits[28],lvds1bits[18],lvds1bits[8]};
samplevalue9  <= {lvds1bits[119],lvds1bits[109],lvds1bits[99],lvds1bits[89],lvds1bits[79],lvds1bits[69],lvdsbits_short[19],lvds1bits[49],lvds1bits[39],lvds1bits[29],lvds1bits[19],lvds1bits[9]};
sampleclkstr0 <= {lvds1bits[130],lvds1bits[120]};
sampleclkstr1 <= {lvds1bits[131],lvds1bits[121]};
sampleclkstr2 <= {lvds1bits[132],lvds1bits[122]};
sampleclkstr3 <= {lvds1bits[133],lvds1bits[123]};
sampleclkstr4 <= {lvds1bits[134],lvds1bits[124]};
sampleclkstr5 <= {lvds1bits[135],lvds1bits[125]};
sampleclkstr6 <= {lvds1bits[136],lvds1bits[126]};
sampleclkstr7 <= {lvds1bits[137],lvds1bits[127]};
sampleclkstr8 <= {lvds1bits[138],lvds1bits[128]};
sampleclkstr9 <= {lvds1bits[139],lvds1bits[129]};

samplevalue0sync  <= samplevalue0 ;
samplevalue1sync  <= samplevalue1 ;
samplevalue2sync  <= samplevalue2 ;
samplevalue3sync  <= samplevalue3 ;
samplevalue4sync  <= samplevalue4 ;
samplevalue5sync  <= samplevalue5 ;
samplevalue6sync  <= samplevalue6 ;
samplevalue7sync  <= samplevalue7 ;
samplevalue8sync  <= samplevalue8 ;
samplevalue9sync  <= samplevalue9 ;
sampleclkstr0sync <= sampleclkstr0;
sampleclkstr1sync <= sampleclkstr1;
sampleclkstr2sync <= sampleclkstr2;
sampleclkstr3sync <= sampleclkstr3;
sampleclkstr4sync <= sampleclkstr4;
sampleclkstr5sync <= sampleclkstr5;
sampleclkstr6sync <= sampleclkstr6;
sampleclkstr7sync <= sampleclkstr7;
sampleclkstr8sync <= sampleclkstr8;
sampleclkstr9sync <= sampleclkstr9;


samplevalue0sync2  <= samplevalue0sync ;
samplevalue1sync2  <= samplevalue1sync ;
samplevalue2sync2  <= samplevalue2sync ;
samplevalue3sync2  <= samplevalue3sync ;
samplevalue4sync2  <= samplevalue4sync ;
samplevalue5sync2  <= samplevalue5sync ;
samplevalue6sync2  <= samplevalue6sync ;
samplevalue7sync2  <= samplevalue7sync ;
samplevalue8sync2  <= samplevalue8sync ;
samplevalue9sync2  <= samplevalue9sync ;
sampleclkstr0sync2 <= sampleclkstr0sync;
sampleclkstr1sync2 <= sampleclkstr1sync;
sampleclkstr2sync2 <= sampleclkstr2sync;
sampleclkstr3sync2 <= sampleclkstr3sync;
sampleclkstr4sync2 <= sampleclkstr4sync;
sampleclkstr5sync2 <= sampleclkstr5sync;
sampleclkstr6sync2 <= sampleclkstr6sync;
sampleclkstr7sync2 <= sampleclkstr7sync;
sampleclkstr8sync2 <= sampleclkstr8sync;
sampleclkstr9sync2 <= sampleclkstr9sync;

samplevalue10sync2  <= samplevalue10sync ;
samplevalue11sync2  <= samplevalue11sync ;
samplevalue12sync2  <= samplevalue12sync ;
samplevalue13sync2  <= samplevalue13sync ;
samplevalue14sync2  <= samplevalue14sync ;
samplevalue15sync2  <= samplevalue15sync ;
samplevalue16sync2  <= samplevalue16sync ;
samplevalue17sync2  <= samplevalue17sync ;
samplevalue18sync2  <= samplevalue18sync ;
samplevalue19sync2  <= samplevalue19sync ;
sampleclkstr10sync2 <= sampleclkstr10sync;
sampleclkstr11sync2 <= sampleclkstr11sync;
sampleclkstr12sync2 <= sampleclkstr12sync;
sampleclkstr13sync2 <= sampleclkstr13sync;
sampleclkstr14sync2 <= sampleclkstr14sync;
sampleclkstr15sync2 <= sampleclkstr15sync;
sampleclkstr16sync2 <= sampleclkstr16sync;
sampleclkstr17sync2 <= sampleclkstr17sync;
sampleclkstr18sync2 <= sampleclkstr18sync;
sampleclkstr19sync2 <= sampleclkstr19sync;

samplevalue20sync2  <= samplevalue20sync ;
samplevalue21sync2  <= samplevalue21sync ;
samplevalue22sync2  <= samplevalue22sync ;
samplevalue23sync2  <= samplevalue23sync ;
samplevalue24sync2  <= samplevalue24sync ;
samplevalue25sync2  <= samplevalue25sync ;
samplevalue26sync2  <= samplevalue26sync ;
samplevalue27sync2  <= samplevalue27sync ;
samplevalue28sync2  <= samplevalue28sync ;
samplevalue29sync2  <= samplevalue29sync ;
sampleclkstr20sync2 <= sampleclkstr20sync;
sampleclkstr21sync2 <= sampleclkstr21sync;
sampleclkstr22sync2 <= sampleclkstr22sync;
sampleclkstr23sync2 <= sampleclkstr23sync;
sampleclkstr24sync2 <= sampleclkstr24sync;
sampleclkstr25sync2 <= sampleclkstr25sync;
sampleclkstr26sync2 <= sampleclkstr26sync;
sampleclkstr27sync2 <= sampleclkstr27sync;
sampleclkstr28sync2 <= sampleclkstr28sync;
sampleclkstr29sync2 <= sampleclkstr29sync;

samplevalue30sync2  <= samplevalue30sync ;
samplevalue31sync2  <= samplevalue31sync ;
samplevalue32sync2  <= samplevalue32sync ;
samplevalue33sync2  <= samplevalue33sync ;
samplevalue34sync2  <= samplevalue34sync ;
samplevalue35sync2  <= samplevalue35sync ;
samplevalue36sync2  <= samplevalue36sync ;
samplevalue37sync2  <= samplevalue37sync ;
samplevalue38sync2  <= samplevalue38sync ;
samplevalue39sync2  <= samplevalue39sync ;
sampleclkstr30sync2 <= sampleclkstr30sync;
sampleclkstr31sync2 <= sampleclkstr31sync;
sampleclkstr32sync2 <= sampleclkstr32sync;
sampleclkstr33sync2 <= sampleclkstr33sync;
sampleclkstr34sync2 <= sampleclkstr34sync;
sampleclkstr35sync2 <= sampleclkstr35sync;
sampleclkstr36sync2 <= sampleclkstr36sync;
sampleclkstr37sync2 <= sampleclkstr37sync;
sampleclkstr38sync2 <= sampleclkstr38sync;
sampleclkstr39sync2 <= sampleclkstr39sync;

end

always @ (posedge clklvds90) begin
samplevalue10  <= {lvds2bits[110],lvds2bits[100],lvds2bits[90],lvds2bits[80],lvdsbits_other[0],lvdsbits_other[10],lvds2bits[50],lvds2bits[40],lvds2bits[30],lvds2bits[20],lvds2bits[10],lvds2bits[0]};
samplevalue11  <= {lvds2bits[111],lvds2bits[101],lvds2bits[91],lvds2bits[81],lvdsbits_other[1],lvdsbits_other[11],lvds2bits[51],lvds2bits[41],lvds2bits[31],lvds2bits[21],lvds2bits[11],lvds2bits[1]};
samplevalue12  <= {lvds2bits[112],lvds2bits[102],lvds2bits[92],lvds2bits[82],lvdsbits_other[2],lvdsbits_other[12],lvds2bits[52],lvds2bits[42],lvds2bits[32],lvds2bits[22],lvds2bits[12],lvds2bits[2]};
samplevalue13  <= {lvds2bits[113],lvds2bits[103],lvds2bits[93],lvds2bits[83],lvdsbits_other[3],lvdsbits_other[13],lvds2bits[53],lvds2bits[43],lvds2bits[33],lvds2bits[23],lvds2bits[13],lvds2bits[3]};
samplevalue14  <= {lvds2bits[114],lvds2bits[104],lvds2bits[94],lvds2bits[84],lvdsbits_other[4],lvdsbits_other[14],lvds2bits[54],lvds2bits[44],lvds2bits[34],lvds2bits[24],lvds2bits[14],lvds2bits[4]};
samplevalue15  <= {lvds2bits[115],lvds2bits[105],lvds2bits[95],lvds2bits[85],lvdsbits_other[5],lvdsbits_other[15],lvds2bits[55],lvds2bits[45],lvds2bits[35],lvds2bits[25],lvds2bits[15],lvds2bits[5]};
samplevalue16  <= {lvds2bits[116],lvds2bits[106],lvds2bits[96],lvds2bits[86],lvdsbits_other[6],lvdsbits_other[16],lvds2bits[56],lvds2bits[46],lvds2bits[36],lvds2bits[26],lvds2bits[16],lvds2bits[6]};
samplevalue17  <= {lvds2bits[117],lvds2bits[107],lvds2bits[97],lvds2bits[87],lvdsbits_other[7],lvdsbits_other[17],lvds2bits[57],lvds2bits[47],lvds2bits[37],lvds2bits[27],lvds2bits[17],lvds2bits[7]};
samplevalue18  <= {lvds2bits[118],lvds2bits[108],lvds2bits[98],lvds2bits[88],lvdsbits_other[8],lvdsbits_other[18],lvds2bits[58],lvds2bits[48],lvds2bits[38],lvds2bits[28],lvds2bits[18],lvds2bits[8]};
samplevalue19  <= {lvds2bits[119],lvds2bits[109],lvds2bits[99],lvds2bits[89],lvdsbits_other[9],lvdsbits_other[19],lvds2bits[59],lvds2bits[49],lvds2bits[39],lvds2bits[29],lvds2bits[19],lvds2bits[9]};
sampleclkstr10 <= {lvds2bits[130],lvds2bits[120]};
sampleclkstr11 <= {lvds2bits[131],lvds2bits[121]};
sampleclkstr12 <= {lvds2bits[132],lvds2bits[122]};
sampleclkstr13 <= {lvds2bits[133],lvds2bits[123]};
sampleclkstr14 <= {lvds2bits[134],lvds2bits[124]};
sampleclkstr15 <= {lvds2bits[135],lvds2bits[125]};
sampleclkstr16 <= {lvds2bits[136],lvds2bits[126]};
sampleclkstr17 <= {lvds2bits[137],lvds2bits[127]};
sampleclkstr18 <= {lvds2bits[138],lvds2bits[128]};
sampleclkstr19 <= {lvds2bits[139],lvds2bits[129]};

samplevalue10sync  <= samplevalue10 ;
samplevalue11sync  <= samplevalue11 ;
samplevalue12sync  <= samplevalue12 ;
samplevalue13sync  <= samplevalue13 ;
samplevalue14sync  <= samplevalue14 ;
samplevalue15sync  <= samplevalue15 ;
samplevalue16sync  <= samplevalue16 ;
samplevalue17sync  <= samplevalue17 ;
samplevalue18sync  <= samplevalue18 ;
samplevalue19sync  <= samplevalue19 ;
sampleclkstr10sync <= sampleclkstr10;
sampleclkstr11sync <= sampleclkstr11;
sampleclkstr12sync <= sampleclkstr12;
sampleclkstr13sync <= sampleclkstr13;
sampleclkstr14sync <= sampleclkstr14;
sampleclkstr15sync <= sampleclkstr15;
sampleclkstr16sync <= sampleclkstr16;
sampleclkstr17sync <= sampleclkstr17;
sampleclkstr18sync <= sampleclkstr18;
sampleclkstr19sync <= sampleclkstr19;
end

always @ (posedge clklvds180) begin
samplevalue20  <= {lvdsbitsC_o[0],lvds3bits[100],lvdsbitsC_o[10],lvds3bits[80],lvds3bits[70],lvds3bits[60],lvds3bits[50],lvds3bits[40],lvds3bits[30],lvds3bits[20],lvds3bits[10],lvds3bits[0]};
samplevalue21  <= {lvdsbitsC_o[1],lvds3bits[101],lvdsbitsC_o[11],lvds3bits[81],lvds3bits[71],lvds3bits[61],lvds3bits[51],lvds3bits[41],lvds3bits[31],lvds3bits[21],lvds3bits[11],lvds3bits[1]};
samplevalue22  <= {lvdsbitsC_o[2],lvds3bits[102],lvdsbitsC_o[12],lvds3bits[82],lvds3bits[72],lvds3bits[62],lvds3bits[52],lvds3bits[42],lvds3bits[32],lvds3bits[22],lvds3bits[12],lvds3bits[2]};
samplevalue23  <= {lvdsbitsC_o[3],lvds3bits[103],lvdsbitsC_o[13],lvds3bits[83],lvds3bits[73],lvds3bits[63],lvds3bits[53],lvds3bits[43],lvds3bits[33],lvds3bits[23],lvds3bits[13],lvds3bits[3]};
samplevalue24  <= {lvdsbitsC_o[4],lvds3bits[104],lvdsbitsC_o[14],lvds3bits[84],lvds3bits[74],lvds3bits[64],lvds3bits[54],lvds3bits[44],lvds3bits[34],lvds3bits[24],lvds3bits[14],lvds3bits[4]};
samplevalue25  <= {lvdsbitsC_o[5],lvds3bits[105],lvdsbitsC_o[15],lvds3bits[85],lvds3bits[75],lvds3bits[65],lvds3bits[55],lvds3bits[45],lvds3bits[35],lvds3bits[25],lvds3bits[15],lvds3bits[5]};
samplevalue26  <= {lvdsbitsC_o[6],lvds3bits[106],lvdsbitsC_o[16],lvds3bits[86],lvds3bits[76],lvds3bits[66],lvds3bits[56],lvds3bits[46],lvds3bits[36],lvds3bits[26],lvds3bits[16],lvds3bits[6]};
samplevalue27  <= {lvdsbitsC_o[7],lvds3bits[107],lvdsbitsC_o[17],lvds3bits[87],lvds3bits[77],lvds3bits[67],lvds3bits[57],lvds3bits[47],lvds3bits[37],lvds3bits[27],lvds3bits[17],lvds3bits[7]};
samplevalue28  <= {lvdsbitsC_o[8],lvds3bits[108],lvdsbitsC_o[18],lvds3bits[88],lvds3bits[78],lvds3bits[68],lvds3bits[58],lvds3bits[48],lvds3bits[38],lvds3bits[28],lvds3bits[18],lvds3bits[8]};
samplevalue29  <= {lvdsbitsC_o[9],lvds3bits[109],lvdsbitsC_o[19],lvds3bits[89],lvds3bits[79],lvds3bits[69],lvds3bits[59],lvds3bits[49],lvds3bits[39],lvds3bits[29],lvds3bits[19],lvds3bits[9]};
sampleclkstr20 <= {lvds3bits[130],lvds3bits[120]};
sampleclkstr21 <= {lvds3bits[131],lvds3bits[121]};
sampleclkstr22 <= {lvds3bits[132],lvds3bits[122]};
sampleclkstr23 <= {lvds3bits[133],lvds3bits[123]};
sampleclkstr24 <= {lvds3bits[134],lvds3bits[124]};
sampleclkstr25 <= {lvds3bits[135],lvds3bits[125]};
sampleclkstr26 <= {lvds3bits[136],lvds3bits[126]};
sampleclkstr27 <= {lvds3bits[137],lvds3bits[127]};
sampleclkstr28 <= {lvds3bits[138],lvds3bits[128]};
sampleclkstr29 <= {lvds3bits[139],lvds3bits[129]};

samplevalue20sync  <= samplevalue20 ;
samplevalue21sync  <= samplevalue21 ;
samplevalue22sync  <= samplevalue22 ;
samplevalue23sync  <= samplevalue23 ;
samplevalue24sync  <= samplevalue24 ;
samplevalue25sync  <= samplevalue25 ;
samplevalue26sync  <= samplevalue26 ;
samplevalue27sync  <= samplevalue27 ;
samplevalue28sync  <= samplevalue28 ;
samplevalue29sync  <= samplevalue29 ;
sampleclkstr20sync <= sampleclkstr20;
sampleclkstr21sync <= sampleclkstr21;
sampleclkstr22sync <= sampleclkstr22;
sampleclkstr23sync <= sampleclkstr23;
sampleclkstr24sync <= sampleclkstr24;
sampleclkstr25sync <= sampleclkstr25;
sampleclkstr26sync <= sampleclkstr26;
sampleclkstr27sync <= sampleclkstr27;
sampleclkstr28sync <= sampleclkstr28;
sampleclkstr29sync <= sampleclkstr29;
end

always @ (posedge clklvds270) begin
samplevalue30  <= {lvds4bits[110],lvds4bits[100],lvdsbits_short[0],lvds4bits[80],lvds4bits[70],lvds4bits[60],lvds4bits[50],lvds4bits[40],lvds4bits[30],lvds4bits[20],lvds4bits[10],lvds4bits[0]};
samplevalue31  <= {lvds4bits[111],lvds4bits[101],lvdsbits_short[1],lvds4bits[81],lvds4bits[71],lvds4bits[61],lvds4bits[51],lvds4bits[41],lvds4bits[31],lvds4bits[21],lvds4bits[11],lvds4bits[1]};
samplevalue32  <= {lvds4bits[112],lvds4bits[102],lvdsbits_short[2],lvds4bits[82],lvds4bits[72],lvds4bits[62],lvds4bits[52],lvds4bits[42],lvds4bits[32],lvds4bits[22],lvds4bits[12],lvds4bits[2]};
samplevalue33  <= {lvds4bits[113],lvds4bits[103],lvdsbits_short[3],lvds4bits[83],lvds4bits[73],lvds4bits[63],lvds4bits[53],lvds4bits[43],lvds4bits[33],lvds4bits[23],lvds4bits[13],lvds4bits[3]};
samplevalue34  <= {lvds4bits[114],lvds4bits[104],lvdsbits_short[4],lvds4bits[84],lvds4bits[74],lvds4bits[64],lvds4bits[54],lvds4bits[44],lvds4bits[34],lvds4bits[24],lvds4bits[14],lvds4bits[4]};
samplevalue35  <= {lvds4bits[115],lvds4bits[105],lvdsbits_short[5],lvds4bits[85],lvds4bits[75],lvds4bits[65],lvds4bits[55],lvds4bits[45],lvds4bits[35],lvds4bits[25],lvds4bits[15],lvds4bits[5]};
samplevalue36  <= {lvds4bits[116],lvds4bits[106],lvdsbits_short[6],lvds4bits[86],lvds4bits[76],lvds4bits[66],lvds4bits[56],lvds4bits[46],lvds4bits[36],lvds4bits[26],lvds4bits[16],lvds4bits[6]};
samplevalue37  <= {lvds4bits[117],lvds4bits[107],lvdsbits_short[7],lvds4bits[87],lvds4bits[77],lvds4bits[67],lvds4bits[57],lvds4bits[47],lvds4bits[37],lvds4bits[27],lvds4bits[17],lvds4bits[7]};
samplevalue38  <= {lvds4bits[118],lvds4bits[108],lvdsbits_short[8],lvds4bits[88],lvds4bits[78],lvds4bits[68],lvds4bits[58],lvds4bits[48],lvds4bits[38],lvds4bits[28],lvds4bits[18],lvds4bits[8]};
samplevalue39  <= {lvds4bits[119],lvds4bits[109],lvdsbits_short[9],lvds4bits[89],lvds4bits[79],lvds4bits[69],lvds4bits[59],lvds4bits[49],lvds4bits[39],lvds4bits[29],lvds4bits[19],lvds4bits[9]};
sampleclkstr30 <= {lvds4bits[130],lvds4bits[120]};
sampleclkstr31 <= {lvds4bits[131],lvds4bits[121]};
sampleclkstr32 <= {lvds4bits[132],lvds4bits[122]};
sampleclkstr33 <= {lvds4bits[133],lvds4bits[123]};
sampleclkstr34 <= {lvds4bits[134],lvds4bits[124]};
sampleclkstr35 <= {lvds4bits[135],lvds4bits[125]};
sampleclkstr36 <= {lvds4bits[136],lvds4bits[126]};
sampleclkstr37 <= {lvds4bits[137],lvds4bits[127]};
sampleclkstr38 <= {lvds4bits[138],lvds4bits[128]};
sampleclkstr39 <= {lvds4bits[139],lvds4bits[129]};












samplevalue30sync  <= samplevalue30 ;
samplevalue31sync  <= samplevalue31 ;
samplevalue32sync  <= samplevalue32 ;
samplevalue33sync  <= samplevalue33 ;
samplevalue34sync  <= samplevalue34 ;
samplevalue35sync  <= samplevalue35 ;
samplevalue36sync  <= samplevalue36 ;
samplevalue37sync  <= samplevalue37 ;
samplevalue38sync  <= samplevalue38 ;
samplevalue39sync  <= samplevalue39 ;
sampleclkstr30sync <= sampleclkstr30;
sampleclkstr31sync <= sampleclkstr31;
sampleclkstr32sync <= sampleclkstr32;
sampleclkstr33sync <= sampleclkstr33;
sampleclkstr34sync <= sampleclkstr34;
sampleclkstr35sync <= sampleclkstr35;
sampleclkstr36sync <= sampleclkstr36;
sampleclkstr37sync <= sampleclkstr37;
sampleclkstr38sync <= sampleclkstr38;
sampleclkstr39sync <= sampleclkstr39;
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
		lvds1bitsfifoout <= {
		sampleclkstr39sync2,samplevalue39sync2,
		sampleclkstr38sync2,samplevalue38sync2,
		sampleclkstr37sync2,samplevalue37sync2,
		sampleclkstr36sync2,samplevalue36sync2,
		sampleclkstr35sync2,samplevalue35sync2,
		sampleclkstr34sync2,samplevalue34sync2,
		sampleclkstr33sync2,samplevalue33sync2,
		sampleclkstr32sync2,samplevalue32sync2,
		sampleclkstr31sync2,samplevalue31sync2,
		sampleclkstr30sync2,samplevalue30sync2,
		
		sampleclkstr29sync2,samplevalue29sync2,
		sampleclkstr28sync2,samplevalue28sync2,
		sampleclkstr27sync2,samplevalue27sync2,
		sampleclkstr26sync2,samplevalue26sync2,
		sampleclkstr25sync2,samplevalue25sync2,
		sampleclkstr24sync2,samplevalue24sync2,
		sampleclkstr23sync2,samplevalue23sync2,
		sampleclkstr22sync2,samplevalue22sync2,
		sampleclkstr21sync2,samplevalue21sync2,
		sampleclkstr20sync2,samplevalue20sync2,
		
		sampleclkstr19sync2,samplevalue19sync2,
		sampleclkstr18sync2,samplevalue18sync2,
		sampleclkstr17sync2,samplevalue17sync2,
		sampleclkstr16sync2,samplevalue16sync2,
		sampleclkstr15sync2,samplevalue15sync2,
		sampleclkstr14sync2,samplevalue14sync2,
		sampleclkstr13sync2,samplevalue13sync2,
		sampleclkstr12sync2,samplevalue12sync2,
		sampleclkstr11sync2,samplevalue11sync2,
		sampleclkstr10sync2,samplevalue10sync2,
		
		sampleclkstr9sync2,samplevalue9sync2,
		sampleclkstr8sync2,samplevalue8sync2,
		sampleclkstr7sync2,samplevalue7sync2,
		sampleclkstr6sync2,samplevalue6sync2,
		sampleclkstr5sync2,samplevalue5sync2,
		sampleclkstr4sync2,samplevalue4sync2,
		sampleclkstr3sync2,samplevalue3sync2,
		sampleclkstr2sync2,samplevalue2sync2,
		sampleclkstr1sync2,samplevalue1sync2,
		sampleclkstr0sync2,samplevalue0sync2
		};
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
	triggercounter3 <= triggercounter2;
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
		pllreset2 <= 1'b0;
		lvds1rd <= 1'b0;
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
			length <= {rx_data[7],rx_data[6],rx_data[5],rx_data[4]};
			state <= TX_DATA1;
		end
		
		1 : begin // reset plls
			pllreset2 <= 1'b1;
			o_tdata <= 33;
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
			if (triggercounter3 == -16'd1) begin
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
