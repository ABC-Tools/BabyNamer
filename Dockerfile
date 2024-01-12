FROM python:3.8
LABEL maintainer="tansan78@gmail.com"
COPY . /app
WORKDIR /app
RUN pip install -r requirements.txt
COPY worker/supervisord.conf /etc/supervisord.conf
EXPOSE 8080
RUN chmod +x ./gunicorn.sh
ENTRYPOINT ["sh", "gunicorn.sh"]
