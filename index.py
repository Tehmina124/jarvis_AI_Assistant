from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI(title="JARVIS AI Assistant")

@app.get("/", response_class=HTMLResponse)
def home():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>JARVIS AI Assistant</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {
                font-family: Arial, sans-serif;
                background: linear-gradient(135deg, #10102e, #352064);
                color: white;
                text-align: center;
                padding: 60px 20px;
            }
            .card {
                max-width: 600px;
                margin: auto;
                padding: 30px;
                border-radius: 20px;
                background: #211b45;
            }
            h1 { color: #80eaff; }
            p { line-height: 1.8; }
        </style>
    </head>
    <body>
        <div class="card">
            <h1>JARVIS AI Assistant</h1>
            <h2>Welcome, Tehmina!</h2>
            <p>Your AI assistant website is running.</p>
            <p>AI Chat | Calculator | Study Assistant</p>
            <p>Coding Assistant | PDF Assistant | Notes & Tasks</p>
            <p>Next step: Connect the AI features to this website.</p>
        </div>
    </body>
    </html>
  
