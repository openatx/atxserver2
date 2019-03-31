FROM python:3.6

ADD . /app
WORKDIR /app

RUN pip install -r requirements.txt
RUN pip install -r requirements-dev.txt

ENTRYPOINT [ "scripts/wait-for-db.sh" ]
CMD ["python", "main.py"]
