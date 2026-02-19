FROM python:3.13-slim

RUN mkdir -p /usr/src/app
WORKDIR /usr/src/app

COPY requirements.txt /usr/src/app/

RUN pip3 install --no-cache-dir -r requirements.txt

COPY . /usr/src/app

EXPOSE 8080

# Disable Python output buffering for real-time logs
ENV PYTHONUNBUFFERED=1

ENTRYPOINT ["python3"]

CMD ["-m", "preprocessor"]