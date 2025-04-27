# HD44780 SIM

A simple simulator for HD44780-based displays with CoCoTB.

> **HD44780 SIM** is an open-source simulation tool that _**barely**_ mimics the behavior of standard HD44780 LCD modules using `pygame`. It’s designed to assist developers and hardware enthusiasts in verifying and validating their HDL designs and firmware intended for HD44780 displays—all without needing physical hardware.

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Requirements](#requirements)
- [Installation](#installation)
- [Usage](#usage)
- [License](#license)

---

## Overview

The **HD44780 SIM** project provides a simulation environment for HD44780-style character displays. Whether you’re developing an embedded system or experimenting with HDL (Verilog/VHDL) designs, this simulator allows you to see **almost** exactly how your design will interact with the Hitachi HD44780 LCD display controller. By integrating CoCoTB as the verification engine, the simulator delivers a flexible, coroutine-based testbench for running simulation scenarios reliably.

This project is the perfect starting point for:
- Rapid prototyping and debugging of display interfacing.
- Validating timing and behavior of custom HDL modules.
- Experimenting with command processing and display control logic without extensive hardware setup.

---

## Features

- **Realistic Simulation:** Emulates the standard functions of an HD44780 controller, including **some** instruction processing and data display.
- **CoCoTB Integration:** Uses CoCoTB for a coroutine-based verification environment, allowing for efficient and dynamic test setups.
- **Customizable Testbench:** Easily modify or extend simulation scenarios to suit your specific development needs.
- **Ease of Use:** Designed to run with minimal setup—clone the repository, install dependencies using Poetry, and simulate!

---

## Requirements

Ensure you have the following installed on your system:

- **Python 3.6+** – The foundation for running CoCoTB.
- **Poetry** – Dependency management and packaging tool for Python.
- **CoCoTB** – The coroutine-based cosimulation library.  
  (Installation instructions can be found on the [CoCoTB website](https://cocotb.org/).)
- **HDL Simulator** – A supported simulator (e.g., [GHDL](https://ghdl.github.io/), [Icarus Verilog](http://iverilog.icarus.com/), etc.) compatible with CoCoTB.

Any additional Python dependencies are managed via Poetry in the `pyproject.toml` file.

---

## Installation

1. **Clone the Repository**

  ```bash
  git clone https://github.com/anubhav-narayan/hd44780_sim.git
  cd hd44780_sim
  ```

2. **Poetry Install**

  ```bash
  poetry install
  ```

3. **Virtual Environment**

  ```bash
  poetry shell
  ```
  or
  ```bash
  poetry env activate
  ```

4. **Run CoCoTB as usual**

  That should be it.

---

## Usage

```python
  from hd77480 import HD44780Sim
  lcd = HD44780Sim(dut, 'lcd', lines=2, segments=16, pixel_size=5, pixel_border=0.15, line_margin=10)
  lcd.start()
  ...
  cocotb.start_soon(lcd.run_coro())
```

---

## License

This project is licensed under the GNU General Public License v3.0. See the [LICENSE](LICENSE.md) file for more details.

---

## Acknowledgements

- **CoCoTB:** Thanks to the CoCoTB team for creating an amazing coroutine-based verification framework.
- **HD44780 Documentation:** A nod to all the technical resources detailing the behavior of HD44780-based LCDs.
- **Community Contributions:** Every user, tester, and contributor who enhances projects like these.

---

*Happy simulating! Explore, experiment, and feel free to reach out with questions or suggestions.*

