# Use the official lightweight Python image.
# https://hub.docker.com/_/python
FROM python:3.10-slim

# Allow statements and log messages to immediately appear in the Knative logs
ENV PYTHONUNBUFFERED True

COPY requirements.txt /requirements.txt

# Install production dependencies.
RUN pip install --no-cache-dir -r /requirements.txt

COPY . /ekiden

RUN pip install --no-cache-dir /ekiden && rm -r /ekiden
# Run the web service on container startup. Here we use the gunicorn
# webserver, with one worker process and 8 threads.
# For environments with multiple CPU cores, increase the number of workers
# to be equal to the cores available.
# Timeout is set to 0 to disable the timeouts of the workers to allow Cloud Run to handle instance scaling.
CMD exec gunicorn ekiden.main:app --workers 1 --threads 8 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT