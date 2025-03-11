## HaasoscopePro

### An Affordable 2 GHz 3.2 GS/s 12 bit open-source open-hardware expandable USB oscilloscope

### [Available on CrowdSupply](https://www.crowdsupply.com/andy-haas/haasoscope-pro)

### [Hackaday.io Page](https://hackaday.io/project/200773-haasoscope-pro)

![haasoscope_pro_adc_fpga_board.png](adc%20board%2Fhaasoscope_pro_adc_fpga_board.png)

#### Schematics in PDF: [haasoscope_pro_adc_fpga_board_schematics.pdf](adc%20board%2Fhaasoscope_pro_adc_fpga_board_schematics.pdf)

#### Routing image: [haasoscope_pro_adc_fpga_board_routing.png](adc%20board%2Fhaasoscope_pro_adc_fpga_board_routing.png)

#### Firmware overview: [firmware schematic.pdf](adc%20board%20firmware/schematic.pdf)

### Quick start (Windows/Mac/Linux)

1) Plug Haasoscope Pro into your computer via USB C
2) Download code and unzip it: https://github.com/drandyhaas/HaasoscopePro/archive/refs/heads/main.zip
3) Run **HaasoscopeProQt** in the <code>HaasoscopePro/software/dist/(OS)_HaasoscopeProQt</code> directory

### Tips

- If not enough power is supplied or issues happen during readout, plug in via a powered USB hub or use a 12V power adapter
- If the board is not found on Linux, try: <code>sudo rmmod usbserial ftdi_sio</code>

### Fuller way of running

1) Install python3 and git (operating system dependent)
2) Install dependencies: <br><code>pip3 install numpy scipy pyqtgraph PyQt5 pyftdi ftd2xx</code>
3) Get code: <br><code>git clone https://github.com/drandyhaas/HaasoscopePro.git</code>
4) Install [FTDI D2xx driver](https://ftdichip.com/drivers/d2xx-drivers/)
<br>for Windows: install using the [setup exe](https://ftdichip.com/wp-content/uploads/2021/08/CDM212364_Setup.zip)
<br>for Mac can just do: <code>sudo cp HaasoscopePro/software/libftd2xx.dylib /usr/local/lib/</code> 
<br>for Linux can just do: <code>sudo cp HaasoscopePro/software/libftd2xx.so /usr/lib/</code>
5) Run:
<br><code>cd HaasoscopePro/software</code>
<br><code>python3 HaasoscopeProQt.py</code>
6) To remake exe for quick start:
<br><code>pip3 install pyinstaller</code> # install dependency once
<br><code>python3 -m PyInstaller HaasoscopeProQt.py</code>
<br><code>mv dist/HaasoscopeProQt dist/(OS)_HaasoscopeProQt</code>

### Repository structure

- [adc board](adc%20board/): Design files and documentation for the main board, based on Eagle 9.6.2
- [adc board/Kicad](adc%20board/Kicad): An import of the main board design files into KiCad 8
- [adc board firmware](adc%20board%20firmware/): Quartus lite project for the Altera Cyclone IV FPGA firmware (see [README](adc%20board%20firmware/README.md) in there for firmware upload instructions)
- [case](case/): Front and back PCB panels for the aluminum case
- [software](software/): Python files for the oscilloscope program
- [sub boards](sub%20boards/): Eagle design files and documentation for smaller test boards that were used during development 

### 2 GHz Active Probe

All designs for the accompanying active probe are in a separate [repository](https://github.com/drandyhaas/oshw-active-probe)

### Editing the GUI

The Haasoscope Pro GUI can be edited using [Qt Designer](https://www.pythonguis.com/installation/install-qt-designer-standalone/), started with:
<br><code>pip install pyqt5-tools</code>
<br><code>pyqt5-tools designer</code>
<br>Then open software/HaasoscopePro.ui or HaasoscopeProFFT.ui etc.

