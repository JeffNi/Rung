# Rung

Job search assistant tool for cover letters, applications and interviews powered by AI.

## 🚀 Features

- **Smart Resume Builder**: Create professional resumes tailored to your industry
- **AI-Powered Cover Letters**: Generate personalized cover letters that match your voice
- **Job-Specific Optimization**: Optimize applications for specific job descriptions
- **User Account Management**: Save and manage your career documents

## 📋 Prerequisites

Before you begin, ensure you have the following installed:
- **Python 3.10+** (for backend)
- **Node.js 18+** and **npm** (for frontend)
- **Git** (to clone the repository)

## 🛠️ Setup Instructions

### 1. Clone the Repository

```bash
git clone https://github.com/YourUsername/Rung.git
cd Rung
```

### 2. Backend Setup

#### Create and activate a virtual environment:

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

**macOS/Linux:**
```bash
python -m venv venv
source venv/bin/activate
```

#### Install Python dependencies:

```bash
pip install -r backend\voicedraft\requirements.txt
```

#### Set up environment variables:

Create a `.env` file in the `backend/voicedraft` directory with your Google Gemini API key:

```
GEMINI_API_KEY=your_google_gemini_api_key_here
```

> **Note:** You can get a free API key from [Google AI Studio](https://aistudio.google.com/app/apikey)

### 3. Frontend Setup

#### Navigate to frontend directory and install dependencies:

```bash
cd frontend
npm install
cd ..
```

## 🏃 Running the Application

### Option 1: Using Batch Files (Windows - Easiest)

We've created convenient batch files to start both servers:

**Start the Frontend:**
```bash
start_frontend.bat
```

**Start the Backend:**
```bash
start_backend.bat
```

### Option 2: Manual Start

#### Terminal 1 - Start the Backend:

```bash
cd Rung
venv\Scripts\activate
cd backend\voicedraft
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

#### Terminal 2 - Start the Frontend:

```bash
cd Rung\frontend
npm run dev
```

## 🌐 Accessing the Application

Once both servers are running:

- **Frontend**: Open your browser to [http://localhost:5173](http://localhost:5173)
- **Backend API**: Available at [http://localhost:8000](http://localhost:8000)
- **API Documentation**: Visit [http://localhost:8000/docs](http://localhost:8000/docs) for interactive API docs

## 📁 Project Structure

```
Rung/
├── backend/
│   ├── voicedraft/          # Main backend application
│   │   ├── main.py          # FastAPI application
│   │   ├── requirements.txt # Python dependencies
│   │   ├── inputs/          # Input templates and samples
│   │   └── outputs/         # Generated cover letters
│   └── ghostmirror/         # Additional backend features
├── frontend/
│   ├── src/
│   │   ├── components/      # React components
│   │   ├── styles/          # CSS stylesheets
│   │   ├── firebase.ts      # Firebase configuration
│   │   └── App.tsx          # Main application component
│   └── package.json         # Node.js dependencies
├── venv/                    # Python virtual environment (created during setup)
├── start_frontend.bat       # Windows batch file to start frontend
└── start_backend.bat        # Windows batch file to start backend
```

## 🔧 Technologies Used

### Backend
- **FastAPI**: Modern web framework for building APIs
- **Uvicorn**: ASGI server
- **Google Generative AI**: AI-powered content generation
- **NLTK**: Natural language processing
- **Python-dotenv**: Environment variable management

### Frontend
- **React**: UI library
- **TypeScript**: Type-safe JavaScript
- **Vite**: Fast build tool
- **Firebase**: Authentication and database
- **jsPDF**: PDF generation

## 🐛 Troubleshooting

### Frontend not displaying
- Clear your browser cache (Ctrl+Shift+Delete)
- Check browser console for errors (F12 → Console tab)
- Ensure port 5173 is not being used by another application

### Backend errors
- Make sure your Google API key is set in the `.env` file
- Verify the virtual environment is activated
- Check that all dependencies are installed: `pip list`

### Port conflicts
- If port 8000 or 5173 is already in use, you can change them:
  - Backend: Modify the port in `start_backend.bat` or the uvicorn command
  - Frontend: Vite will automatically try the next available port

### Python version warning
- The app works with Python 3.10, but you may see a warning about upgrading
- This is just a future compatibility notice and won't affect functionality

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 📧 Support

If you encounter any issues or have questions, please open an issue on GitHub.
