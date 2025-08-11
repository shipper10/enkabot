
Genshin Telegram Bot - Postgres + Local EnkaCard
================================================

This package includes a Telegram bot which:
- Stores users and wishes in PostgreSQL
- Generates EnkaCard images locally (requires system libs installed in Dockerfile)
- Provides /bind, /profile, /abyss, /wish, /wishlog, /characters (3x4 paginated)

Environment variables (set as Koyeb secrets):
- BOT_TOKEN (required)
- DATABASE_URL (required)  e.g. postgresql://user:pass@host:5432/dbname
- HOYOLAB_COOKIE (optional)
- PORT (optional, default 8080)

Notes:
- enkacard local generation depends on the enkacard library API; in case of API mismatches,
  you may need to adapt the generate_character_card_image/generate_profile_card_image functions.
- The Dockerfile installs fonts (Noto) and Cairo/Pango dependencies so cards render correctly.
- For production, use a managed Postgres (Koyeb DB, Supabase, Neon).
