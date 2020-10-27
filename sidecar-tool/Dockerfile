FROM python

WORKDIR /src

ADD requirements.txt /src

RUN pip install --no-cache-dir -r requirements.txt

ADD ./src/*.py /src/

CMD ["python", "-u", "init.py"]