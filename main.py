

from fastapi import FastAPI, HTTPException, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import torch
import torch.nn as nn
from efficientnet_pytorch import EfficientNet
from PIL import Image
import io
from torchvision import transforms

# Initialize FastAPI app
app = FastAPI(
    title="Setu Backend API",
    description="API for Setu - Nepali Sign Language Translation Platform",
    version="1.0.0"
)

# CORS middleware to allow frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load the trained model
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
model = EfficientNet.from_name('efficientnet-b0')
model._fc = nn.Linear(model._fc.in_features, 4)  # 4 classes: Dhanyabaad, Ghar, Ma, Namaskaar
model_path = r"C:\Users\diwas\Desktop\Setu\snl.pth"
model.load_state_dict(torch.load(model_path, map_location=device))
model = model.to(device)
model.eval()

# Class names for prediction
class_names = ['Dhanyabaad', 'Ghar', 'Ma', 'Namaskaar']

# Image transformation pipeline (matching the training transforms)
transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
])

# In-memory data for /about endpoint (no database used)
ABOUT_DATA = {
    "title": "About Setu",
    "mission_statement": "At Setu, our mission is to bridge communication gaps through Nepali Sign Language translation. We believe everyone deserves equal access to understanding and expression, without the barriers of language or communication challenges.",
    "team": [
        {"name": "Rojin Baniya", "role": "Machine Learning", "description": "Designs and develops machine learning models, trains and evaluates algorithms, and applies them to solve real-world problems.", "linkedin": "https://linkedin.com/in/rojin-baniya", "github": "https://github.com/rojin-baniya"},
        {"name": "Aaryan Sharma", "role": "MLOps", "description": "Builds and manages machine learning pipelines, model deployment, monitoring, and infrastructure automation.", "linkedin": "https://linkedin.com/in/aaryan-sharma", "github": "https://github.com/aaryan-sharma"},
        {"name": "Prakriti Devkota", "role": "Frontend Developer", "description": "Creates dynamic, responsive, and user-friendly interfaces.", "linkedin": "https://linkedin.com/in/prakriti-devkota", "github": "https://github.com/prakriti-devkota"},
        {"name": "Rejina Budhathoki", "role": "Backend Developer", "description": "Builds and manages APIs, server-side logic, and database operations.", "linkedin": "https://linkedin.com/in/rejina-budhathoki", "github": "https://github.com/rejina-budhathoki"}
    ]
}

# Pydantic model for contact form (data is logged to console, no storage)
class ContactForm(BaseModel):
    name: str
    email: str
    subject: str
    message: str

# Root endpoint for health check
@app.get("/")
async def root():
    return {"message": "Setu Backend API is running!"}

# About endpoint (returns in-memory data)
@app.get("/about")
async def get_about():
    return ABOUT_DATA

# Contact form submission endpoint (logs to console)
@app.post("/contact")
async def submit_contact(form: ContactForm):
    print(f"Received contact form submission: {form.dict()}")
    return {"status": "success", "message": "Your message has been received. We'll get back to you soon!"}

# Transcription endpoint for NSL prediction (processes image and returns prediction)
@app.post("/transcribe")
async def transcribe(file: UploadFile = File(...)):
    try:
        # Read the uploaded image
        contents = await file.read()
        image = Image.open(io.BytesIO(contents)).convert('RGB')

        # Apply transformations
        input_tensor = transform(image).unsqueeze(0).to(device)

        # Make prediction
        with torch.no_grad():
            outputs = model(input_tensor)
            _, predicted = torch.max(outputs, 1)
            pred_class = class_names[predicted.item()]

        return {"status": "success", "predicted_class": pred_class}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing image: {str(e)}")

# Error handling
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return {"error": str(exc.detail)}

# Run the server if executed directly
if __name__ == "__main__":
    uvicorn.run(app, host="localhost", port=8000)