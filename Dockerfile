# Use the official Python slim image
FROM python:3-slim

# Update package lists
RUN apt-get update

# Install nodejs, npm, and Graphviz
RUN apt-get install -y nodejs npm graphviz

# Copy the application files into the LogPPL directory in the container
COPY . /LogPPL

# Install webppl globally
RUN npm install -g webppl

# Upgrade pip and install requirements from requirements.txt
RUN python -m pip install --upgrade pip
RUN pip install --upgrade -r /LogPPL/requirements.txt

# Set the working directory to LogPPL
WORKDIR /LogPPL

# Expose the port your Flask app runs on
EXPOSE 5000

# Command to run the Flask app
CMD ["python", "app.py"]
