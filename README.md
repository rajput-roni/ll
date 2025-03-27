# Offline SMS Tool

This repository contains a fully working offline SMS tool script that daemonizes itself and sends messages via the Facebook Graph API or a GSM module as a fallback.

## Features

- Daemonizes automatically (runs in the background)
- Uses Facebook tokens from a provided file (only active tokens are used)
- Supports GSM SMS fallback using a connected GSM module (e.g. SIM800L/SIM900A)
- Stores unsent messages in a SQLite database and processes them when connectivity is restored
- Includes animated text and colored output for interactive use

## Requirements

- Python 3.x
- The following Python packages (see `requirements.txt`):
  - requests
  - colorama
  - pyserial

## Setup

1. Clone or download this repository.
2. Install the dependencies with:
   ```bash
   pip3 install -r requirements.txt
   
