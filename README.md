# ✉️ Autonomous AI Email Agent

A robust, privacy-first Python automation agent that reads, categorizes, and automatically replies to your unread Gmail messages using a local Large Language Model (LLM) powered by **Ollama**.

Because the LLM runs entirely on your local machine, **none of your private email content is ever sent to third-party APIs (like OpenAI or Anthropic).**

## ✨ Features

- **100% Local AI:** Uses `gemma3:4b` (or any model via Ollama) to generate context-aware, professional replies locally.
- **Gmail API Integration:** Securely connects to your Gmail inbox via OAuth 2.0 to fetch unread messages and send replies within the same thread.
- **Smart Filtering:** Automatically skips system alerts, no-reply addresses, and security notifications using a customizable keyword filter.
- **Human-in-the-Loop Mode:** Built-in manual approval system (`MANUAL_APPROVAL = True`) allowing you to review and approve AI-generated drafts before they are sent.
- **Continuous Polling:** Runs continuously in the background, monitoring the inbox at fixed intervals.

## 🛠️ Tech Stack

- **Language:** Python 3.10+
- **AI/LLM Engine:** [Ollama](https://ollama.com/) (Local deployment)
- **API:** Google Gmail API (`google-api-python-client`)
- **Authentication:** OAuth 2.0 (`google-auth-oauthlib`)

## 🚀 Installation & Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/your-username/autonomous-email-agent.git
   cd autonomous-email-agent
   ```

2. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Install & Run Ollama:**
   Download and install Ollama from [ollama.com](https://ollama.com). Open your terminal and pull the desired model:
   ```bash
   ollama run gemma3:4b
   ```

4. **Configure Google API Credentials:**
   - Go to the [Google Cloud Console](https://console.cloud.google.com/).
   - Create a project, enable the **Gmail API**, and configure the OAuth consent screen.
   - Create OAuth Client ID credentials (Desktop App) and download the JSON file.
   - Rename the downloaded file to `credentials.json` and place it in the root folder of this project.

## ⚙️ Usage

Start the bot by running:
```bash
python main.py
```
*On the first run, a browser window will open asking you to authenticate with your Google account. This will generate a `token.json` file for future passwordless logins.*

## 🔒 Security & Privacy Notes
- **`credentials.json` and `token.json` are strictly ignored in `.gitignore`. Never commit these files to a public repository.**
- All AI processing occurs locally on your hardware. No email data leaves your machine except when communicating directly with Google's Gmail API.
