
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
                margin: 0;
                padding: 40px 20px;
                font-family: Arial, sans-serif;
                background: linear-gradient(135deg, #10102e, #352064);
                color: white;
                text-align: center;
            }
            .card {
                max-width: 650px;
                margin: 50px auto;
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
            <h1>🤖 JARVIS AI Assistant</h1>
            <h2>Welcome, Tehmina!</h2>
            <p>Your AI assistant website is running.</p>
            <p>AI Chat • Calculator • Study Assistant</p>
            <p>Coding Assistant • PDF Assistant</p>
            <p>Notes • Tasks • Email Writer</p>
        </div>
    </body>
    </html>
    
