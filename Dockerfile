# Use an official Python base image
FROM python:3.12-slim

# Set the working directory inside the container
WORKDIR /app

# Copy all the files to the working directory
COPY . .
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt -e .

# Expose the port your app runs on (optional, for web apps)
EXPOSE 5001

# Define the command to run your app
CMD ["python", "/app/api/run.py"]
