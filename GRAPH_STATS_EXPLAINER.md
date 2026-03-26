# Understanding Graph Stats — Plain English Guide

This app shows a **network of Spotify artists** where each artist is a **node** and each collaboration between two artists is an **edge** (a line connecting them).

---

## Graph Stats (the whole network)

These numbers describe the big picture of the graph currently on screen.

| Stat | What it means |
|---|---|
| **Artists On Screen** *(Shown Nodes)* | How many artists are visible right now. |
| **Collabs On Screen** *(Shown Edges)* | How many collaborations (connections) are visible right now. |
| **Network Crowdedness** *(Density)* | How "crowded" the network is. A density of 1.0 means every artist is connected to every other artist. Close to 0 means most artists barely interact. |
| **Avg Collabs Per Artist** *(Avg Degree)* | On average, how many collaborators each artist has in this graph. Higher = more connected crowd. |
| **Disconnected Groups** *(Components)* | How many separate "islands" exist. If this is 1, everyone is reachable from everyone. If this is 3, there are 3 isolated groups with no path between them. |
| **Biggest Group Size** *(Largest Component)* | The size (in artists) of the biggest connected island. |

---

## Node Stats (a single artist)

Click any artist in the graph to see their personal stats.

| Stat | What it means | Real-world analogy |
|---|---|---|
| **Direct Collaborators** *(Degree)* | How many direct collaborators this artist has. | Number of friends on a friend list. |
| **Connection Score** *(Degree Centrality)* | Degree as a fraction of the maximum possible connections. 1.0 = connected to everyone; 0 = connected to no one. | Popularity score from 0 to 1. |
| **Bridge Score** *(Betweenness)* | How often this artist sits on the *shortest path* between two other artists. High betweenness = a "bridge" between communities. | The person who introduces two friend groups to each other. |
| **Spotify Popularity** *(Popularity)* | Spotify popularity score (0-100). Higher = more streamed. | Chart position / fame level. |

---

## Quick intuition

- An artist with **high direct collaborators + high bridge score** is a superconnector. Remove them and the network can split.
- An artist with **high connection score** is linked to a large share of artists in the current graph.
- An artist with **high Spotify popularity** is likely more widely known outside this network too.

Try deleting a high-betweenness artist and watch the **Components** count go up!
