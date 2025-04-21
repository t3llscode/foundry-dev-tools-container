# Use the official Python image as a base
FROM python:3.13-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install the dependencies
RUN pip install --no-cache-dir --upgrade -r requirements.txt

# Copy the FastAPI application code into the container
COPY ./t3_code ./t3_code
COPY ./datasets ./datasets
COPY ./.vscode-server /root/.vscode-server

# Don't expose the port the app runs on, because we use the names of the containers to communicate
# EXPOSE 8000

# Command to run the FastAPI application (uses Uvicorn internally)
CMD ["python", "t3_code/main.py"]
