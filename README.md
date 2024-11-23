
# Jarvoice API

Your smart voice-powered butler for research, scheduling & smart updates via calls & messages.

## 🌟 Features

- **Research Management**: Initiate and retrieve research on any topic  
- **Smart Scheduling**: Event planning with contextual reminders  
- **Task Management**: Create and track tasks with customizable priorities  
- **Contact Management**: Store and manage contact information  
- **SMS & Call Integration**: Automated notifications and voice interactions  
- **Timezone Support**: Global timezone handling for events and reminders  

## 🚀 Quick Start

### Prerequisites

- Python 3.11+  
- PostgreSQL (via Supabase)  
- Twilio Account (for SMS/calls)  

### Installation

1. Clone the repository:  
   ```bash
   git clone <repository-url>
   cd jarvoice-api
   ```

2. Create and activate virtual environment:  
   ```bash
   python -m venv venv
   source venv/bin/activate  # Unix/macOS
   # or
   .\venv\Scripts\activate  # Windows
   ```

3. Install dependencies:  
   ```bash
   pip install -r requirements.txt
   ```

4. Set up environment variables:  
   ```bash
   cp .env.example .env.local
   ```

   Required environment variables:  
   ```
   SUPABASE_URL=your_supabase_url
   SUPABASE_ANON_KEY=your_supabase_key
   TWILIO_ACCOUNT_SID=your_twilio_sid
   TWILIO_AUTH_TOKEN=your_twilio_token
   ```

### Running the Application

```bash
uvicorn main:app --reload
```

The API will be available at `http://localhost:8000`

## 📚 API Documentation

Once running, visit:  
- Swagger UI: `http://localhost:8000/docs`  
- ReDoc: `http://localhost:8000/redoc`


### Core Endpoints

- `POST /users`: Create new user  
- `GET /users/{user_id}`: Retrieve user details  
- `POST /tasks`: Create new task  
- `POST /events`: Create calendar event  
- `POST /contacts`: Add new contact  
- `POST /1/process`: Process tool calls for AI interactions  

## 🏗 Project Structure

```plaintext
jarvoice-api/
├── main.py              # FastAPI application and routes
├── base_models.py       # Pydantic models
├── tool_functions.py    # AI tool implementations
├── scheduler.py         # Task scheduling logic
├── outbound_caller.py   # Voice call handling
├── twilio_sms.py        # SMS functionality
└── tool_registry.py     # Tool function registry
```

## 🔧 Development

# Vapi Documentation Summary

## Adding Tools

Tools in Vapi are implemented through server URLs and function calls, enabling your assistant to interact with external services.

### Server URLs

Server URLs allow real-time communication between Vapi and your application. They enable you to:

- Receive conversation events (status updates, transcripts, function calls)
- Get dynamic assistant configurations
- Receive end-of-call reports

**To set up a server URL:**
1. Configure the URL in your assistant settings.
2. Implement an endpoint on your server to handle POST requests from Vapi.
3. Process the received data and respond as needed.

### Function Calls

Function calls allow your assistant to trigger specific actions during a conversation. You can define custom functions that your assistant can invoke, such as:

- Forwarding calls
- Hanging up
- Accessing external databases or APIs

## Key Configurations

### Ngrok for Local Development

For testing server URLs in a local development environment, you can use ngrok:

1. Install ngrok.
2. Run your local server.
3. Use ngrok to create a public URL for your local server.
4. Set the ngrok URL as your server URL in Vapi.

### Custom LLM URL

You can plug in your own Language Model by configuring a custom LLM URL, allowing you to use specialized or proprietary models for your assistant.

### Provider Keys

To integrate with external services (e.g., specific TTS, LLM, or STT vendors), add your API keys in the Vapi dashboard.

### Assistant Configuration

Assistants can be customized with various components:

- **Transcriber**: For speech-to-text conversion
- **Model**: The language model powering the assistant's responses
- **Voice**: The text-to-speech voice for the assistant

By leveraging these tools and configurations, you can create highly customized and powerful voice AI assistants using Vapi.

### Adding New Features to Backend after the above Vapi Voice api Configurations

1. Define new models in `base_models.py`  
2. Implement business logic in appropriate modules  
3. Add new endpoints in `main.py`  
4. Register new tool functions in `tool_registry.py`  

### Testing

```bash
# Run tests
pytest

# Test specific functionality
python -m pytest tests/test_specific.py
```

## 📦 Dependencies

Key packages:  
- `fastapi`: Web framework  
- `pydantic`: Data validation  
- `uvicorn`: ASGI server  
- `supabase`: Database client  
- `twilio`: SMS/Voice capabilities  
- `vapi`: Voice API integration  
- `apscheduler`: Task scheduling  

## 🔐 Security

- CORS middleware configured  
- Environment-based configuration  
- Supabase authentication  
- E.164 phone number validation  

## 🤝 Contributing

1. Fork the repository  
2. Create feature branch (`git checkout -b feature/amazing-feature`)  
3. Commit changes (`git commit -m 'Add amazing feature'`)  
4. Push to branch (`git push origin feature/amazing-feature`)  
5. Open Pull Request  

## 📄 License

[MIT License](LICENSE)  

## 👥 Contact

For support or queries, please open an issue in the repository.
```

Let me know if you'd like further adjustments!
