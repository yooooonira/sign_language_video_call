import jwt
from django.conf import settings


def verify_supabase_jwt(token):
    try:
        decoded = jwt.decode(
            token,
            settings.SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            options={"verify_aud": False},
            leeway=10
        )
        nickname = decoded.get("user_metadata").get('user_name')
        if nickname==None:
          nickname = decoded.get('sub')

        return {
            "nickname":nickname,
            "email": decoded.get("email"),
        }
    except jwt.PyJWTError as e:
        print(e)
        return None
