FROM python:3.12-slim

WORKDIR /app

# Copy application files
COPY . /app

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose the application port 8080 8051
EXPOSE 8080 8051

RUN python /app/deployment.py

# Set the correct command to run the Streamlit app
CMD ["streamlit", "run", "main.py", "--server.port=8080", "--server.address=0.0.0.0"]