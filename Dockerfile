# syntax=docker/dockerfile:1

ARG PYTHON_VERSION=3.12.15

FROM python:${PYTHON_VERSION}-slim

LABEL fly_launch_runtime="flask"

WORKDIR /code

COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt

COPY . .

EXPOSE 8080

# Use gunicorn (production WSGI server). app:app = the Flask instance named
# `app` in app.py. One worker with a generous timeout since GIF combining is
# CPU/memory heavy and can take a while.
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "1", "--timeout", "120", "app:app"]
