DROP TABLE IF EXISTS message;
DROP TABLE IF EXISTS service_usage;

create table topic
(
    tid              INTEGER PRIMARY KEY AUTOINCREMENT ,
    label           TEXT,
    chat_id         INTEGER,
    user_id         INTEGER,
    title           TEXT,
    generate_title  INTEGER,
    thread_id       INTEGER,
    unique (label)
);

create index idx_t_uid_cid on topic (user_id, chat_id);

create table message
(
    role            TEXT,
    content         TEXT,
    message_id      INTEGER,
    chat_id         INTEGER,
    ts              INTEGER,
    topic_id        INTEGER,
    message_type    INTEGER default 0
);

create index idx_msg_topic_id on message (topic_id);

create table message_holder
(
    content         TEXT,
    message_id      INTEGER,
    user_id         INTEGER,
    chat_id         INTEGER,
    topic_id        INTEGER,
    reply_id        INTEGER,
    message_type    INTEGER default 0,
    unique (user_id, chat_id)
);

create table profile
(
    uid       INTEGER,
    model     TEXT,
    endpoint  TEXT,
    prompt    TEXT,
    chat_type INTEGER default 0 not null,
    chat_id   INTEGER default 0 not null,
    thread_id INTEGER default 0 not null,
    topic_id  INTEGER default 0 not null,
    unique (uid, chat_id, thread_id)
);

create index idx_profile_uid on profile (uid);

create table users
(
    uid             INTEGER,
    blocked         TEXT,
    unique (uid)
);

create table group_info
(
    chat_id    INTEGER not null ,
    respond_message INTEGER default 0 not null
);

create index gi_u_cid on group_info (chat_id);

create table version
(
    version_name    TEXT,
    version_code    INTEGER
)