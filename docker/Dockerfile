# For more information, please refer to https://aka.ms/vscode-docker-python
FROM python:latest

# Keeps Python from generating .pyc files in the container
ENV PYTHONDONTWRITEBYTECODE=1

# Turns off buffering for easier container logging
ENV PYTHONUNBUFFERED=1

# Set current directory as ENV
ENV PATH=/app:$PATH

# Needed for tzdata
ARG DEBIAN_FRONTEND=noninteractive
ENV TZ=America/Los_Angeles

# install dependencies
RUN apt update
RUN apt install -y iproute2
RUN apt install -y bc
# copy items
WORKDIR /app
COPY training_profile.sh ./
COPY docker-script.sh ./
COPY receiver.py ./

# start receiver
CMD ["./docker-script.sh"]