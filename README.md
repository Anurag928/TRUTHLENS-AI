# Deepfake Detection System

A Flask-based web application for detecting deepfake videos using deep learning.

## Features

- User authentication (login/signup)
- Video upload and analysis
- Deepfake detection using trained PyTorch model
- Results tracking and statistics
- User profile management

## Setup Instructions

### 1. Clone the Repository

```bash
git clone https://github.com/Ashutosh3678/Deepfake-Detection.git
cd Deepfake-Detection
```

### 2. Create Virtual Environment

```bash
python -m venv venv
```

Activate the virtual environment:
- **Windows**: `venv\Scripts\activate`
- **Linux/Mac**: `source venv/bin/activate`

### 3. Install Dependencies

```bash
pip install -r requirement.txt
```

### 4. Configure Environment Variables

Create a `.env` file in the project root directory:

```bash
SECRET_KEY=your-secure-secret-key-here
```

**Important**: 
- The `.env` file contains sensitive information and should NEVER be committed to version control
- Generate a secure secret key using Python:
  ```python
  python -c "import secrets; print(secrets.token_hex(32))"
  ```
- Copy the generated key and paste it in your `.env` file

### 5. Run the Application

```bash
python app.py
```

The application will be available at `http://127.0.0.1:5000`

## Deployment on Render 🚀

### Step-by-Step Guide

1. **Push your code to GitHub** (make sure `.env` is NOT committed)

2. **Go to [Render Dashboard](https://dashboard.render.com/)**

3. **Create a New Web Service**
   - Click "New +" → "Web Service"
   - Connect your GitHub repository
   - Select the `Deepfake-Detection` repository

4. **Configure the Web Service**
   - **Name**: `deepfake-detection` (or your preferred name)
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirement.txt`
   - **Start Command**: `gunicorn app:app`
   - **Instance Type**: Choose based on your needs (Free tier available but limited)

5. **Set Environment Variables**
   - In the Render dashboard, go to "Environment" tab
   - Click "Add Environment Variable"
   - Add the following:
     - **Key**: `SECRET_KEY`
     - **Value**: Generate using `python -c "import secrets; print(secrets.token_hex(32))"`
     - Click "Add"

6. **Deploy**
   - Click "Create Web Service"
   - Render will automatically build and deploy your app
   - Monitor the build logs for any errors

### ⚠️ Important Render Considerations

**Model File Size**:
- Your PyTorch model (`Model 97 Accuracy 100 Frames FF Data.pt`) may be large
- If it's over 100MB, you may need Git LFS or to host it externally (AWS S3, etc.)

**Free Tier Limitations**:
- Services spin down after 15 minutes of inactivity
- 512MB RAM - may not be sufficient for PyTorch models
- First request after inactivity takes 30+ seconds
- **Recommendation**: Use at least the Starter tier ($7/month) with 512MB+ RAM

**Database**:
- SQLite is ephemeral (resets on each deploy)
- For production, migrate to PostgreSQL (Render offers free PostgreSQL)

**Files Storage**:
- Uploaded videos are ephemeral (lost on restart/redeploy)
- For production, use cloud storage (AWS S3, Cloudinary, etc.)

### Checking Your Deployment

After deployment completes:
- Your app will be live at: `https://your-app-name.onrender.com`
- Check the logs in Render dashboard for any errors
- Test the upload and detection functionality

## Deployment Instructions

### Setting SECRET_KEY on Different Platforms

The application requires a `SECRET_KEY` environment variable for security. Here's how to set it on various platforms:

#### **Vercel**

1. Go to your project settings on Vercel dashboard
2. Navigate to "Environment Variables"
3. Add a new variable:
   - **Key**: `SECRET_KEY`
   - **Value**: Your generated secret key
4. Redeploy your application

#### **Render**

1. Go to your web service dashboard on Render
2. Navigate to "Environment" tab
3. Add a new environment variable:
   - **Key**: `SECRET_KEY`
   - **Value**: Your generated secret key
4. Save changes (Render will automatically redeploy)

#### **Heroku**

```bash
heroku config:set SECRET_KEY=your-generated-secret-key
```

Or via Heroku dashboard:
1. Go to your app settings
2. Click "Reveal Config Vars"
3. Add `SECRET_KEY` with your generated value

#### **Railway**

1. Go to your project on Railway
2. Navigate to "Variables" tab
3. Add a new variable:
   - **Key**: `SECRET_KEY`
   - **Value**: Your generated secret key

#### **DigitalOcean App Platform**

1. Go to your app settings
2. Navigate to "App-Level Environment Variables"
3. Add `SECRET_KEY` with your generated value

#### **AWS (Elastic Beanstalk, EC2, etc.)**

For Elastic Beanstalk:
```bash
eb setenv SECRET_KEY=your-generated-secret-key
```

For EC2 or other AWS services, set it in your deployment configuration or directly on the server.

### General Deployment Checklist

- [ ] Generate a strong SECRET_KEY using `secrets.token_hex(32)`
- [ ] Set SECRET_KEY as environment variable on your hosting platform
- [ ] Ensure `.env` file is in `.gitignore` (already configured)
- [ ] Update database configuration for production if needed
- [ ] Configure upload folder permissions
- [ ] Set `debug=False` for production
- [ ] Configure proper CORS settings if needed
- [ ] Set up HTTPS/SSL certificates

## Project Structure

```
.
├── app.py                 # Main Flask application
├── model.py              # PyTorch model definition
├── requirement.txt       # Python dependencies
├── .env                  # Environment variables (not in repo)
├── .gitignore           # Git ignore rules
├── models/              # Trained model files
├── static/              # CSS, JS, and uploaded files
├── templates/           # HTML templates
└── uploaded_videos/     # User uploaded videos
```

## Security Notes

- **Never commit** `.env` file to version control
- **Always use** environment variables for sensitive data
- **Generate unique** SECRET_KEY for each environment (dev, staging, production)
- **Rotate keys** periodically for enhanced security
- Keep dependencies updated to patch security vulnerabilities

## Model Information

The application uses a pre-trained PyTorch model located in `models/Model 97 Accuracy 100 Frames FF Data.pt`.

## License

This project is licensed under the MIT License.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Support

For issues and questions, please open an issue on GitHub.
