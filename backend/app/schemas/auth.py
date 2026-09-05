from typing import List
from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=3, description="Username atau email akun pengguna")
    password: str = Field(..., min_length=4, description="Kata sandi akun")


class UserResponse(BaseModel):
    id: str = Field(..., description="ID unik pengguna")
    username: str = Field(..., description="Username pengguna")
    full_name: str = Field(..., description="Nama lengkap pengguna")
    role: str = Field(default="user", description="Peran pengguna (e.g. admin, analyst, viewer)")
    permissions: List[str] = Field(default=[], description="Daftar hak akses pengguna")


class TokenResponse(BaseModel):
    access_token: str = Field(..., description="JWT Bearer token untuk autentikasi API")
    token_type: str = Field(default="bearer", description="Tipe token")
    expires_in: int = Field(..., description="Masa berlaku token dalam detik")
    user: UserResponse = Field(..., description="Informasi profil pengguna terotentikasi")
