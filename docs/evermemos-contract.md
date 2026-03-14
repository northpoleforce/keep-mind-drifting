# Evermemos Contract (Draft)

## Core Entities

- `MessageRecord`
  - `channel_id`
  - `session_id`
  - `message_id`
  - `role`
  - `text`
  - `topic_node_id`
  - `timestamp`
  - `metadata`
- `TopicNodeRecord`
  - `channel_id`
  - `session_id`
  - `topic_node_id`
  - `parent_topic_node_id`
  - `topic_summary`
  - `confidence`
  - `timestamp`
  - `metadata`

## Required Adapter Methods

- `ping()`
- `save_message(record)`
- `save_topic_node(record)`
- `query_context(query)`
- `rebuild_flow(channel_id, session_id)`

## Indexing Guidance

- Primary lookup: `session_id + timestamp`
- Topic reconstruction: `session_id + topic_node_id + parent_topic_node_id`
- Replay support: stable time ordering for both messages and nodes
