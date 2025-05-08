FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Copy requirements file and install dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

RUN apt-get update && apt-get install -y libgomp1

# Install python-dotenv to handle .env files
RUN pip install --no-cache-dir python-dotenv

# Copy the script directory and main.py
COPY ./scripts/ /app/scripts/
COPY main.py /app/

COPY ./model/ /app/model/

# Copy only the .env file from cricket-ipl-api
COPY ./cricket-ipl-api/.env /app/cricket-ipl-api/.env

ENTRYPOINT [ "python", "main.py" ]
# Run the main script when the container launches
CMD ["--match", "1"]