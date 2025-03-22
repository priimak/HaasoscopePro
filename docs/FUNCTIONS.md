Low Level Board Functions
=========================

For function call 8 bytes are sent over USB. First and sometimes 
second byte (depending on the function) are used to define function. Remaining bytes
are used as arguments. Table below lists these functions. Letter "A" refer to the fact 
that that particular byte used as an argument. Character "-" indicates that that 
particular byte is not used and thus its value ignored by the function. 

| Command                                      | 0  | 1 | 2 | 3 | 4 | 5 | 6 | 7 |
|----------------------------------------------|----|---|---|---|---|---|---|---|
| **get_waveform_data**                            | 0  | - | - | - | A | A | A | A |
| arm_trigger                                  | 1  | A | A | - | A | A | - | - |
| **get_version**                              | 2  | 0 | - | - | - | - | - | - |
| **get_boardin**                              | 2  | 1 | - | - | - | - | - | - |
| **get_overrange_counter**                    | 2  | 2 | A | - | - | - | - | - |
| **get_eventconter**                          | 2  | 3 | - | - | - | - | - | - |
| **get_downsample_merging_counter_triggered** | 2  | 4 | - | - | - | - | - | - |
| set_lvdsout_spare                            | 2  | 5 | A | - | - | - | - | - |
| **set_fanon**                                | 2  | 6 | A | - | - | - | - | - |
| **set_prelength_to_take**                    | 2  | 7 | A | A | - | - | - | - |
| **set_rolling**                              | 2  | 8 | A | - | - | - | - | - |
| spi_command                                  | 3  | A | A | A | A | A | A | A |
| **set_spi_mode**                             | 4  | A | - | - | - | - | - | - |
| **reset_plls**                               | 5  | - | - | - | - | - | - | - |
| **set_clk_phase_adjust**                     | 6  | A | A | A | - | - | - | - |
| **clk_switch**                               | 7  | - | - | - | - | - | - | - |
| set_trigger_props                            | 8  | A | A | A | A | A | A | - |
| set_downsample                               | 9  | A | A | A | - | - | - | - |
| set_boardout                                 | 10 | A | A | - | - | - | - | - |
| **set_led**                                      | 11 | A | A | - | - | - | - | - |

