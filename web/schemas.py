from pydantic import BaseModel, Field


class EnrollRequest(BaseModel):
    account: str = Field(
        ..., min_length=1, description="Username or email for the TOTP account"
    )
    issuer: str = Field(
        default="", description="Service/application name (e.g. 'MyApp')"
    )


class EnrollResponse(BaseModel):
    secret_hex: str = Field(description="Secret key as hex string (store this in your DB)")
    secret_b32: str = Field(description="Secret key as base32 string")
    uri: str = Field(description="otpauth://totp/ URI for QR code generation")


class VerifyRequest(BaseModel):
    secret_hex: str = Field(
        ..., min_length=1, description="Secret key (hex) stored during enrollment"
    )
    code: str = Field(
        ..., min_length=1, description="TOTP code submitted by the user"
    )
    window: int = Field(
        default=1, ge=0, le=10,
        description="Time drift window (±steps). Default 1 = ±45s"
    )


class VerifyResponse(BaseModel):
    valid: bool = Field(description="True if the code is valid within the window")


class GenerateCodeRequest(BaseModel):
    secret_hex: str = Field(
        ..., min_length=1, description="Secret key (hex)"
    )


class GenerateCodeResponse(BaseModel):
    code: str = Field(description="Current TOTP code")
    expires_in: int = Field(description="Seconds until the code changes")


class HealthResponse(BaseModel):
    status: str = Field(default="ok")
