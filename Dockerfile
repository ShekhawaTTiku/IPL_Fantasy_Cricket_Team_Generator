FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Copy requirements file and install dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

RUN apt-get update && apt-get install -y libgomp1

# Copy the script directory and main.py
COPY ./scripts/ /app/scripts/
COPY main.py /app/
COPY .env /app/
COPY ./model/ /app/model/
COPY ./Output/ /app/Output/

ENTRYPOINT [ "python", "main.py" ]
