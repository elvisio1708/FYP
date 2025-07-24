# AI-Powered Fitness & Boxing Training Plan Web App

This project is a full-stack web application that utilizes artificial intelligence to generate personalized fitness and boxing training plans. Built as part of my final year project at Technological University of the Shannon, the app combines machine learning with a responsive web interface to provide users with tailored workout routines based on their goals and fitness levels.

## 🔧 Technologies Used

- **Frontend:** HTML, CSS, JavaScript  
- **Backend:** Python (Flask)  
- **AI/ML:** pandas, scikit-learn  
- **Database:** CSV-based (no SQL backend used)  
- **Version Control:** Git

## 💡 Key Features

- User authentication and profile-based training plan generation  
- AI-generated daily workouts based on fitness goals  
- Clean, responsive interface built with HTML/CSS and JavaScript  
- Feedback loop integration for plan refinement  
- Modular code structure for easy maintenance

## ⚙️ Installation & Setup

### Prerequisites

- Python 3.x  
- pip  
- Flask  
- pandas  
- scikit-learn  
- Jinja2 (for templates)

### Setup Instructions

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/ai-fitness-app.git
   cd ai-fitness-app
   
2. **Create and activate a virtual environment**
    python -m venv venv
    source venv/bin/activate     # On Windows: venv\Scripts\activate

3. **Install required packages**
    pip install -r requirements.txt

4. **Run the Flask app**
    python app.py

5. **Open the app in your browser**
    http://127.0.0.1:5000/


Note: Ensure all dataset files (CSV) and model files are correctly placed inside the /data/ and /models/ directories.

## 🚧 Current Status

The app is functional in parts and runs locally, but it is not fully working as intended. It remains a valuable proof of concept demonstrating full-stack integration with AI features. Planned improvements include:

- Full bug fixing and feature completion  
- Cloud deployment (Heroku/AWS)  
- Frontend overhaul using a modern framework like Vue or React  
- Expanded training dataset for improved ML accuracy

## 👤 Author

**Elvis Haziri**  
📧 elvisihaziri@gmail.com  
    [LinkedIn Profile](https://www.linkedin.com/in/elvis-haziri-095b34251)
