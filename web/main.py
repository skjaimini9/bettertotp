import os
import time

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from btotp.core import generate_code_at, verify_code, DEFAULT_CODE_LENGTH, DEFAULT_HASH_ALGO, DEFAULT_TIME_STEP
from btotp.secret import generate_secret, secret_to_b32, secret_to_hex
from btotp.uri import generate_uri

from .schemas import (
    EnrollRequest,
    EnrollResponse,
    VerifyRequest,
    VerifyResponse,
    GenerateCodeRequest,
    GenerateCodeResponse,
    HealthResponse,
)

app = FastAPI(
    title="BetterTOTP API",
    description="TOTP enrollment and verification service (non-standard algorithm: SHA-512, 75-char alphabet, 45s step)",
    version="1.0.0",
)

# CORS — configure via environment variable
origins_str = os.environ.get("CORS_ORIGINS", "*")
origins = [o.strip() for o in origins_str.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health", response_model=HealthResponse)
def health():
    return HealthResponse(status="ok")


@app.post("/api/enroll", response_model=EnrollResponse, status_code=201)
def enroll(req: EnrollRequest):
    secret = generate_secret()
    secret_hex = secret_to_hex(secret)
    secret_b32 = secret_to_b32(secret)
    uri = generate_uri(
        account=req.account,
        secret_hex=secret_hex,
        issuer=req.issuer,
        algorithm=DEFAULT_HASH_ALGO,
        digits=DEFAULT_CODE_LENGTH,
        period=DEFAULT_TIME_STEP,
    )
    return EnrollResponse(
        secret_hex=secret_hex,
        secret_b32=secret_b32,
        uri=uri,
    )


@app.post("/api/verify", response_model=VerifyResponse)
def verify(req: VerifyRequest):
    try:
        key_bytes = bytes.fromhex(req.secret_hex)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid hex secret")

    valid = verify_code(
        key_bytes,
        req.code,
        window=req.window,
        algorithm=DEFAULT_HASH_ALGO,
        code_length=DEFAULT_CODE_LENGTH,
        time_step=DEFAULT_TIME_STEP,
    )
    return VerifyResponse(valid=valid)


@app.post("/api/generate-code", response_model=GenerateCodeResponse)
def generate_current_code(req: GenerateCodeRequest):
    try:
        key_bytes = bytes.fromhex(req.secret_hex)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid hex secret")

    now = int(time.time())
    code = generate_code_at(
        key_bytes,
        now,
        algorithm=DEFAULT_HASH_ALGO,
        code_length=DEFAULT_CODE_LENGTH,
        time_step=DEFAULT_TIME_STEP,
    )
    expires_in = DEFAULT_TIME_STEP - (now % DEFAULT_TIME_STEP)
    return GenerateCodeResponse(code=code, expires_in=expires_in)
