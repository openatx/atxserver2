FROM python:3.6

ADD . /app
WORKDIR /app

RUN pip install -r requirements.txt

ENTRYPOINT [ "bash", "scripts/wait-for-db.sh" ]
CMD ["python", "-u", "main.py"]
