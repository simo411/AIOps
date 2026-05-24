FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy the memory leak script
COPY src/memory_leak.py .

# Make it executable
RUN chmod +x memory_leak.py

# Run the memory leak simulator
CMD ["python3", "memory_leak.py"]
