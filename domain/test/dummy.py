CREATE_TEN_DUMMY_NODES_QUERY = """
UNWIND $users AS user

OPTIONAL MATCH (existingUser:User {username: user.username})
WITH existingUser, user
CALL apoc.do.when(
  existingUser IS NOT NULL,
  'RETURN "data already exists" AS message',
  '
    CREATE (pd:PrivateData {
      email: user.email,
      password: user.password,
      username: user.username,
      link_info: "",
      verification_info: "",
      link_count: 0,
      verification_count: 0,
      grant: "verified",
      node_id: randomUUID()
    })
    CREATE (u:User {
      username: user.username,
      nickname: user.nickname,
      tags: user.tags,
      my_memo: "",
      node_id: randomUUID()
    })
    CREATE (pd)-[:is_info]->(u)
    RETURN "success" AS message
  ',
  {user: user}
) YIELD value
RETURN value.message
"""


CREATE_TEN_DUMMY_EDGES_QUERY = """
MATCH (u1:User {nickname: 'nickname1'})
MATCH (u2:User {nickname: 'nickname2'})
MATCH (u3:User {nickname: 'nickname3'})
MATCH (u4:User {nickname: 'nickname4'})
MATCH (u5:User {nickname: 'nickname5'})
MATCH (u6:User {nickname: 'nickname6'})
MATCH (u7:User {nickname: 'nickname7'})
MATCH (u8:User {nickname: 'nickname8'})
MATCH (u9:User {nickname: 'nickname9'})
MATCH (u10:User {nickname: 'nickname10'})
MATCH (u11:User {nickname: 'nickname11'})
MATCH (u12:User {nickname: 'nickname12'})
MATCH (u13:User {nickname: 'nickname13'})
MATCH (u14:User {nickname: 'nickname14'})


MERGE (u1)-[:is_roommate {edge_id: randomUUID(), memo: '', group: ''}]->(u2)
MERGE (u1)-[:is_roommate {edge_id: randomUUID(), memo: '', group: ''}]->(u3)
MERGE (u1)-[:is_roommate {edge_id: randomUUID(), memo: '', group: ''}]->(u4)
MERGE (u1)-[:is_roommate {edge_id: randomUUID(), memo: '', group: ''}]->(u5)
MERGE (u1)-[:is_roommate {edge_id: randomUUID(), memo: '', group: ''}]->(u6)
MERGE (u1)-[:is_roommate {edge_id: randomUUID(), memo: '', group: ''}]->(u8)
MERGE (u1)-[:is_roommate {edge_id: randomUUID(), memo: '', group: ''}]->(u9)
MERGE (u1)-[:is_roommate {edge_id: randomUUID(), memo: '', group: ''}]->(u11)
MERGE (u1)-[:is_roommate {edge_id: randomUUID(), memo: '', group: ''}]->(u12)

MERGE (u1)<-[:is_roommate {edge_id: randomUUID(), memo: '', group: ''}]-(u2)
MERGE (u1)<-[:is_roommate {edge_id: randomUUID(), memo: '', group: ''}]-(u3)
MERGE (u1)<-[:is_roommate {edge_id: randomUUID(), memo: '', group: ''}]-(u4)
MERGE (u1)<-[:is_roommate {edge_id: randomUUID(), memo: '', group: ''}]-(u5)
MERGE (u1)<-[:is_roommate {edge_id: randomUUID(), memo: '', group: ''}]-(u6)
MERGE (u1)<-[:is_roommate {edge_id: randomUUID(), memo: '', group: ''}]-(u8)
MERGE (u1)<-[:is_roommate {edge_id: randomUUID(), memo: '', group: ''}]-(u9)
MERGE (u1)<-[:is_roommate {edge_id: randomUUID(), memo: '', group: ''}]-(u11)
MERGE (u1)<-[:is_roommate {edge_id: randomUUID(), memo: '', group: ''}]-(u12)


MERGE (u6)-[:is_roommate {edge_id: randomUUID(), memo: '', group: ''}]->(u7)
MERGE (u6)-[:is_roommate {edge_id: randomUUID(), memo: '', group: ''}]->(u10)
MERGE (u8)-[:is_roommate {edge_id: randomUUID(), memo: '', group: ''}]->(u10)
MERGE (u11)-[:is_roommate {edge_id: randomUUID(), memo: '', group: ''}]->(u12)
MERGE (u9)-[:is_roommate {edge_id: randomUUID(), memo: '', group: ''}]->(u13)

MERGE (u6)<-[:is_roommate {edge_id: randomUUID(), memo: '', group: ''}]-(u7)
MERGE (u6)<-[:is_roommate {edge_id: randomUUID(), memo: '', group: ''}]-(u10)
MERGE (u8)<-[:is_roommate {edge_id: randomUUID(), memo: '', group: ''}]-(u10)
MERGE (u11)<-[:is_roommate {edge_id: randomUUID(), memo: '', group: ''}]-(u12)
MERGE (u9)<-[:is_roommate {edge_id: randomUUID(), memo: '', group: ''}]-(u13)

MERGE (u7)-[:is_roommate {edge_id: randomUUID(), memo: '', group: ''}]->(u14)
MERGE (u14)-[:is_roommate {edge_id: randomUUID(), memo: '', group: ''}]->(u7)

RETURN "Success"
;
"""


DELETE_DUMMY_DATA_QUERY = """
MATCH p=()-[]->(U:User)
WHERE U.username CONTAINS "test"
DETACH DELETE p
RETURN "Success"
;
"""


CREATE_SEVERAL_DUMMY = """
WITH $users AS users, $adjacency_matrix AS matrix

UNWIND range(0, size(users)-1) AS i
WITH i, users[i] AS user, matrix

CREATE (pd:PrivateData {
  email: user.email,
  password: user.password,
  username: user.username,
  link_info: "",
  verification_info: "",
  link_count: 0,
  verification_count: 0,
  grant: "verified",
  node_id: randomUUID()
})
CREATE (u:User {
  username: user.username,
  nickname: user.nickname,
  tags: user.tags,
  my_memo: "",
  node_id: randomUUID()
})
CREATE (pd)-[:is_info]->(u)

WITH collect(u) AS users, matrix

UNWIND range(0, size(users)-1) AS i
UNWIND range(0, size(users)-1) AS j
WITH users[i] AS user1, users[j] AS user2, matrix[i][j] AS should_connect
WHERE i <> j AND should_connect = 1
MERGE (user1)-[:is_roommate {edge_id: randomUUID(), memo: '', group: ''}]->(user2)

RETURN "Success" AS message
"""
