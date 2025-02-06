FROM python:3.10

WORKDIR /usr/src/app

COPY requirements.txt .

#no cache dir handig?
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

# Expose the port that the app will run on
EXPOSE 80

# Use gunicorn as the production WSGI server with 2 workers and 4 threads
ENTRYPOINT ["gunicorn", "--bind", "0.0.0.0:80", "--workers", "2", "--threads", "4", "app:app"]