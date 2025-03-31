# Offline SMS Sender with GSM Fallback

यह repository एक Python script प्रदान करती है जो Facebook API के माध्यम से SMS भेजती है और यदि इंटरनेट उपलब्ध न हो तो GSM मॉड्यूल के जरिए SMS भेजने का fallback उपयोग करती है।

## Features

- **Facebook Messenger Integration:** इंटरनेट उपलब्ध होने पर Facebook API से मैसेज भेजना।
- **GSM SMS Fallback:** इंटरनेट unavailable होने पर /dev/ttyUSB0 पर कनेक्ट GSM मॉड्यूल के माध्यम से SMS भेजना।
- **Daemonize Mode:** बैकग्राउंड में चलने की क्षमता, जिससे Termux exit होने पर भी स्क्रिप्ट active रहे।
- **SQLite3 Logging:** भेजे गए मैसेजों का लॉग रखने के लिए SQLite3 का उपयोग।

## Installation

1. Repository clone करें:
   ```bash
   git clone https://github.com/yourusername/set-up-offline-sms.git
   cd set-up-offline-sms
