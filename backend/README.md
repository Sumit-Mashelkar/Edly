# Backend database foundation

Run the migration and deterministic seed import from `backend/`:

```bash
alembic upgrade head
python -m app.db.seed
```

The importer uses `seed/seed_shows.json`, preserves source episode IDs,
language variants, content groups, statuses, Season 0, and declared artwork
availability. It is safe to run repeatedly.

Show status is derived from its episodes because the source data has episode
statuses only: a show is `published` when any source episode is published,
otherwise it is `draft`.

## Authentication

The backend supports `editor` and `admin` roles. Run the seed command to create
the development users `editor@example.com` and `admin@example.com`; both use
the `DEV_PASSWORD` value, which defaults to `peblo-dev-password` locally.
Replace it and `JWT_SECRET` outside local development.

Login with `POST /auth/login` using JSON credentials, then send the returned
token as `Authorization: Bearer <token>`. `/auth/me` requires authentication;
admin-only operations use the reusable server-side admin dependency.
