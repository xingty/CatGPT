DROP TABLE IF EXISTS message;
DROP TABLE IF EXISTS service_usage;

create table topic
(
    tid              INTEGER PRIMARY KEY AUTOINCREMENT ,
    label           TEXT,
    chat_id         INTEGER,
    user_id         INTEGER,
    title           TEXT,
    generate_title  INTEGER
);

create index idx_t_topic_id on topic (tid);

create table message
(
    role       TEXT,
    content    TEXT,
    message_id INTEGER,
    chat_id    INTEGER,
    ts         INTEGER,
    topic_id   INTEGER
);

create index idx_msg_topic_id on message (topic_id);