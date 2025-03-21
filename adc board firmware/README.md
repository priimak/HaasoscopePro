# For compiling and uploading firmware

Install Quartus Prime Lite (free)
 - Tested on Windows, but Linux should work too
 - Tested with version 23.1, but newer should also be OK

Open the **adc_board_firmware/coincidence.qpf** project file in this directory with Quartus Prime Lite
 - File... Open Project

If you've made changes to the code, recompile
 - Processing... Start Compilation (or the "play" button in the menu bar)

To upload firmware to board:
 - Attach power to board
 - Attach USB Blaster to board via JTAG (to set up the usb blaster see tips below)
 - Tools... Programmer
   - Hardware Setup... select USB blaster by double clicking, then close
   - (If you need permanent writing to the board flash, and have recompiled, remake the jic file by doing File... Convert Programming Files, then Open Conversion Setup Data..., select **adc_board_firmware/coincidence.cof**, then Generate button at bottom)
   - Add File... **adc_board_firmware/output_files/coincidence.sof** (for temporary testing) or **adc_board_firmware/output_files/coincidence.jic** (for permanent writing to the board flash memory)
   - Select checkbox Program/Configure
   - Start

To setup USB Blaster on Windows:
 - After plugging in the USB Blaster, it may appear as an unrecognized device in the device manager. If so, you need to install a driver for it. Drivers come with the Quartus installation (even the "programmer only" version). Follow these instructions to install the driver:<br>
Plug in the USB blaster device, go to it in the device manager, and do Update driver, then Browse my computer for drivers, Let me pick from a list of devices, select JTAG cables, Have disk, and select the intelFPGA_lite\<version>\quartus\drivers\usb-blaster-ii directory, and install.

To setup USB Blaster on Linux:
 - In theory it should work out of the box, but you just need permissions to access it. Try this and then plug it in: <code>sudo cp HaasoscopePro/software/blaster.rules /etc/udev/rules.d/</code>

Tips in case of problems:
 - Maybe the USB-blaster must first be powered from the board and then connected to the PC. So the procedure step by step: connect the USB-Blaster to your board, power-on the board, plug the USB cable in the PC.

Screenshots for temporary (sof) or permanent flash (jic) programming:

![Screenshot 2025-03-10 155821](https://github.com/user-attachments/assets/a48c5c72-e71a-4d7f-8bfe-ed48cdbfaf09)

![Screenshot 2025-03-10 155805](https://github.com/user-attachments/assets/000f7881-6075-42fd-b315-97af277fd60a)

