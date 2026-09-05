import os


JWT_SECRET = os.getenv(
	"JWT_SECRET",
	"local-development-only-secret-replace-in-production-32chars",
)
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
DEV_PASSWORD = os.getenv("DEV_PASSWORD", "peblo-dev-password")
