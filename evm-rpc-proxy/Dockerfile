FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8545

ENTRYPOINT ["python3", "evm_rpc_proxy.py"]
