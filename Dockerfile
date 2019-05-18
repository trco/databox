FROM python:3.6.8-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set working directory
WORKDIR /databox

# Install dependencies
RUN pip install pipenv
COPY Pipfile Pipfile.lock /databox/
RUN pipenv install --system

# Copy project
COPY . /databox/
