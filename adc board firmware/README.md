Install Quartus Prime Lite (free)
 - Tested on Windows, but Linux should work too
 - Tested with version 23.1, but newer should also be OK

Open the **adc_board_firmware/coincidence.qpf** project file in this directory with Quartus Prime Lite
 - File... Open Project

If you've made changes to the code, recompile
 - Processing... Start Compilation (or the "play" button in the menu bar)

To upload firmware to board:
 - Attach power to board
 - Attach USB Blaster to board via JTAG (to set up the usb blaster [these hints](https://docs.google.com/document/d/1CwERi99UN8asUvkfyjQFWtYEEusfU2QxoBewEEcmuAA/edit?usp=drivesdk) may help)
 - Tools... Programmer
   - Hardware Setup... select USB blaster by double clicking, then close
   - (If you need permanent writing to the board flash, and have recompiled, remake the jic file by doing File... Convert Programming Files, then Open Conversion Setup Data..., select **adc_board_firmware/coincidence.cof**, then Generate button at bottom)
   - Add File... **adc_board_firmware/output_files/coincidence.sof** (for temporary testing) or **adc_board_firmware/output_files/coincidence.jic** (for permanent writing to the board flash memory)
   - Select checkbox Program/Configure
   - Start

Tips in case of problems:
 - Maybe the USB-blaster must first be powered from the board and then connected to the PC. So the procedure step by step: connect the USB-Blaster to your board, power-on the board, plug the USB cable in the PC.

Screenshots for temporary (sof) or permanent flash (jic) programming:

![Screenshot 2025-03-10 155821](https://github.com/user-attachments/assets/a48c5c72-e71a-4d7f-8bfe-ed48cdbfaf09)

![Screenshot 2025-03-10 155805](https://github.com/user-attachments/assets/000f7881-6075-42fd-b315-97af277fd60a)

