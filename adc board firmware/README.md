Install Quartus Prime Lite (free)
 - Tested on Windows, but Linux should work too
 - Tested with version 23.1, but newer should also be OK

Open the **coincidence.qpf** project file in this directory with Quartus Prime Lite
 - File... Open Project

If you've made changes to the code, recompile
 - Processing... Start Compilation (or the "play" button in the menu bar)

To upload firmware to board:
 - Attach power to board
 - Attach USB Blaster to board via JTAG
 - Tools... Programmer
   - Hardware Setup... select USB blaster by double clicking, then close
   - (If you need permanent writing to the board flash, and have recompiled, remake the jic file by doing File... Convert Programming Files, then Open Conversion Setup Data..., select **adc_board_firmware/coincidence.cof**, then Generate button at bottom)
   - Add File... **coincidence.sof** (for temporary testing) or **coincidence.jic** (for permanent writing to the board flash memory)
   - Select checkbox Program/Configure
   - Start
 
