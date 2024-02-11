FROM python:3.8
LABEL maintainer="tansan78@gmail.com"
ENV TZ="America/Los_Angeles"
COPY ./app /app/app/
COPY ./worker /app/worker/
COPY ./requirements.txt /app/requirements.txt
COPY ./gunicorn.sh /app/gunicorn.sh
WORKDIR /app
RUN pip install -r requirements.txt
COPY worker/supervisord.conf /etc/supervisord.conf
EXPOSE 8080
RUN chmod +x ./gunicorn.sh
ENTRYPOINT ["sh", "gunicorn.sh"]
