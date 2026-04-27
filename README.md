# PrivyChat

PrivyChat is a secure messaging web application designed for small and medium-sized enterprises (SMEs).  
The system focuses on privacy-aware communication by addressing common limitations in existing messaging platforms, particularly metadata exposure and lack of organisational control.

## Features
- User registration and authentication
- Group chat within company workspaces
- Direct messaging between users
- Private team chat for restricted communication
- Admin panel for user approval and management
- GDPR-compliant features (privacy policy consent and data deletion)

## Technologies Used
- Python (Flask)
- HTML, CSS, JavaScript
- SQLite (database)

## System Design
The application follows a client-server architecture:
- Frontend handles user interaction and interface
- Backend (Flask) manages logic, authentication, and messaging
- SQLite database stores users and messages

## Security Features
- Password hashing using Werkzeug
- Session-based authentication
- Company-based access control (data isolation)
- Basic role-based access (admin and user)

## Limitations
- No end-to-end encryption (messages stored in plaintext)
- Polling used instead of WebSockets (may cause delays)
- Limited role-based access control

## Future Improvements
- Implement end-to-end encryption
- Introduce WebSockets for real-time messaging
- Improve metadata minimisation
- Add audit logging and advanced access controls
- Conduct usability testing with real SME users

## How to Run
1. Install Python
2. Install Flask:
