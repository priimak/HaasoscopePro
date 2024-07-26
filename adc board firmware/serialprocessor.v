module processor(clk, 
	phasecounterselect,phaseupdown,phasestep,scanclk, clkswitch
	);
	
	input clk;
	
	localparam START=0, CLKSWITCH1=1, CLKSWITCH2=3, PHASEALL=4, PHASE1=5, PLLCLOCK=6;
	reg[7:0] state=START;
	
	reg[7:0] pllclock_counter=0;
	reg[7:0] scanclk_cycles=0;
	output reg[2:0] phasecounterselect; // Dynamic phase shift counter Select. 000:all 001:M 010:C0 011:C1 100:C2 101:C3 110:C4. Registered in the rising edge of scanclk.
	output reg phaseupdown=1; // Dynamic phase shift direction; 1:UP, 0:DOWN. Registered in the PLL on the rising edge of scanclk.
	output reg phasestep=0;
	output reg scanclk=0;
	output reg clkswitch=0; // No matter what, inclk0 is the default clock

	always @(posedge clk) begin
	case (state)
	START: begin		  
		
		
	end
   CLKSWITCH1: begin
		//toggle clk inputs
		pllclock_counter=0;			
		clkswitch = 1;
		state=CLKSWITCH2;
	end
	CLKSWITCH2: begin // to switch between clock inputs, put clkswitch high for a few cycles, then back down low
		pllclock_counter=pllclock_counter+1;
		if (pllclock_counter[3]) begin
			clkswitch = 0;
			state=START;
		end
	end
	PHASEALL: begin
		//adjust clock phases
		phasecounterselect=3'b000; // all clocks - see https://www.intel.com/content/dam/www/programmable/us/en/pdfs/literature/hb/cyc3/cyc3_ciii51006.pdf table 5-10
		//phaseupdown=1'b1; // up
		scanclk=1'b0; // start low
		phasestep=1'b1; // assert!
		pllclock_counter=0;
		scanclk_cycles=0;
		state=PLLCLOCK;
	end
	PHASE1: begin
		//adjust phase of clock c1
		phasecounterselect=3'b011; // clock c1 - see https://www.intel.com/content/dam/www/programmable/us/en/pdfs/literature/hb/cyc3/cyc3_ciii51006.pdf table 5-10
		//phaseupdown=1'b1; // up
		scanclk=1'b0; // start low
		phasestep=1'b1; // assert!
		pllclock_counter=0;
		scanclk_cycles=0;
		state=PLLCLOCK;
	end	
	PLLCLOCK: begin // to step the clock phase, you have to toggle scanclk a few times
		pllclock_counter=pllclock_counter+1;
		if (pllclock_counter[4]) begin
			scanclk = ~scanclk;
			pllclock_counter=0;
			scanclk_cycles=scanclk_cycles+1;
			if (scanclk_cycles>5) phasestep=1'b0; // deassert!
			if (scanclk_cycles>7) state=START;
		end
	end


	endcase
	end  
	
endmodule
