--
-- PostgreSQL database dump
--

\restrict eOOZ4PWrfoqJBg39mv2KFQxrwhdkPnTVEyLUQC5ojgHu4UjFeQ3miV3BbV4amIJ

-- Dumped from database version 16.14 (Debian 16.14-1.pgdg13+1)
-- Dumped by pg_dump version 16.14 (Debian 16.14-1.pgdg13+1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: audit; Type: SCHEMA; Schema: -; Owner: distribution_user
--

CREATE SCHEMA audit;


ALTER SCHEMA audit OWNER TO distribution_user;

--
-- Name: projectstatus; Type: TYPE; Schema: public; Owner: distribution_user
--

CREATE TYPE public.projectstatus AS ENUM (
    'DRAFT',
    'IN_PROGRESS',
    'COMPLETED',
    'CANCELLED'
);


ALTER TYPE public.projectstatus OWNER TO distribution_user;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: audit_runs; Type: TABLE; Schema: audit; Owner: distribution_user
--

CREATE TABLE audit.audit_runs (
    id bigint NOT NULL,
    started_at timestamp with time zone DEFAULT now() NOT NULL,
    finished_at timestamp with time zone,
    dataset_name text NOT NULL,
    total_records integer NOT NULL,
    valid_records integer DEFAULT 0,
    invalid_records integer DEFAULT 0,
    duplicate_records integer DEFAULT 0,
    report jsonb,
    created_by text DEFAULT 'system'::text
);


ALTER TABLE audit.audit_runs OWNER TO distribution_user;

--
-- Name: audit_runs_id_seq; Type: SEQUENCE; Schema: audit; Owner: distribution_user
--

CREATE SEQUENCE audit.audit_runs_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE audit.audit_runs_id_seq OWNER TO distribution_user;

--
-- Name: audit_runs_id_seq; Type: SEQUENCE OWNED BY; Schema: audit; Owner: distribution_user
--

ALTER SEQUENCE audit.audit_runs_id_seq OWNED BY audit.audit_runs.id;


--
-- Name: row_audit_results; Type: TABLE; Schema: audit; Owner: distribution_user
--

CREATE TABLE audit.row_audit_results (
    id bigint NOT NULL,
    audit_run_id bigint NOT NULL,
    store_id bigint,
    dimension character varying(50) NOT NULL,
    severity character varying(20) NOT NULL,
    issue_code character varying(100) NOT NULL,
    issue_description text,
    old_value text,
    suggested_value text,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE audit.row_audit_results OWNER TO distribution_user;

--
-- Name: row_audit_results_id_seq; Type: SEQUENCE; Schema: audit; Owner: distribution_user
--

CREATE SEQUENCE audit.row_audit_results_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE audit.row_audit_results_id_seq OWNER TO distribution_user;

--
-- Name: row_audit_results_id_seq; Type: SEQUENCE OWNED BY; Schema: audit; Owner: distribution_user
--

ALTER SEQUENCE audit.row_audit_results_id_seq OWNED BY audit.row_audit_results.id;


--
-- Name: accounts; Type: TABLE; Schema: public; Owner: distribution_user
--

CREATE TABLE public.accounts (
    mobile character varying(20) NOT NULL,
    id integer NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.accounts OWNER TO distribution_user;

--
-- Name: accounts_id_seq; Type: SEQUENCE; Schema: public; Owner: distribution_user
--

CREATE SEQUENCE public.accounts_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.accounts_id_seq OWNER TO distribution_user;

--
-- Name: accounts_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: distribution_user
--

ALTER SEQUENCE public.accounts_id_seq OWNED BY public.accounts.id;


--
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: distribution_user
--

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);


ALTER TABLE public.alembic_version OWNER TO distribution_user;

--
-- Name: companies; Type: TABLE; Schema: public; Owner: distribution_user
--

CREATE TABLE public.companies (
    account_id integer NOT NULL,
    name character varying(255) NOT NULL,
    economic_code character varying(64),
    national_id character varying(64),
    phone character varying(32),
    email character varying(255),
    address character varying(500),
    id integer NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.companies OWNER TO distribution_user;

--
-- Name: companies_id_seq; Type: SEQUENCE; Schema: public; Owner: distribution_user
--

CREATE SEQUENCE public.companies_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.companies_id_seq OWNER TO distribution_user;

--
-- Name: companies_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: distribution_user
--

ALTER SEQUENCE public.companies_id_seq OWNED BY public.companies.id;


--
-- Name: drivers; Type: TABLE; Schema: public; Owner: distribution_user
--

CREATE TABLE public.drivers (
    import_batch_id integer NOT NULL,
    driver_code character varying(50),
    first_name character varying(100),
    last_name character varying(100),
    phone character varying(50),
    license_number character varying(50),
    license_expiry date,
    experience_years integer,
    latitude numeric(10,7),
    longitude numeric(10,7),
    status character varying(30) NOT NULL,
    raw_data json,
    error_note character varying(1000),
    id integer NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.drivers OWNER TO distribution_user;

--
-- Name: drivers_id_seq; Type: SEQUENCE; Schema: public; Owner: distribution_user
--

CREATE SEQUENCE public.drivers_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.drivers_id_seq OWNER TO distribution_user;

--
-- Name: drivers_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: distribution_user
--

ALTER SEQUENCE public.drivers_id_seq OWNED BY public.drivers.id;


--
-- Name: files; Type: TABLE; Schema: public; Owner: distribution_user
--

CREATE TABLE public.files (
    entity_type character varying(50) NOT NULL,
    entity_id integer NOT NULL,
    category character varying(100) NOT NULL,
    original_name character varying(500) NOT NULL,
    stored_name character varying(255) NOT NULL,
    file_path character varying(1000) NOT NULL,
    content_type character varying(100) NOT NULL,
    file_size bigint NOT NULL,
    id integer NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    uploaded_by integer
);


ALTER TABLE public.files OWNER TO distribution_user;

--
-- Name: files_id_seq; Type: SEQUENCE; Schema: public; Owner: distribution_user
--

CREATE SEQUENCE public.files_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.files_id_seq OWNER TO distribution_user;

--
-- Name: files_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: distribution_user
--

ALTER SEQUENCE public.files_id_seq OWNED BY public.files.id;


--
-- Name: gps_records; Type: TABLE; Schema: public; Owner: distribution_user
--

CREATE TABLE public.gps_records (
    import_batch_id integer NOT NULL,
    vehicle_plate character varying(50) NOT NULL,
    latitude numeric(10,7) NOT NULL,
    longitude numeric(10,7) NOT NULL,
    "timestamp" timestamp with time zone NOT NULL,
    speed_kmh double precision,
    heading double precision,
    accuracy_m double precision,
    raw_data json,
    error_note character varying(1000),
    id integer NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.gps_records OWNER TO distribution_user;

--
-- Name: gps_records_id_seq; Type: SEQUENCE; Schema: public; Owner: distribution_user
--

CREATE SEQUENCE public.gps_records_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.gps_records_id_seq OWNER TO distribution_user;

--
-- Name: gps_records_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: distribution_user
--

ALTER SEQUENCE public.gps_records_id_seq OWNED BY public.gps_records.id;


--
-- Name: import_batches; Type: TABLE; Schema: public; Owner: distribution_user
--

CREATE TABLE public.import_batches (
    file_id integer NOT NULL,
    entity_type character varying(50) NOT NULL,
    status character varying(50) NOT NULL,
    total_rows integer NOT NULL,
    valid_rows integer NOT NULL,
    error_rows integer NOT NULL,
    imported_rows integer NOT NULL,
    error_log json,
    column_mapping json,
    started_at timestamp with time zone,
    completed_at timestamp with time zone,
    id integer NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.import_batches OWNER TO distribution_user;

--
-- Name: import_batches_id_seq; Type: SEQUENCE; Schema: public; Owner: distribution_user
--

CREATE SEQUENCE public.import_batches_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.import_batches_id_seq OWNER TO distribution_user;

--
-- Name: import_batches_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: distribution_user
--

ALTER SEQUENCE public.import_batches_id_seq OWNED BY public.import_batches.id;


--
-- Name: orders; Type: TABLE; Schema: public; Owner: distribution_user
--

CREATE TABLE public.orders (
    import_batch_id integer NOT NULL,
    order_code character varying(200) NOT NULL,
    store_code character varying(100),
    store_name character varying(500),
    address character varying(2000),
    latitude numeric(10,7),
    longitude numeric(10,7),
    weight_kg double precision,
    volume_m3 double precision,
    delivery_date timestamp with time zone,
    delivery_time_from timestamp with time zone,
    delivery_time_to timestamp with time zone,
    status character varying(30) NOT NULL,
    raw_data json,
    error_note character varying(1000),
    id integer NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.orders OWNER TO distribution_user;

--
-- Name: orders_id_seq; Type: SEQUENCE; Schema: public; Owner: distribution_user
--

CREATE SEQUENCE public.orders_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.orders_id_seq OWNER TO distribution_user;

--
-- Name: orders_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: distribution_user
--

ALTER SEQUENCE public.orders_id_seq OWNED BY public.orders.id;


--
-- Name: projects; Type: TABLE; Schema: public; Owner: distribution_user
--

CREATE TABLE public.projects (
    company_id integer NOT NULL,
    name character varying(255) NOT NULL,
    description text,
    status public.projectstatus NOT NULL,
    id integer NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.projects OWNER TO distribution_user;

--
-- Name: projects_id_seq; Type: SEQUENCE; Schema: public; Owner: distribution_user
--

CREATE SEQUENCE public.projects_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.projects_id_seq OWNER TO distribution_user;

--
-- Name: projects_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: distribution_user
--

ALTER SEQUENCE public.projects_id_seq OWNED BY public.projects.id;


--
-- Name: request_files; Type: TABLE; Schema: public; Owner: distribution_user
--

CREATE TABLE public.request_files (
    request_id integer NOT NULL,
    file_type character varying(30) NOT NULL,
    original_name character varying(255) NOT NULL,
    stored_name character varying(255) NOT NULL,
    file_path character varying(500) NOT NULL,
    content_type character varying(100),
    file_size integer NOT NULL,
    id integer NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.request_files OWNER TO distribution_user;

--
-- Name: request_files_id_seq; Type: SEQUENCE; Schema: public; Owner: distribution_user
--

CREATE SEQUENCE public.request_files_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.request_files_id_seq OWNER TO distribution_user;

--
-- Name: request_files_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: distribution_user
--

ALTER SEQUENCE public.request_files_id_seq OWNED BY public.request_files.id;


--
-- Name: requests; Type: TABLE; Schema: public; Owner: distribution_user
--

CREATE TABLE public.requests (
    company_name character varying(200) NOT NULL,
    contact_name character varying(200) NOT NULL,
    mobile character varying(30) NOT NULL,
    email character varying(200),
    industry character varying(100),
    goal text,
    status character varying(30) NOT NULL,
    id integer NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.requests OWNER TO distribution_user;

--
-- Name: requests_id_seq; Type: SEQUENCE; Schema: public; Owner: distribution_user
--

CREATE SEQUENCE public.requests_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.requests_id_seq OWNER TO distribution_user;

--
-- Name: requests_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: distribution_user
--

ALTER SEQUENCE public.requests_id_seq OWNED BY public.requests.id;


--
-- Name: stores; Type: TABLE; Schema: public; Owner: distribution_user
--

CREATE TABLE public.stores (
    import_batch_id integer NOT NULL,
    code character varying(50) NOT NULL,
    name character varying(200),
    phone character varying(50),
    address character varying(2000),
    latitude numeric(10,7),
    longitude numeric(10,7),
    category character varying(50),
    priority integer NOT NULL,
    status character varying(30) NOT NULL,
    service_time_min integer,
    raw_data json,
    error_note character varying(1000),
    id integer NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.stores OWNER TO distribution_user;

--
-- Name: stores_id_seq; Type: SEQUENCE; Schema: public; Owner: distribution_user
--

CREATE SEQUENCE public.stores_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.stores_id_seq OWNER TO distribution_user;

--
-- Name: stores_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: distribution_user
--

ALTER SEQUENCE public.stores_id_seq OWNED BY public.stores.id;


--
-- Name: vehicles; Type: TABLE; Schema: public; Owner: distribution_user
--

CREATE TABLE public.vehicles (
    import_batch_id integer NOT NULL,
    vehicle_code character varying(100) NOT NULL,
    plate_number character varying(50) NOT NULL,
    vehicle_type character varying(100),
    capacity_kg double precision,
    capacity_m3 double precision,
    cost_per_km numeric(12,2),
    fixed_cost numeric(12,2),
    latitude numeric(10,7),
    longitude numeric(10,7),
    status character varying(30) NOT NULL,
    available_from timestamp with time zone,
    available_until timestamp with time zone,
    raw_data json,
    error_note character varying(1000),
    id integer NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.vehicles OWNER TO distribution_user;

--
-- Name: vehicles_id_seq; Type: SEQUENCE; Schema: public; Owner: distribution_user
--

CREATE SEQUENCE public.vehicles_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.vehicles_id_seq OWNER TO distribution_user;

--
-- Name: vehicles_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: distribution_user
--

ALTER SEQUENCE public.vehicles_id_seq OWNED BY public.vehicles.id;


--
-- Name: audit_runs id; Type: DEFAULT; Schema: audit; Owner: distribution_user
--

ALTER TABLE ONLY audit.audit_runs ALTER COLUMN id SET DEFAULT nextval('audit.audit_runs_id_seq'::regclass);


--
-- Name: row_audit_results id; Type: DEFAULT; Schema: audit; Owner: distribution_user
--

ALTER TABLE ONLY audit.row_audit_results ALTER COLUMN id SET DEFAULT nextval('audit.row_audit_results_id_seq'::regclass);


--
-- Name: accounts id; Type: DEFAULT; Schema: public; Owner: distribution_user
--

ALTER TABLE ONLY public.accounts ALTER COLUMN id SET DEFAULT nextval('public.accounts_id_seq'::regclass);


--
-- Name: companies id; Type: DEFAULT; Schema: public; Owner: distribution_user
--

ALTER TABLE ONLY public.companies ALTER COLUMN id SET DEFAULT nextval('public.companies_id_seq'::regclass);


--
-- Name: drivers id; Type: DEFAULT; Schema: public; Owner: distribution_user
--

ALTER TABLE ONLY public.drivers ALTER COLUMN id SET DEFAULT nextval('public.drivers_id_seq'::regclass);


--
-- Name: files id; Type: DEFAULT; Schema: public; Owner: distribution_user
--

ALTER TABLE ONLY public.files ALTER COLUMN id SET DEFAULT nextval('public.files_id_seq'::regclass);


--
-- Name: gps_records id; Type: DEFAULT; Schema: public; Owner: distribution_user
--

ALTER TABLE ONLY public.gps_records ALTER COLUMN id SET DEFAULT nextval('public.gps_records_id_seq'::regclass);


--
-- Name: import_batches id; Type: DEFAULT; Schema: public; Owner: distribution_user
--

ALTER TABLE ONLY public.import_batches ALTER COLUMN id SET DEFAULT nextval('public.import_batches_id_seq'::regclass);


--
-- Name: orders id; Type: DEFAULT; Schema: public; Owner: distribution_user
--

ALTER TABLE ONLY public.orders ALTER COLUMN id SET DEFAULT nextval('public.orders_id_seq'::regclass);


--
-- Name: projects id; Type: DEFAULT; Schema: public; Owner: distribution_user
--

ALTER TABLE ONLY public.projects ALTER COLUMN id SET DEFAULT nextval('public.projects_id_seq'::regclass);


--
-- Name: request_files id; Type: DEFAULT; Schema: public; Owner: distribution_user
--

ALTER TABLE ONLY public.request_files ALTER COLUMN id SET DEFAULT nextval('public.request_files_id_seq'::regclass);


--
-- Name: requests id; Type: DEFAULT; Schema: public; Owner: distribution_user
--

ALTER TABLE ONLY public.requests ALTER COLUMN id SET DEFAULT nextval('public.requests_id_seq'::regclass);


--
-- Name: stores id; Type: DEFAULT; Schema: public; Owner: distribution_user
--

ALTER TABLE ONLY public.stores ALTER COLUMN id SET DEFAULT nextval('public.stores_id_seq'::regclass);


--
-- Name: vehicles id; Type: DEFAULT; Schema: public; Owner: distribution_user
--

ALTER TABLE ONLY public.vehicles ALTER COLUMN id SET DEFAULT nextval('public.vehicles_id_seq'::regclass);


--
-- Data for Name: audit_runs; Type: TABLE DATA; Schema: audit; Owner: distribution_user
--

COPY audit.audit_runs (id, started_at, finished_at, dataset_name, total_records, valid_records, invalid_records, duplicate_records, report, created_by) FROM stdin;
\.


--
-- Data for Name: row_audit_results; Type: TABLE DATA; Schema: audit; Owner: distribution_user
--

COPY audit.row_audit_results (id, audit_run_id, store_id, dimension, severity, issue_code, issue_description, old_value, suggested_value, created_at) FROM stdin;
\.


--
-- Data for Name: accounts; Type: TABLE DATA; Schema: public; Owner: distribution_user
--

COPY public.accounts (mobile, id, created_at, updated_at) FROM stdin;
09391232904	1	2026-07-15 17:09:41.561263+00	2026-07-15 17:09:41.561263+00
۰۹۱۲۲۲۲۲۲۲۲	2	2026-07-15 23:05:36.227229+00	2026-07-15 23:05:36.227229+00
۰۹۲۲۲۲۲۲۲۲۲	3	2026-07-15 23:33:23.975114+00	2026-07-15 23:33:23.975114+00
\.


--
-- Data for Name: alembic_version; Type: TABLE DATA; Schema: public; Owner: distribution_user
--

COPY public.alembic_version (version_num) FROM stdin;
675bbb1c38b1
\.


--
-- Data for Name: companies; Type: TABLE DATA; Schema: public; Owner: distribution_user
--

COPY public.companies (account_id, name, economic_code, national_id, phone, email, address, id, created_at, updated_at) FROM stdin;
1	شرکت جاده ابریشم	\N	\N	\N	\N	\N	1	2026-07-15 17:09:41.571749+00	2026-07-15 17:09:41.571749+00
2	شرکت ۰۹۱۲۲۲۲۲۲۲۲	\N	\N	\N	\N	\N	2	2026-07-15 23:05:36.243174+00	2026-07-15 23:05:36.243174+00
3	شرکت ۰۹۲۲۲۲۲۲۲۲۲	\N	\N	\N	\N	\N	3	2026-07-15 23:33:23.984021+00	2026-07-15 23:33:23.984021+00
\.


--
-- Data for Name: drivers; Type: TABLE DATA; Schema: public; Owner: distribution_user
--

COPY public.drivers (import_batch_id, driver_code, first_name, last_name, phone, license_number, license_expiry, experience_years, latitude, longitude, status, raw_data, error_note, id, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: files; Type: TABLE DATA; Schema: public; Owner: distribution_user
--

COPY public.files (entity_type, entity_id, category, original_name, stored_name, file_path, content_type, file_size, id, created_at, updated_at, uploaded_by) FROM stdin;
\.


--
-- Data for Name: gps_records; Type: TABLE DATA; Schema: public; Owner: distribution_user
--

COPY public.gps_records (import_batch_id, vehicle_plate, latitude, longitude, "timestamp", speed_kmh, heading, accuracy_m, raw_data, error_note, id, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: import_batches; Type: TABLE DATA; Schema: public; Owner: distribution_user
--

COPY public.import_batches (file_id, entity_type, status, total_rows, valid_rows, error_rows, imported_rows, error_log, column_mapping, started_at, completed_at, id, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: orders; Type: TABLE DATA; Schema: public; Owner: distribution_user
--

COPY public.orders (import_batch_id, order_code, store_code, store_name, address, latitude, longitude, weight_kg, volume_m3, delivery_date, delivery_time_from, delivery_time_to, status, raw_data, error_note, id, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: projects; Type: TABLE DATA; Schema: public; Owner: distribution_user
--

COPY public.projects (company_id, name, description, status, id, created_at, updated_at) FROM stdin;
1	پروژه تست ۱۰۰۰	پروژه تست ۱۰۰۰	DRAFT	1	2026-07-15 17:09:41.587983+00	2026-07-15 17:09:41.587983+00
2	پروژه ۰۹۱۲۲۲۲۲۲۲۲	پروژه ۰۹۱۲۲۲۲۲۲۲۲ مر بوط به  شرکت ۰۹۱۲۲۲۲۲۲۲۲	DRAFT	2	2026-07-15 23:05:36.256256+00	2026-07-15 23:05:36.256256+00
3	پروژه ۰۹۲۲۲۲۲۲۲۲۲	پروژه ۰۰۹۲۲۲۲۲۲۲۲۲ مر بوط به  شرکت ۰۹۲۲۲۲۲۲۲۲۲	DRAFT	3	2026-07-15 23:33:23.991779+00	2026-07-15 23:33:23.991779+00
\.


--
-- Data for Name: request_files; Type: TABLE DATA; Schema: public; Owner: distribution_user
--

COPY public.request_files (request_id, file_type, original_name, stored_name, file_path, content_type, file_size, id, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: requests; Type: TABLE DATA; Schema: public; Owner: distribution_user
--

COPY public.requests (company_name, contact_name, mobile, email, industry, goal, status, id, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: stores; Type: TABLE DATA; Schema: public; Owner: distribution_user
--

COPY public.stores (import_batch_id, code, name, phone, address, latitude, longitude, category, priority, status, service_time_min, raw_data, error_note, id, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: vehicles; Type: TABLE DATA; Schema: public; Owner: distribution_user
--

COPY public.vehicles (import_batch_id, vehicle_code, plate_number, vehicle_type, capacity_kg, capacity_m3, cost_per_km, fixed_cost, latitude, longitude, status, available_from, available_until, raw_data, error_note, id, created_at, updated_at) FROM stdin;
\.


--
-- Name: audit_runs_id_seq; Type: SEQUENCE SET; Schema: audit; Owner: distribution_user
--

SELECT pg_catalog.setval('audit.audit_runs_id_seq', 1, false);


--
-- Name: row_audit_results_id_seq; Type: SEQUENCE SET; Schema: audit; Owner: distribution_user
--

SELECT pg_catalog.setval('audit.row_audit_results_id_seq', 1, false);


--
-- Name: accounts_id_seq; Type: SEQUENCE SET; Schema: public; Owner: distribution_user
--

SELECT pg_catalog.setval('public.accounts_id_seq', 3, true);


--
-- Name: companies_id_seq; Type: SEQUENCE SET; Schema: public; Owner: distribution_user
--

SELECT pg_catalog.setval('public.companies_id_seq', 3, true);


--
-- Name: drivers_id_seq; Type: SEQUENCE SET; Schema: public; Owner: distribution_user
--

SELECT pg_catalog.setval('public.drivers_id_seq', 1, false);


--
-- Name: files_id_seq; Type: SEQUENCE SET; Schema: public; Owner: distribution_user
--

SELECT pg_catalog.setval('public.files_id_seq', 1, false);


--
-- Name: gps_records_id_seq; Type: SEQUENCE SET; Schema: public; Owner: distribution_user
--

SELECT pg_catalog.setval('public.gps_records_id_seq', 1, false);


--
-- Name: import_batches_id_seq; Type: SEQUENCE SET; Schema: public; Owner: distribution_user
--

SELECT pg_catalog.setval('public.import_batches_id_seq', 1, false);


--
-- Name: orders_id_seq; Type: SEQUENCE SET; Schema: public; Owner: distribution_user
--

SELECT pg_catalog.setval('public.orders_id_seq', 1, false);


--
-- Name: projects_id_seq; Type: SEQUENCE SET; Schema: public; Owner: distribution_user
--

SELECT pg_catalog.setval('public.projects_id_seq', 3, true);


--
-- Name: request_files_id_seq; Type: SEQUENCE SET; Schema: public; Owner: distribution_user
--

SELECT pg_catalog.setval('public.request_files_id_seq', 1, false);


--
-- Name: requests_id_seq; Type: SEQUENCE SET; Schema: public; Owner: distribution_user
--

SELECT pg_catalog.setval('public.requests_id_seq', 1, false);


--
-- Name: stores_id_seq; Type: SEQUENCE SET; Schema: public; Owner: distribution_user
--

SELECT pg_catalog.setval('public.stores_id_seq', 1, false);


--
-- Name: vehicles_id_seq; Type: SEQUENCE SET; Schema: public; Owner: distribution_user
--

SELECT pg_catalog.setval('public.vehicles_id_seq', 1, false);


--
-- Name: audit_runs audit_runs_pkey; Type: CONSTRAINT; Schema: audit; Owner: distribution_user
--

ALTER TABLE ONLY audit.audit_runs
    ADD CONSTRAINT audit_runs_pkey PRIMARY KEY (id);


--
-- Name: row_audit_results row_audit_results_pkey; Type: CONSTRAINT; Schema: audit; Owner: distribution_user
--

ALTER TABLE ONLY audit.row_audit_results
    ADD CONSTRAINT row_audit_results_pkey PRIMARY KEY (id);


--
-- Name: accounts accounts_pkey; Type: CONSTRAINT; Schema: public; Owner: distribution_user
--

ALTER TABLE ONLY public.accounts
    ADD CONSTRAINT accounts_pkey PRIMARY KEY (id);


--
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: distribution_user
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


--
-- Name: companies companies_pkey; Type: CONSTRAINT; Schema: public; Owner: distribution_user
--

ALTER TABLE ONLY public.companies
    ADD CONSTRAINT companies_pkey PRIMARY KEY (id);


--
-- Name: drivers drivers_pkey; Type: CONSTRAINT; Schema: public; Owner: distribution_user
--

ALTER TABLE ONLY public.drivers
    ADD CONSTRAINT drivers_pkey PRIMARY KEY (id);


--
-- Name: files files_pkey; Type: CONSTRAINT; Schema: public; Owner: distribution_user
--

ALTER TABLE ONLY public.files
    ADD CONSTRAINT files_pkey PRIMARY KEY (id);


--
-- Name: files files_stored_name_key; Type: CONSTRAINT; Schema: public; Owner: distribution_user
--

ALTER TABLE ONLY public.files
    ADD CONSTRAINT files_stored_name_key UNIQUE (stored_name);


--
-- Name: gps_records gps_records_pkey; Type: CONSTRAINT; Schema: public; Owner: distribution_user
--

ALTER TABLE ONLY public.gps_records
    ADD CONSTRAINT gps_records_pkey PRIMARY KEY (id);


--
-- Name: import_batches import_batches_pkey; Type: CONSTRAINT; Schema: public; Owner: distribution_user
--

ALTER TABLE ONLY public.import_batches
    ADD CONSTRAINT import_batches_pkey PRIMARY KEY (id);


--
-- Name: orders orders_pkey; Type: CONSTRAINT; Schema: public; Owner: distribution_user
--

ALTER TABLE ONLY public.orders
    ADD CONSTRAINT orders_pkey PRIMARY KEY (id);


--
-- Name: projects projects_pkey; Type: CONSTRAINT; Schema: public; Owner: distribution_user
--

ALTER TABLE ONLY public.projects
    ADD CONSTRAINT projects_pkey PRIMARY KEY (id);


--
-- Name: request_files request_files_pkey; Type: CONSTRAINT; Schema: public; Owner: distribution_user
--

ALTER TABLE ONLY public.request_files
    ADD CONSTRAINT request_files_pkey PRIMARY KEY (id);


--
-- Name: request_files request_files_stored_name_key; Type: CONSTRAINT; Schema: public; Owner: distribution_user
--

ALTER TABLE ONLY public.request_files
    ADD CONSTRAINT request_files_stored_name_key UNIQUE (stored_name);


--
-- Name: requests requests_pkey; Type: CONSTRAINT; Schema: public; Owner: distribution_user
--

ALTER TABLE ONLY public.requests
    ADD CONSTRAINT requests_pkey PRIMARY KEY (id);


--
-- Name: stores stores_pkey; Type: CONSTRAINT; Schema: public; Owner: distribution_user
--

ALTER TABLE ONLY public.stores
    ADD CONSTRAINT stores_pkey PRIMARY KEY (id);


--
-- Name: drivers uq_drivers_batch_driver; Type: CONSTRAINT; Schema: public; Owner: distribution_user
--

ALTER TABLE ONLY public.drivers
    ADD CONSTRAINT uq_drivers_batch_driver UNIQUE (import_batch_id, driver_code);


--
-- Name: orders uq_orders_batch_order; Type: CONSTRAINT; Schema: public; Owner: distribution_user
--

ALTER TABLE ONLY public.orders
    ADD CONSTRAINT uq_orders_batch_order UNIQUE (import_batch_id, order_code);


--
-- Name: stores uq_stores_batch_code; Type: CONSTRAINT; Schema: public; Owner: distribution_user
--

ALTER TABLE ONLY public.stores
    ADD CONSTRAINT uq_stores_batch_code UNIQUE (import_batch_id, code);


--
-- Name: vehicles vehicles_pkey; Type: CONSTRAINT; Schema: public; Owner: distribution_user
--

ALTER TABLE ONLY public.vehicles
    ADD CONSTRAINT vehicles_pkey PRIMARY KEY (id);


--
-- Name: idx_row_audit_results_audit_run; Type: INDEX; Schema: audit; Owner: distribution_user
--

CREATE INDEX idx_row_audit_results_audit_run ON audit.row_audit_results USING btree (audit_run_id);


--
-- Name: idx_row_audit_results_dimension; Type: INDEX; Schema: audit; Owner: distribution_user
--

CREATE INDEX idx_row_audit_results_dimension ON audit.row_audit_results USING btree (dimension);


--
-- Name: idx_row_audit_results_issue; Type: INDEX; Schema: audit; Owner: distribution_user
--

CREATE INDEX idx_row_audit_results_issue ON audit.row_audit_results USING btree (issue_code);


--
-- Name: idx_row_audit_results_store; Type: INDEX; Schema: audit; Owner: distribution_user
--

CREATE INDEX idx_row_audit_results_store ON audit.row_audit_results USING btree (store_id);


--
-- Name: ix_accounts_id; Type: INDEX; Schema: public; Owner: distribution_user
--

CREATE INDEX ix_accounts_id ON public.accounts USING btree (id);


--
-- Name: ix_accounts_mobile; Type: INDEX; Schema: public; Owner: distribution_user
--

CREATE UNIQUE INDEX ix_accounts_mobile ON public.accounts USING btree (mobile);


--
-- Name: ix_companies_id; Type: INDEX; Schema: public; Owner: distribution_user
--

CREATE INDEX ix_companies_id ON public.companies USING btree (id);


--
-- Name: ix_companies_name; Type: INDEX; Schema: public; Owner: distribution_user
--

CREATE UNIQUE INDEX ix_companies_name ON public.companies USING btree (name);


--
-- Name: ix_drivers_driver_code; Type: INDEX; Schema: public; Owner: distribution_user
--

CREATE INDEX ix_drivers_driver_code ON public.drivers USING btree (driver_code);


--
-- Name: ix_drivers_id; Type: INDEX; Schema: public; Owner: distribution_user
--

CREATE INDEX ix_drivers_id ON public.drivers USING btree (id);


--
-- Name: ix_drivers_import_batch_id; Type: INDEX; Schema: public; Owner: distribution_user
--

CREATE INDEX ix_drivers_import_batch_id ON public.drivers USING btree (import_batch_id);


--
-- Name: ix_drivers_phone; Type: INDEX; Schema: public; Owner: distribution_user
--

CREATE INDEX ix_drivers_phone ON public.drivers USING btree (phone);


--
-- Name: ix_drivers_status; Type: INDEX; Schema: public; Owner: distribution_user
--

CREATE INDEX ix_drivers_status ON public.drivers USING btree (status);


--
-- Name: ix_files_category; Type: INDEX; Schema: public; Owner: distribution_user
--

CREATE INDEX ix_files_category ON public.files USING btree (category);


--
-- Name: ix_files_entity_id; Type: INDEX; Schema: public; Owner: distribution_user
--

CREATE INDEX ix_files_entity_id ON public.files USING btree (entity_id);


--
-- Name: ix_files_entity_type; Type: INDEX; Schema: public; Owner: distribution_user
--

CREATE INDEX ix_files_entity_type ON public.files USING btree (entity_type);


--
-- Name: ix_files_id; Type: INDEX; Schema: public; Owner: distribution_user
--

CREATE INDEX ix_files_id ON public.files USING btree (id);


--
-- Name: ix_files_uploaded_by; Type: INDEX; Schema: public; Owner: distribution_user
--

CREATE INDEX ix_files_uploaded_by ON public.files USING btree (uploaded_by);


--
-- Name: ix_gps_records_id; Type: INDEX; Schema: public; Owner: distribution_user
--

CREATE INDEX ix_gps_records_id ON public.gps_records USING btree (id);


--
-- Name: ix_gps_records_import_batch_id; Type: INDEX; Schema: public; Owner: distribution_user
--

CREATE INDEX ix_gps_records_import_batch_id ON public.gps_records USING btree (import_batch_id);


--
-- Name: ix_gps_records_timestamp; Type: INDEX; Schema: public; Owner: distribution_user
--

CREATE INDEX ix_gps_records_timestamp ON public.gps_records USING btree ("timestamp");


--
-- Name: ix_gps_records_vehicle_plate; Type: INDEX; Schema: public; Owner: distribution_user
--

CREATE INDEX ix_gps_records_vehicle_plate ON public.gps_records USING btree (vehicle_plate);


--
-- Name: ix_import_batches_entity_type; Type: INDEX; Schema: public; Owner: distribution_user
--

CREATE INDEX ix_import_batches_entity_type ON public.import_batches USING btree (entity_type);


--
-- Name: ix_import_batches_file_id; Type: INDEX; Schema: public; Owner: distribution_user
--

CREATE INDEX ix_import_batches_file_id ON public.import_batches USING btree (file_id);


--
-- Name: ix_import_batches_id; Type: INDEX; Schema: public; Owner: distribution_user
--

CREATE INDEX ix_import_batches_id ON public.import_batches USING btree (id);


--
-- Name: ix_import_batches_status; Type: INDEX; Schema: public; Owner: distribution_user
--

CREATE INDEX ix_import_batches_status ON public.import_batches USING btree (status);


--
-- Name: ix_orders_id; Type: INDEX; Schema: public; Owner: distribution_user
--

CREATE INDEX ix_orders_id ON public.orders USING btree (id);


--
-- Name: ix_orders_import_batch_id; Type: INDEX; Schema: public; Owner: distribution_user
--

CREATE INDEX ix_orders_import_batch_id ON public.orders USING btree (import_batch_id);


--
-- Name: ix_orders_order_code; Type: INDEX; Schema: public; Owner: distribution_user
--

CREATE INDEX ix_orders_order_code ON public.orders USING btree (order_code);


--
-- Name: ix_orders_status; Type: INDEX; Schema: public; Owner: distribution_user
--

CREATE INDEX ix_orders_status ON public.orders USING btree (status);


--
-- Name: ix_orders_store_code; Type: INDEX; Schema: public; Owner: distribution_user
--

CREATE INDEX ix_orders_store_code ON public.orders USING btree (store_code);


--
-- Name: ix_projects_company_id; Type: INDEX; Schema: public; Owner: distribution_user
--

CREATE INDEX ix_projects_company_id ON public.projects USING btree (company_id);


--
-- Name: ix_projects_id; Type: INDEX; Schema: public; Owner: distribution_user
--

CREATE INDEX ix_projects_id ON public.projects USING btree (id);


--
-- Name: ix_request_files_id; Type: INDEX; Schema: public; Owner: distribution_user
--

CREATE INDEX ix_request_files_id ON public.request_files USING btree (id);


--
-- Name: ix_request_files_request_id; Type: INDEX; Schema: public; Owner: distribution_user
--

CREATE INDEX ix_request_files_request_id ON public.request_files USING btree (request_id);


--
-- Name: ix_requests_company_name; Type: INDEX; Schema: public; Owner: distribution_user
--

CREATE INDEX ix_requests_company_name ON public.requests USING btree (company_name);


--
-- Name: ix_requests_id; Type: INDEX; Schema: public; Owner: distribution_user
--

CREATE INDEX ix_requests_id ON public.requests USING btree (id);


--
-- Name: ix_requests_mobile; Type: INDEX; Schema: public; Owner: distribution_user
--

CREATE INDEX ix_requests_mobile ON public.requests USING btree (mobile);


--
-- Name: ix_requests_status; Type: INDEX; Schema: public; Owner: distribution_user
--

CREATE INDEX ix_requests_status ON public.requests USING btree (status);


--
-- Name: ix_stores_code; Type: INDEX; Schema: public; Owner: distribution_user
--

CREATE INDEX ix_stores_code ON public.stores USING btree (code);


--
-- Name: ix_stores_id; Type: INDEX; Schema: public; Owner: distribution_user
--

CREATE INDEX ix_stores_id ON public.stores USING btree (id);


--
-- Name: ix_stores_import_batch_id; Type: INDEX; Schema: public; Owner: distribution_user
--

CREATE INDEX ix_stores_import_batch_id ON public.stores USING btree (import_batch_id);


--
-- Name: ix_stores_phone; Type: INDEX; Schema: public; Owner: distribution_user
--

CREATE INDEX ix_stores_phone ON public.stores USING btree (phone);


--
-- Name: ix_stores_status; Type: INDEX; Schema: public; Owner: distribution_user
--

CREATE INDEX ix_stores_status ON public.stores USING btree (status);


--
-- Name: ix_vehicles_id; Type: INDEX; Schema: public; Owner: distribution_user
--

CREATE INDEX ix_vehicles_id ON public.vehicles USING btree (id);


--
-- Name: ix_vehicles_import_batch_id; Type: INDEX; Schema: public; Owner: distribution_user
--

CREATE INDEX ix_vehicles_import_batch_id ON public.vehicles USING btree (import_batch_id);


--
-- Name: ix_vehicles_plate_number; Type: INDEX; Schema: public; Owner: distribution_user
--

CREATE INDEX ix_vehicles_plate_number ON public.vehicles USING btree (plate_number);


--
-- Name: ix_vehicles_status; Type: INDEX; Schema: public; Owner: distribution_user
--

CREATE INDEX ix_vehicles_status ON public.vehicles USING btree (status);


--
-- Name: ix_vehicles_vehicle_code; Type: INDEX; Schema: public; Owner: distribution_user
--

CREATE INDEX ix_vehicles_vehicle_code ON public.vehicles USING btree (vehicle_code);


--
-- Name: row_audit_results row_audit_results_audit_run_id_fkey; Type: FK CONSTRAINT; Schema: audit; Owner: distribution_user
--

ALTER TABLE ONLY audit.row_audit_results
    ADD CONSTRAINT row_audit_results_audit_run_id_fkey FOREIGN KEY (audit_run_id) REFERENCES audit.audit_runs(id) ON DELETE CASCADE;


--
-- Name: companies companies_account_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: distribution_user
--

ALTER TABLE ONLY public.companies
    ADD CONSTRAINT companies_account_id_fkey FOREIGN KEY (account_id) REFERENCES public.accounts(id);


--
-- Name: drivers drivers_import_batch_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: distribution_user
--

ALTER TABLE ONLY public.drivers
    ADD CONSTRAINT drivers_import_batch_id_fkey FOREIGN KEY (import_batch_id) REFERENCES public.import_batches(id) ON DELETE CASCADE;


--
-- Name: gps_records gps_records_import_batch_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: distribution_user
--

ALTER TABLE ONLY public.gps_records
    ADD CONSTRAINT gps_records_import_batch_id_fkey FOREIGN KEY (import_batch_id) REFERENCES public.import_batches(id) ON DELETE CASCADE;


--
-- Name: import_batches import_batches_file_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: distribution_user
--

ALTER TABLE ONLY public.import_batches
    ADD CONSTRAINT import_batches_file_id_fkey FOREIGN KEY (file_id) REFERENCES public.files(id) ON DELETE CASCADE;


--
-- Name: orders orders_import_batch_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: distribution_user
--

ALTER TABLE ONLY public.orders
    ADD CONSTRAINT orders_import_batch_id_fkey FOREIGN KEY (import_batch_id) REFERENCES public.import_batches(id) ON DELETE CASCADE;


--
-- Name: projects projects_company_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: distribution_user
--

ALTER TABLE ONLY public.projects
    ADD CONSTRAINT projects_company_id_fkey FOREIGN KEY (company_id) REFERENCES public.companies(id) ON DELETE CASCADE;


--
-- Name: request_files request_files_request_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: distribution_user
--

ALTER TABLE ONLY public.request_files
    ADD CONSTRAINT request_files_request_id_fkey FOREIGN KEY (request_id) REFERENCES public.requests(id) ON DELETE CASCADE;


--
-- Name: stores stores_import_batch_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: distribution_user
--

ALTER TABLE ONLY public.stores
    ADD CONSTRAINT stores_import_batch_id_fkey FOREIGN KEY (import_batch_id) REFERENCES public.import_batches(id) ON DELETE CASCADE;


--
-- Name: vehicles vehicles_import_batch_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: distribution_user
--

ALTER TABLE ONLY public.vehicles
    ADD CONSTRAINT vehicles_import_batch_id_fkey FOREIGN KEY (import_batch_id) REFERENCES public.import_batches(id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

\unrestrict eOOZ4PWrfoqJBg39mv2KFQxrwhdkPnTVEyLUQC5ojgHu4UjFeQ3miV3BbV4amIJ

