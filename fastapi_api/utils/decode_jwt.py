import jwt
import os
import logging
from typing import Optional, Dict

log = logging.getLogger(__name__)

def verify_supabase_jwt(token: str) -> Optional[Dict[str, str]]:
    """Supabase JWT 토큰을 검증하고 사용자 정보를 반환"""
    try:
        secret = os.getenv("SUPABASE_JWT_SECRET") or os.getenv("AI_WS_TOKEN")
        
        if not secret:
            log.error("SUPABASE_JWT_SECRET not found in environment variables")
            return None
            
        decoded = jwt.decode(
            token,
            secret,
            algorithms=["HS256"],
            options={"verify_aud": False},
            leeway=10
        )
        
        user_metadata = decoded.get("user_metadata", {})
        nickname = user_metadata.get('user_name') if user_metadata else None
        
        if nickname is None:
            nickname = decoded.get('sub')

        return {
            "nickname": nickname,
            "email": decoded.get("email"),
            "user_id": decoded.get("sub"),
        }
    except jwt.PyJWTError as e:
        log.warning(f"JWT validation failed: {e}")
        return None
    except Exception as e:
        log.error(f"Unexpected error in JWT validation: {e}")
        return None