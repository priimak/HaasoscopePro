## HaasoscopePro

### An Affordable 2 GHz 3.2 GS/s 12 bit open-source open-hardware expandable USB oscilloscope

### [Available on CrowdSupply](https://www.crowdsupply.com/andy-haas/haasoscope-pro)

![haasoscope_pro_adc_fpga_board.png](adc%20board%2Fhaasoscope_pro_adc_fpga_board.png)

#### Schematics in PDF: [haasoscope_pro_adc_fpga_board_schematics.pdf](adc%20board%2Fhaasoscope_pro_adc_fpga_board_schematics.pdf)

#### Routing image: [haasoscope_pro_adc_fpga_board_routing.png](adc%20board%2Fhaasoscope_pro_adc_fpga_board_routing.png)

### Quick start

Windows:
<pre>
tinyurl.com/HaasoscopeProWin
unzip
run HaasoscopeProQt.exe
</pre>

Mac:
<pre>
tinyurl.com/HaasoscopeProMac
unzip
sudo cp libftd2xx.dylib /usr/local/lib/ # install driver, just need to do once
./HaasoscopeProQt
</pre>

Also works on Linux...

### Fuller way of running (Win/Mac/Linux)
<pre>
# install python3 and git
#(operating system dependent)

# install dependencies
pip3 install numpy scipy pyqtgraph PyQt5 pyftdi ftd2xx

# download code
git clone https://github.com/drandyhaas/HaasoscopePro.git

# install driver
https://ftdichip.com/drivers/d2xx-drivers/
# for mac can just do: sudo cp HaasoscopePro/software/libftd2xx.dylib /usr/local/lib/
# for linux can just do: sudo cp HaasoscopePro/software/libftd2xx.so /usr/lib/

# run
cd HaasoscopePro/software
python3 HaasoscopeProQt.py

# to remake exe that goes into zip file for quick start
pip3 install pyinstaller # install dependency once
python3 -m PyInstaller HaasoscopeProQt.py
</pre>

### Repository structure:
- adc board: Design files and documentation for the main hardware board, based on Eagle (9.6.2)
- adc board firmware: Quartus (23.1 lite) project for the Altera Cyclone IV FPGA firmware
- case: Front and back PCB panels for the aluminum case
- software: Python files for the oscilloscope program
- other directories: Design files and documentation for smaller test boards that were used during development 

