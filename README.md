# Offline SMS Sender with GSM Fallback

यह repository एक Python script प्रदान करती है जो Facebook API के माध्यम से SMS भेजती है और यदि इंटरनेट उपलब्ध न हो तो GSM SMS fallback का उपयोग करती है। 

## Features
- Facebook API के माध्यम से SMS भेजना
- GSM मॉड्यूल (जैसे SIM800L/SIM900A) के माध्यम से offline SMS भेजना
- Background में daemonize mode में चलाना
- SQLite3 DB integration for offline queue and logging

## Installation

1. Repository clone करें:
   ```bash
   git clone https://github.com/yourusername/set-up-offline-sms.git
   cd set-up-offline-sms
