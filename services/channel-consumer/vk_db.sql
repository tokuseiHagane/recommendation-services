-- Database generated with pgModeler (PostgreSQL Database Modeler).
-- pgModeler version: 1.1.6
-- PostgreSQL version: 17.0
-- Project Site: pgmodeler.io
-- Model Author: ---

-- Database creation must be performed outside a multi lined SQL file. 
-- These commands were put in this file only as a convenience.
-- 
-- object: vk | type: DATABASE --
-- DROP DATABASE IF EXISTS vk;
CREATE DATABASE vk
	OWNER = postgres;
-- ddl-end --


-- object: public.groups | type: TABLE --
-- DROP TABLE IF EXISTS public.groups CASCADE;
CREATE TABLE public.groups (
	id int4 NOT NULL,
	name varchar,
	screen_name varchar,
	members_count int4,
	CONSTRAINT channel_pk PRIMARY KEY (id)
);
-- ddl-end --
ALTER TABLE public.groups OWNER TO postgres;
-- ddl-end --

-- object: public.posts | type: TABLE --
-- DROP TABLE IF EXISTS public.posts CASCADE;
CREATE TABLE public.posts (
	id int4 NOT NULL,
	len_message int4,
	repost_count int4,
	view_count int4,
	comments_count int4,
	message_timestamp timestamp,
	edit_date timestamp,
	reactions_count int4,
	id_groups int4,
	CONSTRAINT posts_pk PRIMARY KEY (id)
);
-- ddl-end --
ALTER TABLE public.posts OWNER TO postgres;
-- ddl-end --

-- object: groups_fk | type: CONSTRAINT --
-- ALTER TABLE public.posts DROP CONSTRAINT IF EXISTS groups_fk CASCADE;
ALTER TABLE public.posts ADD CONSTRAINT groups_fk FOREIGN KEY (id_groups)
REFERENCES public.groups (id) MATCH FULL
ON DELETE SET NULL ON UPDATE CASCADE;
-- ddl-end --


