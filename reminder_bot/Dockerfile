FROM python:3

WORKDIR /app

ENV PYTHONUNBUFFERED=1

COPY requirements.txt requirements.txt

RUN pip install -r requirements.txt

COPY app.py app.py
COPY model.py model.py

RUN mkdir data

CMD python app.py