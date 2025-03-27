# Offline GSM SMS Sender

Yeh tool GSM module (SIM800L/SIM900A) ke through bina internet ke SMS bhejne ke liye banaya gaya hai.  
Script interactive input leta hai ya command-line arguments se parameters pass kiye ja sakte hain.

## Features

- Bina internet ke SMS bhejna using GSM module.
- Serial port aur baud rate configuration.
- Option to run as a daemon (background process) taki Termux exit hone ke baad bhi kaam kare.

## Requirements

- Python 3.x
- [pyserial](https://pypi.org/project/pyserial/)

## Setup

1. Repository clone ya download karein.
2. Install dependencies:
   ```bash
   pip3 install -r requirements.txt
   
