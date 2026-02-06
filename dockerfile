# Use a stable Python image that doesn't require additional apt dependencies
FROM python:3.9-buster

# Set working directory
WORKDIR /tenderai

# Copy requirements.txt first for better cache usage
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire application
COPY . .

# Make directories that the app expects to exist
RUN mkdir -p data/md data/indices output mlruns static

# Create a non-root user and give them ownership of the app directory
RUN useradd -m appuser && chown -R appuser:appuser /tenderai
USER appuser

# Expose the port that Streamlit will run on
EXPOSE 8501

# Command to run the application
CMD ["streamlit", "run", "home.py", "--server.port=8501", "--server.address=0.0.0.0"]