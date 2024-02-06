FROM python:3.8.12-slim-buster

WORKDIR /root/RobotCop

# Install 'git'
RUN apt-get update && apt-get install -y git

# Install other dependencies from requirements.txt
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN apt-get update && apt-get install -y ffmpeg && apt-get clean && rm -rf /var/lib/apt/lists/*

CMD [ "python3", "./main.py" ]