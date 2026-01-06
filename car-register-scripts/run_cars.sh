#!/usr/bin/env bash

LOG_DIR="/home/raspberrymax/logs"
LOG_FILE="$LOG_DIR/car_registration.log"

mkdir -p "$LOG_DIR"

{
  echo "========================================"
  echo "Run started: $(date)"
  echo "========================================"

  cd /home/raspberrymax/Car-Registration-Pi/car-register-scripts
  source ../../venv/bin/activate

  python main.py karim
  sleep 15

  python main.py matt
  sleep 15

  python main.py tatiana_altima
  sleep 15

  python main.py tatiana_odyssey

  echo "Run finished: $(date)"
  echo
} >> "$LOG_FILE" 2>&1
