FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt update && apt install -y \
    python3 \
    python3-pip \
    python3-venv \
    build-essential

WORKDIR /app

# Copy only what's needed to install (for caching)
COPY setup.py requirements.txt ./
COPY src/ ./src/

RUN pip install -e .

# No command! So container just sleeps (does nothing on startup)
CMD [ "sleep", "infinity" ]