from datetime import datetime, timedelta
from typing import Optional, Union
from jose import JWTError, jwt
import bcrypt
import os

# ---------------------------------------------------------------------------
# JWT 配置
# ---------------------------------------------------------------------------
# SECRET_KEY 是 MathRob 后端自己用于签发 / 校验登录 JWT 的对称密钥，
# 属于系统内部凭证，并非第三方服务（Gemini / S3 / DB）的密钥。
#
# 作用链路：
#   1. 用户登录成功 -> jwt.encode(..., SECRET_KEY) 签发 token
#   2. 后续请求携带 token -> jwt.decode(token, SECRET_KEY) 校验签名
#
# 部署说明：
#   - 生产环境应通过环境变量 SECRET_KEY 覆盖此默认值，避免源码泄漏后被伪造 token。
#   - 当前默认值仅用于内网/开发环境（系统部署在局域网，外网不可达）。
#   - 若需要对外暴露，请务必在 .env 中设置随机且足够长的 SECRET_KEY。
# ---------------------------------------------------------------------------
SECRET_KEY = os.getenv("SECRET_KEY", "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7")
ALGORITHM = "HS256"  # JWT 签名算法
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # Token 有效期：24 小时

class AuthService:
    def verify_password(self, plain_password, hashed_password):
        # bcrypt.checkpw requires bytes
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

    def get_password_hash(self, password):
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None):
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=15)
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt

    def decode_token(self, token: str):
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            username: str = payload.get("sub")
            if username is None:
                return None
            return username
        except JWTError:
            return None

auth_service = AuthService()
