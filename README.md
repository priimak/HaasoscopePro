## HaasoscopePro

### An Affordable 2 GHz 3.2 GS/s 12 bit open-source open-hardware expandable USB oscilloscope

### [Available on CrowdSupply](https://www.crowdsupply.com/andy-haas/haasoscope-pro)

![haasoscope_pro_adc_fpga_board.png](adc%20board%2Fhaasoscope_pro_adc_fpga_board.png)

#### Schematics in PDF: [haasoscope_pro_adc_fpga_board_schematics.pdf](adc%20board%2Fhaasoscope_pro_adc_fpga_board_schematics.pdf)

#### Routing image: [haasoscope_pro_adc_fpga_board_routing.png](adc%20board%2Fhaasoscope_pro_adc_fpga_board_routing.png)

### Quick start

1) Plug Haasoscope Pro into your computer via USB C <br>
(If not enough power is supplied also plug in the external 12V power adapter)
2) Download code and unzip it: https://github.com/drandyhaas/HaasoscopePro/archive/refs/heads/main.zip
3) Run **HaasoscopeProQt** in the <code>HaasoscopePro/software/dist/(OS)_HaasoscopeProQt</code> directory

### Fuller way of running (Windows/Mac/Linux)

1) Install python3 and git (operating system dependent)

2) Install dependencies:
<code>
<br>pip3 install numpy scipy pyqtgraph PyQt5 pyftdi ftd2xx
</code>

3) Get code: <code>
<br>git clone https://github.com/drandyhaas/HaasoscopePro.git
</code>

4) Install driver: https://ftdichip.com/drivers/d2xx-drivers/
<br>for Mac can just do: <code>sudo cp HaasoscopePro/software/libftd2xx.dylib /usr/local/lib/</code> 
<br>for Linux can just do: <code>sudo cp HaasoscopePro/software/libftd2xx.so /usr/lib/</code>

5) Run: <code>
<br>cd HaasoscopePro/software
<br>python3 HaasoscopeProQt.py
</code>

6) To remake exe for quick start:
<code>
<br>pip3 install pyinstaller # install dependency once
<br>python3 -m PyInstaller HaasoscopeProQt.py
</code>

### Repository structure:
- <code>adc board</code>: Design files and documentation for the main hardware board, based on Eagle (9.6.2)
- <code>adc board firmware</code>: Quartus (23.1 lite) project for the Altera Cyclone IV FPGA firmware
- <code>case</code>: Front and back PCB panels for the aluminum case
- <code>software</code>: Python files for the oscilloscope program
- <code>(other directories)</code>: Design files and documentation for smaller test boards that were used during development 

