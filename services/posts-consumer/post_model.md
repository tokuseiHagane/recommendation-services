Модель сущности пост представленная в виде sql:
```sql
CREATE TABLE public.posts (
	id int4 NOT NULL,
	content text,
	repost_count int4,
	view_count int4,
	link jsonb,
	message_timestamp timestamp,
	has_reactions boolean,
	id_channels int4,
	free_reactions_count int4,
	paid_reactions_count int4,
	CONSTRAINT posts_pk PRIMARY KEY (id)
);
```